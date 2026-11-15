"""Package runtime resources without accidentally dropping Flutter's data directory."""
import argparse,hashlib,zipfile
from pathlib import Path

def package(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    expected={}
    for path in root.rglob('*'):
        relative=path.relative_to(root)
        if not path.is_file() or relative.parts[0]=='data' or '__pycache__' in relative.parts:continue
        expected['LiveWatch/'+relative.as_posix()]=path
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(expected.items()):z.write(path,name)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(expected)
        for name in ('LiveWatch.exe','_desktop/data/icudtl.dat','_desktop/data/app.so','_runtime/python311.zip','_app/main.py','tools/node.exe'):
            assert 'LiveWatch/'+name in z.namelist(),name
        for name,path in expected.items():assert z.getinfo(name).file_size==path.stat().st_size
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.sha256.txt').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    return digest,len(expected)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('output');a=p.parse_args();print(package(a.root,a.output))
