import os,sys,subprocess,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    if sys.platform!='win32': raise SystemExit('Windows only')
    exe=ROOT/'dist/LiveWatch/LiveWatch.exe'
    with tempfile.TemporaryDirectory(prefix='LiveWatch 中文 空格 ') as td:
        report=Path(td)/'smoke.json'; env=os.environ.copy(); env['LIVEWATCH_HOME']=td
        subprocess.run([str(exe),'--self-test','--report',str(report)],env=env,check=True,timeout=90)
        result=json.loads(report.read_text(encoding='utf-8')); assert result['imports']=='ok'
        assert all(result['dependencies'].values()),'CI must have FFmpeg, FFprobe and Node on PATH'
        marker=Path(td)/'gui.txt'; env['LIVEWATCH_GUI_SMOKE']=str(marker)
        subprocess.run([str(exe)],env=env,check=True,timeout=90)
        assert marker.exists(),'Flet client did not mount and render the four pages'
        # No external tools on PATH: dependency detection must explain missing tools, not crash.
        cleanenv=env.copy(); cleanenv['PATH']=os.environ.get('SystemRoot',r'C:\Windows')+r'\System32'
        missing=Path(td)/'missing.json'
        subprocess.run([str(exe),'--self-test','--report',str(missing)],env=cleanenv,check=True,timeout=90)
        deps=json.loads(missing.read_text(encoding='utf-8'))['dependencies']
        assert deps['node'] and not deps['ffmpeg'] and not deps['ffprobe']
    print('Windows frozen import, dependency checks, real Flet GUI mount: PASS')
if __name__=='__main__': main()
