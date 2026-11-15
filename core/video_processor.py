import asyncio, json
from pathlib import Path
from utils.runtime import binary, process_options

async def run(args):
    p = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **process_options())
    try: out, err = await asyncio.wait_for(p.communicate(),120)
    except BaseException:
        p.kill(); await p.wait(); raise
    if p.returncode: raise RuntimeError(err.decode(errors='replace')[-2000:])
    return out

async def probe(path):
    tool = binary('ffprobe')
    if not tool: raise RuntimeError('未找到 FFprobe')
    data = json.loads(await run([tool,'-v','error','-show_format','-show_streams','-of','json',str(path)]))
    video = next((s for s in data['streams'] if s['codec_type']=='video'),None)
    duration = float(data.get('format',{}).get('duration',0))
    if not video or duration <= 0: raise ValueError('视频轨道或时长无效')
    return {'duration':duration,'size':Path(path).stat().st_size,'video_codec':video['codec_name'],'width':video.get('width'),'height':video.get('height'),'frame_rate':video.get('avg_frame_rate'),'audio_tracks':sum(s['codec_type']=='audio' for s in data['streams'])}

async def remux(path, delete_source=False):
    path = Path(path); target = path.with_suffix('.mp4'); temp = path.with_suffix('.partial.mp4')
    if target.exists() or temp.exists(): raise FileExistsError('目标文件已存在，拒绝覆盖')
    original = await probe(path)
    try:
        await run([binary('ffmpeg'),'-n','-v','error','-i',str(path),'-map','0:v:0','-map','0:a?','-c','copy','-movflags','+faststart',str(temp)])
        converted = await probe(temp)
        if abs(converted['duration']-original['duration']) > max(2,original['duration']*.02) or converted['audio_tracks'] != original['audio_tracks']:
            raise ValueError('重新封装后时长或音轨校验失败')
        # Full packet scan, beyond header-only probing. No destructive action on failure.
        await run([binary('ffmpeg'),'-v','error','-xerror','-i',str(temp),'-map','0:v','-map','0:a?','-c','copy','-f','null','-'])
        temp.rename(target)
        if delete_source: path.unlink()
        return target
    except BaseException:
        temp.unlink(missing_ok=True); raise
