"""Douyin dispatch adapted from StreamCap DouyinHandler (Apache-2.0).
Platform parsing itself is delegated to locked StreamGet, not reimplemented.
"""
import re, asyncio, logging
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger('livewatch.parser')
QUALITIES = {'原画':'OD','超清':'UHD','高清':'HD','标清':'SD'}

class AccessRestricted(RuntimeError): pass

def clean_url(text):
    m = re.search(r'https?://[^\s<>"，。；！、]+', text)
    if not m: raise ValueError('未找到有效的抖音链接')
    p = urlsplit(m.group().rstrip(').,;!）'))
    if p.username or p.password or p.port not in (None,443,80): raise ValueError('链接包含不支持的认证信息或端口')
    path = p.path.rstrip('/')
    host = p.hostname
    valid = ((host == 'live.douyin.com' and re.fullmatch(r'/[A-Za-z0-9_-]+',path)) or
             (host == 'v.douyin.com' and re.fullmatch(r'/[A-Za-z0-9_-]+',path)) or
             (host == 'www.douyin.com' and re.fullmatch(r'/user/[A-Za-z0-9_-]+',path)))
    if not valid: raise ValueError('仅支持抖音直播间、分享短链和主播主页链接')
    return urlunsplit(('https',host,path,'',''))

def extract_urls(text):
    urls = re.findall(r'https?://[^\s<>"，。；！、]+',text)
    if not urls: raise ValueError('请粘贴至少一个链接')
    return [clean_url(u) for u in urls]

@dataclass
class StreamInfo:
    name: str
    room_id: str
    title: str = ''
    live: bool = False
    url: str = ''
    quality: str = 'OD'

class StreamResolver:
    async def resolve(self, url, quality='OD'):
        from streamget import DouyinLiveStream
        from utils.runtime import binary
        if not binary('node'): raise RuntimeError('缺少 Node.js，请查看软件设置中的依赖向导')
        client = DouyinLiveStream()
        try:
            async with asyncio.timeout(45):
                if 'v.douyin.com' in url or '/user/' in url:
                    raw = await client.fetch_app_stream_data(url=url)
                else:
                    raw = await client.fetch_web_stream_data(url=url)
                # Upstream defaults a missing status to offline; never accept that ambiguity.
                if raw.get('status') not in (2,4): raise RuntimeError('平台状态不明确，未判定为下播')
                data = await client.fetch_stream_url(raw, quality)
                canonical = raw.get('live_url') or url
                room_id = str(raw.get('id_str') or raw.get('id') or canonical.rsplit('/',1)[-1])
                # Prefer stable web room identity over per-session room id.
                if raw.get('live_url'): room_id = canonical.rstrip('/').rsplit('/',1)[-1]
                return StreamInfo(data.anchor_name or '未命名主播',room_id,data.title or raw.get('title',''),data.is_live,data.record_url or '',data.quality or quality)
        except Exception as exc:
            message = str(exc)
            log.warning('解析失败 %s: %s',type(exc).__name__,message)
            if any(s in message.lower() for s in ('403','429','risk control','captcha','验证码','风控','forbidden')):
                raise AccessRestricted('平台限制访问，已暂停任务；请稍后手动重试') from None
            raise RuntimeError(f'解析失败（{type(exc).__name__}），请查看脱敏解析日志') from None
