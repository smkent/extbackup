import os
import sys
import subprocess
import tempfile

from .mount import Mount
from .mount import BindMounts


def require_root():
    if os.getuid():
        os.execvp('sudo', ['sudo'] + sys.argv)
        raise Exception('os.execvp failed')


def main():
    require_root()
    with Mount('/boot'), BindMounts() as bind, \
            tempfile.TemporaryDirectory() as temp_dir:
        bind.mount('/')
        bind.mount('/boot')
        bind.mount('/home')
        print('====')
        print(temp_dir)
        subprocess.check_call(['touch',
                               os.path.join(temp_dir, 'lame.txt')])
        print(os.listdir(bind.temp_dir))
        print(os.listdir(temp_dir))
        print('====')
