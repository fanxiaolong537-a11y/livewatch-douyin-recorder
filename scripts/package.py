import shutil,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=Path(shutil.make_archive(str(root/'dist/LiveWatch-Windows-x64'),'zip',root/'dist','LiveWatch'))
(root/'dist/SHA256SUMS.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n',encoding='ascii')
