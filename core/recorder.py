import asyncio, json, logging, uuid, time
from datetime import datetime
from pathlib import Path
from vendor.streamcap.video.ts import TSCommandBuilder
from core.process_manager import spawn, stop, capture
from core.video_processor import probe, remux
from utils.runtime import binary, safe_name

log = logging.getLogger('livewatch.recorder')
def now(): return datetime.now().astimezone().isoformat(timespec='seconds')

class CaptureBuilder(TSCommandBuilder):
    """Reuse StreamCap's segment/codec output builder with a bounded input policy.
    Original base retained for attribution. Drop automatic stale-URL reconnect,
    overwrite and unrestricted input protocols; monitor owns fresh-URL retries.
    """
    def _get_basic_ffmpeg_command(self):
        args = [binary('ffmpeg'),'-n','-hide_banner','-loglevel','warning']
        if self.record_url.startswith(('http://','https://')):
            args += ['-rw_timeout','15000000','-user_agent','Mozilla/5.0','-referer','https://live.douyin.com/','-protocol_whitelist','http,https,tcp,tls,crypto']
        else: args += ['-re']  # local authorized integration fixtures
        return args + ['-i',self.record_url,'-sn','-dn']

class RecordingSession:
    def __init__(self, task, info, root, store, segment_seconds=1800, convert=False, delete_source=False):
        self.task = task; self.info = info; self.store = store; self.segment_seconds = segment_seconds
        self.convert = convert; self.delete_source = delete_source; self.process = None; self.reader = None
        self.id = uuid.uuid4().hex; self.started = now(); self.clock = time.monotonic(); self.attempt = 0
        dt = datetime.now(); name = safe_name(info.name)
        self.directory = Path(root) / name / dt.strftime('%Y-%m-%d') / (dt.strftime('%H%M%S')+'_'+self.id[:8])
        self.directory.mkdir(parents=True, exist_ok=False)
        self.prefix = name + '_' + dt.strftime('%Y%m%d_%H%M%S')
        self.meta = {'schema_version':1,'session_id':self.id,'anchor_name':info.name,'room_id':info.room_id,'title':info.title,'started':self.started,'ended':None,'duration':0,'video_files':[],'segments':[],'events':[],'status':'录制中','quality_requested':task['quality']}
        self.record = dict(id=self.id,task_id=task['id'],name=info.name,title=info.title,started=self.started,ended=None,duration=0,size=0,quality=task['quality'],path=str(self.directory / 'metadata.json'),status='录制中')
        self.persist()
    def persist(self):
        temp = self.directory / 'metadata.tmp'
        temp.write_text(json.dumps(self.meta,ensure_ascii=False,indent=2),encoding='utf-8'); temp.replace(self.directory/'metadata.json')
        self.store.save_recording(self.record)
    def event(self, kind, **details):
        self.meta['events'].append({'time':now(),'type':kind,**details}); self.persist()
    async def start(self, url):
        if self.process and self.process.returncode is None: raise RuntimeError('拒绝重复录制进程')
        if not binary('ffmpeg') or not binary('ffprobe'): raise RuntimeError('缺少 FFmpeg/FFprobe')
        self.attempt += 1
        pattern = self.directory / f'{self.prefix}_r{self.attempt:03d}_%04d.ts'
        builder = CaptureBuilder(url,segment_record=True,segment_time=str(self.segment_seconds),full_path=str(pattern))
        command = builder.build_command()
        # Only video/audio, no platform data/subtitle tracks.
        idx = command.index('-map'); command[idx:idx+2] = ['-map','0:v:0','-map','0:a?']
        self.process = await spawn(command)
        self.reader = asyncio.create_task(capture(self.process.stderr,log))
        self.event('start' if self.attempt == 1 else 'reconnect',attempt=self.attempt)
        log.info('录制启动 task=%s session=%s attempt=%s',self.task['id'],self.id,self.attempt)
    async def stop_process(self):
        if self.process: await stop(self.process)
        if self.reader: await self.reader
    def size(self): return sum(p.stat().st_size for p in self.directory.glob('*') if p.suffix in ('.ts','.mp4'))
    async def finish(self, status):
        await self.stop_process()
        segments=[]
        for p in sorted(self.directory.glob('*.ts')):
            entry={'path':str(p),'status':'有效'}
            try:
                entry.update(await probe(p))
                if self.convert:
                    try:
                        dest = await remux(p,self.delete_source); entry['path']=str(dest); entry['source_retained']=p.exists()
                        log.info('转封装成功 session=%s file=%s',self.id,dest.name)
                    except Exception as exc:
                        entry['remux_error']='转封装失败，保留 TS'; log.exception('转封装失败 session=%s',self.id)
            except Exception:
                entry['status']='检测失败，保留文件'; log.exception('视频检测失败 session=%s',self.id)
            segments.append(entry)
        duration=sum(s.get('duration',0) for s in segments)
        if not segments or any(s['status']!='有效' for s in segments): status='文件异常（需检查）'
        self.meta.update(ended=now(),duration=duration,segments=segments,video_files=[s['path'] for s in segments],status=status)
        self.record.update(ended=self.meta['ended'],duration=duration,size=self.size(),status=status)
        self.persist(); log.info('录制结束 session=%s status=%s',self.id,status)
