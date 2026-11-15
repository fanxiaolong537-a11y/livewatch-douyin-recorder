"""Real localhost HTTP transport using only generated authorized media."""
import asyncio,threading,time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from core.recorder import RecordingSession
from core.stream_resolver import StreamInfo

async def test_http_stream_recording(video,store,tmp_path):
    payload=video.read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            self.send_response(200); self.send_header('Content-Type','video/mp2t'); self.end_headers()
            try:
                for _ in range(3):
                    for i in range(0,len(payload),188*32):
                        self.wfile.write(payload[i:i+188*32]); self.wfile.flush(); time.sleep(.015)
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    i=store.add('https://live.douyin.com/123'); info=StreamInfo('HTTP 测试','123','自有生成测试流',True)
    session=RecordingSession(store.task(i),info,tmp_path,store,segment_seconds=2)
    try:
        await session.start(f'http://127.0.0.1:{server.server_port}/live.ts')
        await asyncio.sleep(4)
        await session.finish('已停止')
        assert session.meta['duration']>0 and session.meta['segments']
        assert session.meta['segments'][0]['width']==320
    finally:
        await session.stop_process(); await asyncio.to_thread(server.shutdown); server.server_close()

async def test_http_disconnect_recovery(video,store,tmp_path):
    from core.monitor import Monitor
    from tests.test_core import wait_until
    payload=video.read_bytes(); counts={'connections':0,'resolve':0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            counts['connections']+=1
            self.send_response(200); self.send_header('Content-Type','video/mp2t'); self.end_headers()
            # Deliberately close the first HTTP response mid-source, then serve recovery.
            data=payload[:len(payload)//2] if counts['connections']==1 else payload*2
            try:
                for i in range(0,len(data),188*32):
                    self.wfile.write(data[i:i+188*32]); self.wfile.flush(); time.sleep(.008)
            except (BrokenPipeError,ConnectionResetError): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=server.serve_forever,daemon=True).start()
    class Resolve:
        async def resolve(self,url,quality):
            counts['resolve']+=1
            return StreamInfo('网络重连测试','1','本地自有视频',True,f'http://127.0.0.1:{server.server_port}/live.ts?attempt={counts["resolve"]}')
    i=store.add('https://live.douyin.com/1'); store.set_setting('request_spacing',0)
    m=Monitor(store,tmp_path,Resolve(),lambda p:10**12,tick=.05); m.start(i)
    try:
        await wait_until(lambda:i in m.sessions and m.sessions[i].attempt>=2,seconds=16)
        session=m.sessions[i]; await asyncio.sleep(1); await m.stop(i)
        assert counts['connections']>=2 and counts['resolve']>=2
        assert any(e['type']=='interruption' for e in session.meta['events'])
        assert any(e['type']=='reconnect' for e in session.meta['events'])
    finally:
        await m.stop_all(); await asyncio.to_thread(server.shutdown); server.server_close()
