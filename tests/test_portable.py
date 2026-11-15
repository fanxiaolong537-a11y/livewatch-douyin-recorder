import zipfile
from pathlib import Path
import pytest
from core.dependency_setup import extract_verified

def test_safe_extract_only_expected_files(tmp_path):
    archive=tmp_path/'component.zip'; tools=tmp_path/'tools'; tools.mkdir()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('ffmpeg/bin/ffmpeg.exe',b'MZffmpeg');z.writestr('ffmpeg/bin/ffprobe.exe',b'MZffprobe')
        z.writestr('../../unexpected.exe',b'MZbad');z.writestr('ffmpeg/LICENSE',b'license text')
    extract_verified(archive,tools)
    assert (tools/'ffmpeg.exe').read_bytes()==b'MZffmpeg'
    assert (tools/'ffprobe.exe').exists() and not (tmp_path/'unexpected.exe').exists()
    assert (tools/'ffmpeg-licenses/LICENSE').exists()

@pytest.mark.parametrize('kind',['missing','invalid','duplicate'])
def test_bad_component_never_installs(tmp_path,kind):
    archive=tmp_path/'component.zip';tools=tmp_path/'tools';tools.mkdir()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('pkg/bin/ffmpeg.exe',b'invalid' if kind=='invalid' else b'MZgood')
        if kind!='missing':z.writestr('pkg/bin/ffprobe.exe',b'MZgood')
        if kind=='duplicate':z.writestr('pkg2/bin/ffmpeg.exe',b'MZanother')
    with pytest.raises(RuntimeError):extract_verified(archive,tools)
    assert not list(tools.glob('*.exe'))

def test_portable_root(monkeypatch,tmp_path):
    from utils.runtime import root_dir
    monkeypatch.setenv('LIVEWATCH_ROOT',str(tmp_path));assert root_dir()==tmp_path
