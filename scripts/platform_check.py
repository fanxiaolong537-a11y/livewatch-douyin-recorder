"""Explicit opt-in integration test for a user-owned or authorized live room."""
import sys,asyncio,argparse,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.stream_resolver import StreamResolver,clean_url
from core.recorder import RecordingSession
from storage.database import Store
from utils.runtime import setup_path,data_dir,configure_logs

async def check(args):
    setup_path(); home=data_dir(); configure_logs(home)
    info=await StreamResolver().resolve(clean_url(args.url))
    print(json.dumps({'anchor_name':info.name,'room_id':info.room_id,'title':info.title,'is_live':info.live},ensure_ascii=False))
    if info.live and args.seconds:
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.sqlite3'); i=store.add(clean_url(args.url))
            session=RecordingSession(store.task(i),info,Path(args.output).resolve(),store)
            try:
                await session.start(info.url); await asyncio.sleep(args.seconds)
            finally:
                await session.finish('授权平台测试结束'); store.close()
            print('metadata:',session.directory/'metadata.json')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('url'); p.add_argument('--authorized',action='store_true'); p.add_argument('--seconds',type=int,default=15); p.add_argument('--output',default=str(data_dir()/'Recordings'))
    a=p.parse_args()
    if not a.authorized: p.error('必须确认 --authorized：该直播由本人或已授权方提供')
    if not 0<=a.seconds<=300: p.error('seconds must be between 0 and 300')
    asyncio.run(check(a))
