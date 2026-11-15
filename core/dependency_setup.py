"""Pinned, verified user-side FFmpeg provisioning. No installer or admin rights."""
import hashlib, os, ssl, tempfile, urllib.request, zipfile, shutil
from pathlib import Path
from utils.runtime import binary, root_dir

FFMPEG_URL='https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-essentials_build.zip'
FFMPEG_SHA256='db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec'
MAX_DOWNLOAD=160*1024*1024

def install_ffmpeg(progress=None):
    if binary('ffmpeg') and binary('ffprobe'): return
    if os.name!='nt': raise RuntimeError('自动准备组件只适用于 Windows')
    import certifi
    tools=root_dir()/'tools'; tools.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prepare-',dir=tools) as temp:
        archive=Path(temp)/'ffmpeg.zip'; digest=hashlib.sha256(); size=0
        request=urllib.request.Request(FFMPEG_URL,headers={'User-Agent':'LiveWatch/0.1.1'})
        with urllib.request.urlopen(request,timeout=60,context=ssl.create_default_context(cafile=certifi.where())) as response, archive.open('wb') as out:
            while block:=response.read(1024*1024):
                size+=len(block)
                if size>MAX_DOWNLOAD: raise RuntimeError('组件下载超出预期大小，已中止')
                digest.update(block); out.write(block)
                if progress: progress(size)
        if digest.hexdigest()!=FFMPEG_SHA256: raise RuntimeError('录制组件校验失败，未安装，请稍后重试')
        extract_verified(archive,tools)

def extract_verified(archive,tools):
    tools=Path(tools)
    with zipfile.ZipFile(archive) as z:
        binaries={}
        for name in ('ffmpeg.exe','ffprobe.exe'):
            matches=[n for n in z.namelist() if n.endswith('/bin/'+name)]
            if len(matches)!=1: raise RuntimeError('组件压缩包结构不符合预期')
            data=z.read(matches[0])
            if not data.startswith(b'MZ'): raise RuntimeError('组件不是 Windows 可执行文件')
            binaries[name]=data
        for name,data in binaries.items():
            pending=tools/(name+'.pending'); pending.write_bytes(data); pending.replace(tools/name)
        notices=tools/'ffmpeg-licenses'; notices.mkdir(exist_ok=True)
        for n in z.namelist():
            if Path(n).name.lower() in ('license','license.txt','readme','readme.txt'):
                (notices/Path(n).name).write_bytes(z.read(n))
        (notices/'SOURCE.txt').write_text('User-side download, unmodified Gyan FFmpeg 8.1.2 essentials build.\nDownload: '+FFMPEG_URL+'\nSHA256: '+FFMPEG_SHA256+'\nBuild information: https://www.gyan.dev/ffmpeg/builds/\nSource: https://ffmpeg.org/download.html#get-sources\n',encoding='utf-8')
