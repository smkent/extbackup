import argparse
import enum
import os
import stat
import subprocess
import sys
import tempfile

from .mount import mount
from .mount import unmount
from .mount import Mount
from .mount import BindMounts

MAPPER_NAME = 'backup_offsite'
MOUNT_DIR = '/mnt/backup-offsite'


class Action(enum.Enum):
    BACKUP = 'backup'
    MOUNT = 'mount'
    UNMOUNT = 'unmount'


def _require_root():
    if os.getuid():
        os.execvp('sudo', ['sudo'] + sys.argv)
        raise Exception('os.execvp failed')


class ExternalBackup(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        if self.args.action == Action.BACKUP:
            self._backup()
        if self.args.action == Action.MOUNT:
            self._mount()
        if self.args.action == Action.UNMOUNT:
            self._unmount()

    def _mapper_path(self):
        return os.path.join('/dev', 'mapper', MAPPER_NAME)

    def _unmount(self):
        if os.path.ismount(MOUNT_DIR):
            unmount(MOUNT_DIR)
        if os.path.exists(self._mapper_path()):
            print('Closing {}'.format(self._mapper_path()))
            subprocess.check_call(['cryptsetup', 'luksClose', MAPPER_NAME])

    def _mount(self):
        if not self.args.device:
            raise Exception('No device specified')
        if not os.path.exists(self.args.device):
            raise Exception('{} does not exist'.format(self.args.device))
        if not stat.S_ISBLK(os.stat(self.args.device).st_mode):
            raise Exception('{} is not a block device')
        if not os.path.exists(self._mapper_path()):
            subprocess.check_call(['cryptsetup', 'luksOpen',
                                   self.args.device, MAPPER_NAME])
            print('Started {}'.format(self._mapper_path()))
        mount(MOUNT_DIR, source=self._mapper_path())

    def _backup(self):
        if not os.path.ismount(MOUNT_DIR):
            raise Exception('{} is not mounted'.format(MOUNT_DIR))
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
            for mount_dir in os.listdir(bind.temp_dir):
                print('{} -> {}'
                      .format(mount_dir,
                              os.listdir(os.path.join(bind.temp_dir,
                                                      mount_dir))))
            print(os.listdir(temp_dir))
            print('====')


def main():
    ap = argparse.ArgumentParser(description='External disk backup tool')
    ap.add_argument('-d', '--device', dest='device', metavar='dev',
                    help='Device to mount')
    ap.add_argument('action',  type=Action,
                    help=('Action to perform (choices: {})'
                          .format(' '.join([a.value for a in Action]))))
    args = ap.parse_args()

    _require_root()

    eb = ExternalBackup(args)
    eb.run()
