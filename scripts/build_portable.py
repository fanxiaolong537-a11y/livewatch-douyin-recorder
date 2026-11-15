"""Reproducible Windows portable assembly, usable on Linux or Windows.
Prerequisites: Python with pip and `pip install ziglang==0.13.0`.
No account, admin install or GitHub API is used.
"""
import argparse,hashlib,subprocess,sys,urllib.request,shutil,zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from assemble_portable import main as assemble,HASHES
ROOT=Path(__file__).resolve().parents[1]
URLS={
'python.zip':'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',
'flet.zip':'https://github.com/flet-dev/flet/releases/download/v0.85.3/flet-windows.zip',
'node.zip':'https://nodejs.org/dist/v22.20.0/node-v22.20.0-win-x64.zip'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--cache',default=str(ROOT/'build/portable-cache'));p.add_argument('--output',default=str(ROOT/'dist/LiveWatch'));a=p.parse_args()
    cache=Path(a.cache).resolve();out=Path(a.output).resolve();cache.mkdir(parents=True,exist_ok=True)
    def fetch(item):
        name,url=item;dest=cache/name
        if not dest.exists():urllib.request.urlretrieve(url,dest)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=HASHES[name]:raise RuntimeError('Checksum mismatch: '+name)
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,URLS.items()))
    wheels=cache/'wheels';wheels.mkdir(exist_ok=True)
    subprocess.run([sys.executable,'-m','pip','wheel','--no-deps','--wheel-dir',str(wheels),'PyExecJS==1.5.1'],check=True)
    subprocess.run([sys.executable,'-m','pip','download','--no-deps','--find-links',str(wheels),'--dest',str(wheels),'--platform','win_amd64','--python-version','3.11','--implementation','cp','--abi','cp311','--only-binary=:all:','-r',str(ROOT/'requirements-windows-runtime.txt')],check=True)
    subprocess.run([sys.executable,'-m','ziglang','cc','-target','x86_64-windows-gnu','-municode','-Wl,--subsystem,windows','-O2','-s',str(ROOT/'scripts/launcher.c'),'-o',str(cache/'LiveWatch.exe'),'-luser32'],check=True)
    assemble(cache,out)
    print('Built Windows portable files at',out,'; verify on Windows before claiming native test success.')
if __name__=='__main__':main()
