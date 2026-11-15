import asyncio, logging, shutil, sqlite3, time
from pathlib import Path
from core.stream_resolver import StreamResolver, AccessRestricted
from core.recorder import RecordingSession
from utils.runtime import binary

log = logging.getLogger('livewatch.app')

class Monitor:
    def __init__(self, store, root, resolver=None, disk_free=None, tick=1):
        self.store=store; self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.resolver=resolver or StreamResolver(); self.jobs={}; self.sessions={}; self.states={}; self.details={}
        self.disk_free=disk_free or (lambda p: shutil.disk_usage(p).free); self.tick=tick
        self._next_request=0.; self._request_lock=asyncio.Lock(); self.closing=False
    def state(self, ident, status, detail=''):
        self.states[ident]=status; self.details[ident]=detail
    def start(self, ident):
        if ident in self.jobs and not self.jobs[ident][0].done(): return
        self.store.update(ident,enabled=1); event=asyncio.Event()
        self.jobs[ident]=(asyncio.create_task(self._run(ident,event)),event)
    async def stop(self, ident, persist=True):
        if persist: self.store.update(ident,enabled=0)
        pair=self.jobs.get(ident)
        if pair:
            pair[1].set(); await pair[0]; self.jobs.pop(ident,None)
        self.state(ident,'已停止')
    def start_all(self):
        for task in self.store.tasks(): self.start(task['id'])
    async def stop_all(self, persist=True):
        await asyncio.gather(*(self.stop(i,persist) for i in list(self.jobs)))
    async def shutdown(self):
        self.closing=True; await self.stop_all(False)
    def resume(self):
        for task in self.store.tasks():
            if task['enabled']: self.start(task['id'])
    async def sleep(self, event, seconds):
        try: await asyncio.wait_for(event.wait(),seconds)
        except asyncio.TimeoutError: pass
    async def resolve(self, task):
        # Global spacing plus bounded request duration. All tasks share one gate.
        async with self._request_lock:
            await asyncio.sleep(max(0,self._next_request-time.monotonic()))
            self._next_request=time.monotonic()+self.store.setting('request_spacing',3)
        return await asyncio.wait_for(self.resolver.resolve(task['url'],task['quality']),50)
    async def _run(self, ident, event):
        session=None; failures=0; reason='已停止'; last_check=0
        self.state(ident,'待监控')
        try:
            while not event.is_set():
                task=self.store.task(ident)
                root=Path(task['directory'] or self.store.setting('directory',str(self.root))); root.mkdir(parents=True,exist_ok=True)
                if self.disk_free(root)<self.store.setting('min_free_gb',5)*1024**3:
                    reason='磁盘空间不足，已安全停止'; self.store.update(ident,enabled=0); self.state(ident,'已停止',reason)
                    if session: session.event('disk_low')
                    break
                if session and session.process and session.process.returncode is None:
                    if time.monotonic()-last_check < self.store.setting('interval',120):
                        await self.sleep(event,self.tick); continue
                    try:
                        info=await self.resolve(task); last_check=time.monotonic()
                        if not info.live:
                            await session.finish('录制完成'); self.sessions.pop(ident,None); session=None
                            self.state(ident,'未开播'); await self.sleep(event,self.store.setting('interval',120))
                    except AccessRestricted:
                        self.store.update(ident,enabled=0); reason='平台限制访问'; self.state(ident,'解析失败',reason); break
                    except Exception as exc:
                        # Keep healthy recorder alive on status-request failure.
                        last_check=time.monotonic(); self.details[ident]=str(exc)
                    continue
                if session and session.process:
                    await session.stop_process(); session.event('interruption',exit_code=session.process.returncode)
                    session.process=None; self.state(ident,'正在重连'); failures+=1
                    await self.sleep(event,min(300,5*2**min(failures-1,6)))
                    if event.is_set(): break
                try:
                    if not session and len(self.sessions)>=self.store.setting('concurrency',3):
                        self.state(ident,'待监控','已达到并发上限'); await self.sleep(event,self.tick); continue
                    info=await self.resolve(task)
                    if event.is_set(): break
                    try: self.store.update(ident,room_id=info.room_id,name=info.name,title=info.title)
                    except sqlite3.IntegrityError:
                        self.store.update(ident,enabled=0); reason='与已有主播重复'; self.state(ident,'已停止',reason); break
                    if not info.live:
                        if session: await session.finish('录制完成'); self.sessions.pop(ident,None); session=None
                        failures=0; self.state(ident,'未开播'); await self.sleep(event,self.store.setting('interval',120)); continue
                    if not info.url: raise RuntimeError('已开播但没有可访问的直播流')
                    if not binary('ffmpeg') or not binary('ffprobe'): raise AccessRestricted('缺少 FFmpeg/FFprobe，请先完成依赖安装')
                    # No await between capacity check and reservation.
                    if not session:
                        if len(self.sessions)>=self.store.setting('concurrency',3): continue
                        session=RecordingSession(task,info,root,self.store,self.store.setting('segment_minutes',30)*60,self.store.setting('convert',False),self.store.setting('delete_source',False))
                        self.sessions[ident]=session
                    await session.start(info.url); self.state(ident,'录制中'); last_check=time.monotonic()
                    # Reset backoff only after a stable recording, not immediately on spawn.
                    await self.sleep(event,self.tick)
                    if time.monotonic()-session.clock>60 and session.process.returncode is None: failures=0
                except AccessRestricted as exc:
                    reason=str(exc); self.store.update(ident,enabled=0); self.state(ident,'解析失败',reason); break
                except Exception as exc:
                    failures+=1; self.state(ident,'正在重连' if session else '解析失败',str(exc)); log.exception('任务 %s 失败，第 %s 次重试',ident,failures)
                    await self.sleep(event,min(300,5*2**min(failures-1,6)))
        except Exception as exc:
            reason='任务异常，请查看日志'; self.state(ident,'解析失败',reason); log.exception('任务 %s 意外异常',ident)
        finally:
            if session:
                try: await session.finish(reason)
                except Exception: log.exception('结束任务 %s 时保存失败',ident)
            self.sessions.pop(ident,None)
            if event.is_set(): self.state(ident,'已停止')
