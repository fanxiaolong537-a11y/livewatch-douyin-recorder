from __future__ import annotations
import os, sys, shutil, subprocess, re, json, logging, zipfile
from pathlib import Path
from logging.handlers import RotatingFileHandler

VERSION = '0.1.2'

def root_dir():
    if os.environ.get('LIVEWATCH_ROOT'): return Path(os.environ['LIVEWATCH_ROOT'])
    return Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]

def data_dir():
    p = Path(os.environ.get('LIVEWATCH_HOME', Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'LiveWatch'))
    p.mkdir(parents=True, exist_ok=True)
    return p

def binary(name):
    ext = '.exe' if os.name == 'nt' else ''
    p = root_dir() / 'tools' / (name + ext)
    return str(p) if p.is_file() else shutil.which(name)

def setup_path():
    os.environ['PATH'] = str(root_dir() / 'tools') + os.pathsep + os.environ.get('PATH', '')

def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}

def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f%]', '_', str(value)).strip(' .')[:60] or '未命名'
    if value.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))}:
        value = '_' + value
    return value

def redact(text):
    text = re.sub(r'https?://[^\s\]"\'<>]+', '[URL已脱敏]', str(text), flags=re.I)
    text = re.sub(r'(?im)(cookie|authorization|set-cookie)\s*[:=].*$', r'\1=[已脱敏]', text)
    return re.sub(r'(?i)((?:token|signature|a_bogus|x-bogus|mstoken|ttwid|sessionid)\s*[=:]\s*)[^\s,;&]+', r'\1[已脱敏]', text)

class SafeFormatter(logging.Formatter):
    def format(self, record):
        return redact(super().format(record))

def configure_logs(home):
    logdir = Path(home) / 'logs'; logdir.mkdir(exist_ok=True)
    for name in ('app','parser','recorder'):
        logger = logging.getLogger('livewatch.' + name); logger.setLevel(logging.INFO); logger.propagate = False
        if not logger.handlers:
            handler = RotatingFileHandler(logdir / (name + '.log'), maxBytes=2_000_000, backupCount=3, encoding='utf-8')
            handler.setFormatter(SafeFormatter('%(asctime)s %(levelname)s %(message)s')); logger.addHandler(handler)
    # Upstream may log full requests; disable its independent loguru sinks.
    from loguru import logger
    logger.remove()

def export_diagnostics(home, output):
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in (Path(home) / 'logs').glob('*.log*'):
            z.writestr(p.name, redact(p.read_text(encoding='utf-8', errors='replace')))
        z.writestr('environment.json', json.dumps({'version': VERSION,'platform':sys.platform,'python':sys.version,'dependencies': {n: bool(binary(n)) for n in ('ffmpeg','ffprobe','node')}}, ensure_ascii=False))

def open_path(path, folder=False):
    p = Path(path).resolve()
    if folder and not p.is_dir(): p = p.parent
    if not p.exists(): raise FileNotFoundError(str(p))
    if os.name == 'nt': os.startfile(str(p))
    else: subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(p)])

def autostart(enabled):
    if os.name != 'nt': raise RuntimeError('开机启动仅支持 Windows')
    if not getattr(sys, 'frozen', False) and not os.environ.get('LIVEWATCH_PORTABLE'): raise RuntimeError('请在 EXE 版本中设置开机启动')
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as key:
        if enabled: winreg.SetValueEx(key, 'LiveWatch', 0, winreg.REG_SZ, '"' + str(root_dir()/'LiveWatch.exe' if os.environ.get('LIVEWATCH_PORTABLE') else sys.executable) + '"')
        else:
            try: winreg.DeleteValue(key, 'LiveWatch')
            except FileNotFoundError: pass
