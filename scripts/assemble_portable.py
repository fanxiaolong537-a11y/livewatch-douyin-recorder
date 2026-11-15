"""Assemble genuine Windows PE runtime and wheels; this is not PyInstaller cross-build.
Requires downloaded, pinned assets and cross-compiled launcher.c. Does not claim
Windows-native testing. FFmpeg is downloaded by the user-side first-run wizard.
"""
import json,zipfile,hashlib,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HASHES={
'python.zip':'009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b',
'flet.zip':'4c0a3f74f7b277e685aad1c584440cfcab4e0fba4068b6537be511c533feff4e',
'node.zip':'bb819d6eb8f5bfda294bbc83a7e4ec6539da67c4233d54b0d655b9248b15e29d'}
def main(cache,out):
    cache=Path(cache).resolve(); out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
    manifest={'version':'0.1.2','assembly':'Windows embeddable Python + native PE launcher','assets':HASHES,'wheels':{}}
    for name,digest in HASHES.items():
        if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=digest: raise RuntimeError('Asset checksum mismatch: '+name)
    runtime=out/'_runtime'; runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(cache/'python.zip') as z: z.extractall(runtime)
    (runtime/'python311._pth').write_text('python311.zip\n.\nsite-packages\n../_app\nimport site\n',encoding='ascii')
    packages=runtime/'site-packages'; packages.mkdir(exist_ok=True)
    for wheel in sorted((cache/'wheels').glob('*.whl')):
        manifest['wheels'][wheel.name]=hashlib.sha256(wheel.read_bytes()).hexdigest()
        with zipfile.ZipFile(wheel) as z:
            for member in z.namelist():
                if member.endswith('/'):continue
                parts=Path(member).parts
                if any(p in ('..','') for p in parts):raise ValueError('Unsafe wheel path')
                if '.data/' in member:
                    head,kind,*rest=parts
                    if kind not in ('purelib','platlib'):continue
                    target=packages.joinpath(*rest)
                else:target=packages/member
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
    desktop=out/'_desktop';desktop.mkdir(exist_ok=True)
    with zipfile.ZipFile(cache/'flet.zip') as z:
        entry=next(n for n in z.namelist() if n.endswith('flet.exe')); prefix=entry[:-len('flet.exe')]
        for n in z.namelist():
            if n.startswith(prefix) and not n.endswith('/'):
                target=desktop/n[len(prefix):];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(n))
    tools=out/'tools';tools.mkdir(exist_ok=True)
    with zipfile.ZipFile(cache/'node.zip') as z:
        for suffix,dest in [('/node.exe',tools/'node.exe'),('/LICENSE',out/'licenses/Node-LICENSE.txt')]:
            name=next(n for n in z.namelist() if n.endswith(suffix));dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(name))
    app=out/'_app';app.mkdir(exist_ok=True)
    for folder in ('app','core','storage','ui','utils','vendor'):
        shutil.copytree(ROOT/folder,app/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy(ROOT/'main.py',app/'main.py');shutil.copy(cache/'LiveWatch.exe',out/'LiveWatch.exe')
    shutil.copytree(ROOT/'licenses',out/'licenses',dirs_exist_ok=True)
    for f in ('LICENSE','THIRD_PARTY_NOTICES.md','README.md'):shutil.copy(ROOT/f,out/f)
    shutil.copytree(ROOT/'docs',out/'docs',dirs_exist_ok=True)
    for wheel in (cache/'wheels').glob('*.whl'):
        with zipfile.ZipFile(wheel) as z:
            for name in z.namelist():
                if not name.endswith('/') and any(x in Path(name).name.lower() for x in ('license','copying','notice')):
                    target=out/'licenses/wheels'/wheel.stem/Path(name).name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
    source=out/'源码与构建';source.mkdir(exist_ok=True)
    for folder in ('app','core','storage','ui','utils','vendor','scripts','tests','docs','licenses','.github'):
        shutil.copytree(ROOT/folder,source/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path in ROOT.iterdir():
        if path.is_file() and (path.suffix in ('.py','.txt','.md','.ps1','.toml') or path.name in ('LICENSE','.gitignore')):
            shutil.copy(path,source/path.name)
    (out/'BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.cache,a.output)
