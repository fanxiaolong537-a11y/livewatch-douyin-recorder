import asyncio,json,logging,sqlite3
from pathlib import Path
import pytest
from core.stream_resolver import clean_url,extract_urls,StreamInfo,StreamResolver,AccessRestricted
from core.recorder import RecordingSession
from core.video_processor import probe,remux
from core.monitor import Monitor
from utils.runtime import safe_name,redact,export_diagnostics

@pytest.mark.parametrize('url,expected',[
 ('看直播 https://live.douyin.com/123456?foo=bar','https://live.douyin.com/123456'),
 ('https://v.douyin.com/AbCd/','https://v.douyin.com/AbCd'),
 ('https://www.douyin.com/user/MS4w-LjAB','https://www.douyin.com/user/MS4w-LjAB')])
def test_clean(url,expected): assert clean_url(url)==expected

@pytest.mark.parametrize('url',['hello','https://evil.com/abc','https://live.douyin.com.evil.com/123','https://user@live.douyin.com/123','https://live.douyin.com:99/123','https://www.douyin.com/video/123'])
def test_bad_links(url):
    with pytest.raises(ValueError): clean_url(url)

def test_batch_and_duplicate(store):
    urls=extract_urls('https://live.douyin.com/123\nhttps://v.douyin.com/foo')
    assert len(urls)==2
    store.add(urls[0])
    with pytest.raises(sqlite3.IntegrityError): store.add(urls[0])
    a=store.add(urls[1]); store.update(a,room_id='r')
    with pytest.raises(sqlite3.IntegrityError): store.update(1,room_id='r')

@pytest.mark.parametrize('name',['CON','a:b?c*','空间 中文 /测试','NUL.txt','LPT1','百分%比'])
def test_windows_names(name):
    result=safe_name(name)
    assert not any(c in result for c in '<>:"/\\|?*%')
    assert result.split('.')[0].upper() not in ('CON','NUL','LPT1')

def test_redaction(tmp_path):
    secret='Cookie: abc=SECRET\nAuthorization: Bearer SECRET\nhttps://host/x?token=SECRET\na_bogus=SECRET'
    assert 'SECRET' not in redact(secret)
    (tmp_path/'logs').mkdir(); (tmp_path/'logs'/'app.log').write_text(secret)
    out=tmp_path/'diagnostics.zip'; export_diagnostics(tmp_path,out)
    import zipfile
    with zipfile.ZipFile(out) as z: assert all(b'SECRET' not in z.read(n) for n in z.namelist())

def test_restart_persistence(tmp_path):
    from storage.database import Store
    path=tmp_path/'state.sqlite3'; s=Store(path); i=s.add('https://live.douyin.com/123',enabled=1,note='测试'); s.close()
    s=Store(path); assert s.task(i)['enabled']==1 and s.task(i)['note']=='测试'; s.close()

async def test_real_record_stop_probe_remux(video,store,tmp_path):
    i=store.add('https://live.douyin.com/123'); t=store.task(i); info=StreamInfo('主播 中文','123','测试',True,str(video))
    session=RecordingSession(t,info,tmp_path/'空 格中文目录',store,segment_seconds=1)
    await session.start(str(video)); await asyncio.sleep(4); await session.finish('已停止')
    meta=json.loads((session.directory/'metadata.json').read_text(encoding='utf-8'))
    assert meta['duration']>0 and len(meta['segments'])>=2
    p=Path(meta['segments'][0]['path']); result=await probe(p)
    assert result['audio_tracks']==1 and result['width']==320
    converted=await remux(p); assert converted.exists() and p.exists()
    assert (await probe(converted))['duration']>0
    with pytest.raises(FileExistsError): await remux(p)
    assert session.process.returncode is not None

async def test_validated_delete_source(video,tmp_path):
    import shutil
    p=tmp_path/'delete.ts'; shutil.copy(video,p)
    target=await remux(p,True); assert target.exists() and not p.exists()

async def test_invalid_file_not_deleted(tmp_path):
    p=tmp_path/'invalid.ts'; p.write_bytes(b'not a video')
    with pytest.raises(Exception): await remux(p,True)
    assert p.exists()

class Resolver:
    def __init__(self,video=None): self.live=False; self.error=False; self.calls=0; self.video=video
    async def resolve(self,url,quality):
        self.calls+=1
        if self.error: raise OSError('simulated network down')
        return StreamInfo('测试主播',url.rsplit('/',1)[-1],'授权生成视频',self.live,str(self.video or ''),quality)

async def wait_until(predicate,seconds=8):
    for _ in range(int(seconds/.05)):
        if predicate(): return
        await asyncio.sleep(.05)
    raise AssertionError('state wait timed out')

async def test_offline_error_not_offline(store,tmp_path):
    i=store.add('https://live.douyin.com/1'); r=Resolver(); r.error=True
    store.set_setting('request_spacing',0); m=Monitor(store,tmp_path,resolver=r,disk_free=lambda p:10**12,tick=.05)
    m.start(i); await wait_until(lambda:m.states.get(i)=='解析失败'); assert m.states[i]!='未开播'
    await m.stop(i)
    r.error=False; store.set_setting('interval',.1); m.start(i)
    await wait_until(lambda:m.states.get(i)=='未开播'); await m.stop(i)

