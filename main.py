import os, sys, json, argparse
from pathlib import Path
from utils.runtime import setup_path, binary, data_dir, VERSION

def lock_instance(home):
    handle=open(home/'instance.lock','a+b')
    try:
        if os.name=='nt':
            import msvcrt
            handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0); msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close(); raise RuntimeError('LiveWatch 已在运行，请从系统托盘打开')
    return handle

def main():
    import multiprocessing
    multiprocessing.freeze_support(); setup_path()
    parser=argparse.ArgumentParser(); parser.add_argument('--self-test',action='store_true'); parser.add_argument('--report'); args=parser.parse_args()
    if args.self_test:
        import flet, streamget
        from ui.desktop import Desktop
        from core.recorder import CaptureBuilder
        report={'version':VERSION,'imports':'ok','dependencies':{n:bool(binary(n)) for n in ('ffmpeg','ffprobe','node')}}
        if args.report: Path(args.report).write_text(json.dumps(report),encoding='utf-8')
        elif sys.stdout: print(json.dumps(report))
        return
    try: instance=lock_instance(data_dir())
    except RuntimeError as exc:
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,str(exc),'LiveWatch',0)
        else: print(str(exc))
        return
    if getattr(sys, 'frozen', False):
        view = Path(sys._MEIPASS) / 'flet_desktop/app/flet'
        if (view / 'flet.exe').is_file(): os.environ['FLET_VIEW_PATH'] = str(view)
    import flet as ft
    from ui.desktop import main as desktop_main
    ft.run(desktop_main)
    instance.close()

if __name__=='__main__': main()
