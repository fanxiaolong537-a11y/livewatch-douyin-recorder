import subprocess, shutil
from pathlib import Path
import pytest

@pytest.fixture(scope='session')
def video(tmp_path_factory):
    if not shutil.which('ffmpeg'): pytest.skip('FFmpeg unavailable')
    p=tmp_path_factory.mktemp('media')/'自有测试 视频.ts'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','testsrc2=size=320x180:rate=25','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','12','-c:v','mpeg2video','-g','25','-c:a','mp2','-f','mpegts',str(p)],check=True)
    return p

@pytest.fixture
def store(tmp_path):
    from storage.database import Store
    s=Store(tmp_path/'test.sqlite3'); yield s; s.close()
