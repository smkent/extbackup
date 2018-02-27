import os
import sys

from .mount import Mount
from .mount import MountsTempDir


def require_root():
    if os.getuid():
        os.execvp('sudo', ['sudo'] + sys.argv)
        raise Exception('os.execvp failed')


def main():
    require_root()
    with Mount('/boot'), MountsTempDir() as td:
        td.mount('/')
        td.mount('/boot')
        td.mount('/home')
        print('====')
        print(os.listdir(td.data_dir))
        print(td.data_dir)
        print('====')
