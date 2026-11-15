"""Offline Windows PE, ABI, DLL and resource package validation; not OS execution."""
import struct,sys,json,subprocess
from pathlib import Path
root=Path(sys.argv[1]).resolve()
def pe(path):
    data=path.read_bytes();assert data[:2]==b'MZ',str(path)
    at=struct.unpack_from('<I',data,0x3c)[0]; assert data[at:at+4]==b'PE\0\0'
    machine=struct.unpack_from('<H',data,at+4)[0]; assert machine==0x8664,(path,machine)
    return struct.unpack_from('<H',data,at+24+68)[0]
assert pe(root/'LiveWatch.exe')==2,'Launcher must be Windows GUI subsystem'
for p in [root/'_runtime/pythonw.exe',root/'_desktop/flet.exe',root/'tools/node.exe']:pe(p)
checked=0
for p in (root/'_runtime').rglob('*.pyd'):pe(p);checked+=1
for n in ['_app/main.py','_runtime/python311.dll','_runtime/python311.zip','_desktop/flutter_windows.dll','_desktop/data/icudtl.dat','_runtime/site-packages/streamget/js','licenses/Node-LICENSE.txt']:
    assert (root/n).exists(),n
pth=(root/'_runtime/python311._pth').read_text();assert '../_app' in pth and 'site-packages' in pth
# Verify every third-party DLL directly imported by the Flet frontend is shipped.
text=subprocess.check_output(['objdump','-p',str(root/'_desktop/flet.exe')],text=True)
shipped={p.name.lower() for p in (root/'_desktop').glob('*.dll')}
for line in text.splitlines():
    if 'DLL Name:' in line:
        name=line.split(':',1)[1].strip().lower()
        if name.endswith('_plugin.dll') or name.startswith(('flutter_','vcruntime','msvcp')):assert name in shipped,name
print(json.dumps({'pe_architecture':'x86_64','launcher_subsystem':'Windows GUI','pyd_modules_checked':checked,'resources':'PASS','direct_gui_dlls':'PASS','windows_execution':'NOT VERIFIED'},indent=2))