async def test_three_recordings_and_disk_guard(video,store,tmp_path):
    ids=[store.add(f'https://live.douyin.com/{i}') for i in range(1,5)]
    r=Resolver(video); r.live=True; free=[10**12]
    store.set_setting('request_spacing',0); store.set_setting('interval',.2)
    m=Monitor(store,tmp_path,resolver=r,disk_free=lambda p:free[0],tick=.05)
    for i in ids: m.start(i)
    await wait_until(lambda:len(m.sessions)==3)
    await asyncio.sleep(3); assert len(m.sessions)==3
    free[0]=0; await wait_until(lambda:not m.sessions)
    await m.stop_all(); assert all(not t['enabled'] for t in store.tasks())
    assert len(store.recordings())==3

async def test_reconnect_refreshes_url_without_overwrite(video,store,tmp_path):
    i=store.add('https://live.douyin.com/1'); r=Resolver(video); r.live=True
    store.set_setting('request_spacing',0); store.set_setting('interval',.1)
    m=Monitor(store,tmp_path,resolver=r,disk_free=lambda p:10**12,tick=.05)
    m.start(i); await wait_until(lambda:i in m.sessions and m.sessions[i].process is not None)
    s=m.sessions[i]; await asyncio.sleep(2); first=s.process
    first.kill(); await first.wait()
    await wait_until(lambda:s.attempt>=2,seconds=10)
    assert r.calls>=2; await asyncio.sleep(2); await m.stop(i)
    names=[p.name for p in s.directory.glob('*.ts')]
    assert any('_r001_' in n for n in names) and any('_r002_' in n for n in names)
    assert any(e['type']=='reconnect' for e in s.meta['events'])

async def test_access_restriction_pauses(store,tmp_path):
    class Restricted:
        async def resolve(self,*args): raise AccessRestricted('平台禁止访问')
    i=store.add('https://live.douyin.com/1'); m=Monitor(store,tmp_path,Restricted(),lambda p:10**12)
    m.start(i); await wait_until(lambda:not store.task(i)['enabled']); assert m.states[i]=='解析失败'; await m.stop(i)

async def test_streamget_adapter_contract(monkeypatch):
    import streamget
    class Fake:
        async def fetch_web_stream_data(self,url): return {'status':2,'id_str':'session123','live_url':'https://live.douyin.com/777','title':'t'}
        async def fetch_app_stream_data(self,url): return await self.fetch_web_stream_data(url)
        async def fetch_stream_url(self,raw,quality):
            from types import SimpleNamespace
            return SimpleNamespace(anchor_name='test',title='t',is_live=True,record_url='https://example.com/live.m3u8',quality=quality)
    monkeypatch.setattr(streamget,'DouyinLiveStream',Fake)
    import core.stream_resolver as module
    monkeypatch.setattr('utils.runtime.binary',lambda name:'/node')
    for url in ['https://live.douyin.com/777','https://v.douyin.com/foo','https://www.douyin.com/user/foo']:
        result=await StreamResolver().resolve(url,'HD'); assert result.room_id=='777' and result.live and result.quality=='HD'

async def test_shutdown_preserves_resume_intent(store,tmp_path):
    i=store.add('https://live.douyin.com/1',enabled=1); r=Resolver()
    store.set_setting('request_spacing',0)
    m=Monitor(store,tmp_path,r,lambda p:10**12); m.resume()
    await wait_until(lambda:m.states.get(i)=='未开播'); await m.shutdown()
    assert store.task(i)['enabled']==1
    m2=Monitor(store,tmp_path,r,lambda p:10**12); m2.resume()
    await wait_until(lambda:m2.states.get(i)=='未开播'); await m2.stop(i)
    assert store.task(i)['enabled']==0

async def test_live_to_offline_finalizes(video,store,tmp_path):
    i=store.add('https://live.douyin.com/1'); r=Resolver(video); r.live=True
    store.set_setting('request_spacing',0); store.set_setting('interval',.1)
    m=Monitor(store,tmp_path,r,lambda p:10**12,tick=.05); m.start(i)
    await wait_until(lambda:m.states.get(i)=='录制中'); await asyncio.sleep(2)
    r.live=False; await wait_until(lambda:m.states.get(i)=='未开播')
    assert not m.sessions and store.recordings()[0]['status']=='录制完成'; await m.stop(i)

async def test_split_log_redaction():
    from core.process_manager import capture
    from utils.runtime import SafeFormatter
    import io
    stream=asyncio.StreamReader(); output=io.StringIO(); logger=logging.getLogger('test-redact')
    handler=logging.StreamHandler(output); handler.setFormatter(SafeFormatter('%(message)s')); logger.addHandler(handler); logger.setLevel(logging.WARNING)
    reader=asyncio.create_task(capture(stream,logger))
    stream.feed_data(b'Cookie: tok'); await asyncio.sleep(0)
    stream.feed_data(b'en=SECRET\n'); stream.feed_eof(); await reader
    assert 'SECRET' not in output.getvalue(); logger.removeHandler(handler)

async def test_unknown_platform_status_rejected(monkeypatch):
    import streamget
    class Fake:
        async def fetch_web_stream_data(self,url): return {'anchor_name':'test'}
    monkeypatch.setattr(streamget,'DouyinLiveStream',Fake)
    monkeypatch.setattr('utils.runtime.binary',lambda name:'/node')
    with pytest.raises(RuntimeError): await StreamResolver().resolve('https://live.douyin.com/1')
