"""Windows one-dir packaging, adapted from StreamCap scripts/build.py.
Copyright (c) Hmily, Apache-2.0. Changes: LiveWatch resources, license inventory,
no FFmpeg/Node redistribution, explicit Flet client bundling.
"""
import os,sys,subprocess,urllib.request,zipfile,shutil,json,importlib.metadata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.platform!='win32': raise SystemExit('Windows native runner required; cross-build prohibited')
    archive_dir=ROOT/'build/flet_client'; archive_dir.mkdir(parents=True,exist_ok=True)
    archive=archive_dir/'flet-windows.zip'
    url='https://github.com/flet-dev/flet/releases/download/v0.85.3/flet-windows.zip'
    if not archive.exists(): urllib.request.urlretrieve(url,archive)
    unpack=archive_dir/'unpacked'
    with zipfile.ZipFile(archive) as z: z.extractall(unpack)
    executable=next(unpack.rglob('flet.exe'))
    fletdir=executable.parent
    env=os.environ.copy(); env['FLET_VIEW_PATH']=str(fletdir)
    command=[sys.executable,'-m','PyInstaller','--onedir','--windowed','--name','LiveWatch','--clean','--noconfirm',
        '--collect-all','flet_desktop','--collect-data','streamget','--collect-submodules','streamget',
        '--hidden-import','pystray._win32',
        '--add-data',str(fletdir)+';flet_desktop/app/flet',
        '--add-data',str(ROOT/'licenses')+';licenses',str(ROOT/'main.py')]
    subprocess.run(command,cwd=ROOT,env=env,check=True)
    output=ROOT/'dist/LiveWatch'
    for name in ['README.md','LICENSE','THIRD_PARTY_NOTICES.md']:
        shutil.copy(ROOT/name,output/name)
    shutil.copytree(ROOT/'docs',output/'docs',dirs_exist_ok=True)
    shutil.copytree(ROOT/'licenses',output/'licenses',dirs_exist_ok=True)
    # Include installed wheel license texts, not only a handwritten dependency list.
    inventory=[]
    for dist in importlib.metadata.distributions():
        name=dist.metadata['Name']; inventory.append({'name':name,'version':dist.version,'license':dist.metadata.get('License-Expression') or dist.metadata.get('License','')})
        for entry in dist.files or []:
            if any(k in str(entry).lower() for k in ('license','notice','copying')):
                source=Path(dist.locate_file(entry))
                if source.is_file():
                    dest=output/'licenses'/'python'/name/str(entry).replace('..','_')
                    dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy(source,dest)
    (output/'licenses'/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'tools').mkdir(exist_ok=True)
    (output/'tools'/'安装依赖.txt').write_text('放入自行从可信官方来源获取的 ffmpeg.exe、ffprobe.exe 和 node.exe。详见 README。\n本压缩包不分发这些二进制。',encoding='utf-8')

if __name__=='__main__': main()
