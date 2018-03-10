import argparse
import enum
import os
import stat
import subprocess
import sys

from .backup import ExternalBackup
from .backup import MOUNT_DIR
from .mount import mount
from .mount import unmount

MAPPER_NAME = 'backup-external'


class Action(enum.Enum):
    BACKUP = 'backup'
    CREATE = 'create'
    MOUNT = 'mount'
    UNMOUNT = 'unmount'


class App(object):
    def __init__(self, args):
        self.args = args

    def run(self):
        if self.args.action == Action.BACKUP:
            eb = ExternalBackup(pretend=self.args.pretend,
                                config_file=self.args.config_file)
            eb.backup()
        if self.args.action == Action.CREATE:
            self._check_device()
            self._create()
        if self.args.action == Action.MOUNT:
            self._check_device()
            self._unlock()
            self._mount()
        if self.args.action == Action.UNMOUNT:
            self._unmount()
            self._lock()

    def _mapper_path(self):
        return os.path.join('/dev', 'mapper', MAPPER_NAME)

    def _check_device(self):
        if not self.args.device:
            raise Exception('No device specified')
        if not os.path.exists(self.args.device):
            raise Exception('{} does not exist'.format(self.args.device))
        if not stat.S_ISBLK(os.stat(self.args.device).st_mode):
            raise Exception('{} is not a block device')

    def _create(self):
        if os.path.ismount(MOUNT_DIR):
            raise Exception('{} is already mounted'.format(MOUNT_DIR))
        if os.path.exists(self._mapper_path()):
            raise Exception('{} is already in use'.format(self._mapper_path()))
        subprocess.check_call(['cryptsetup', '-y',
                               '--cipher', 'aes-xts-plain64:sha512',
                               '--hash', 'sha512',
                               '--key-size', '512',
                               'luksFormat', self.args.device])
        self._unlock()
        subprocess.check_call(['mkfs.ext4', self._mapper_path()])
        subprocess.check_call(['tune2fs', '-m', '0', self._mapper_path()])
        self._lock()

    def _unlock(self):
        if not os.path.exists(self._mapper_path()):
            subprocess.check_call(['cryptsetup', 'luksOpen',
                                   self.args.device, MAPPER_NAME])
            print('Started {}'.format(self._mapper_path()))

    def _lock(self):
        if os.path.exists(self._mapper_path()):
            print('Closing {}'.format(self._mapper_path()))
            subprocess.check_call(['cryptsetup', 'luksClose', MAPPER_NAME])

    def _unmount(self):
        if os.path.ismount(MOUNT_DIR):
            unmount(MOUNT_DIR)
            print('Removing {}'.format(MOUNT_DIR))
            os.rmdir(MOUNT_DIR)

    def _mount(self):
        if not os.path.isdir(MOUNT_DIR):
            print('Creating {}'.format(MOUNT_DIR))
            os.mkdir(MOUNT_DIR)
        if not os.path.ismount(MOUNT_DIR):
            mount(MOUNT_DIR, source=self._mapper_path())


def _require_root():
    if os.getuid():
        os.execvp('sudo', ['sudo'] + sys.argv)
        raise Exception('os.execvp failed')


def main():
    ap = argparse.ArgumentParser(description='External disk backup tool')
    ap.add_argument('-c', '--config', dest='config_file', metavar='file',
                    default=os.path.join(
                        os.path.expanduser('~'), '.extbackup'),
                    help=('rsync include/exclude paths config file '
                          '(default: %(default)s)'))
    ap.add_argument('-d', '--device', dest='device', metavar='dev',
                    help='Device to mount')
    ap.add_argument('-p', '--pretend', dest='pretend', action='store_true',
                    help='Perform a backup dry run')
    ap.add_argument('action',  type=Action,
                    help=('Action to perform (choices: {})'
                          .format(' '.join([a.value for a in Action]))))
    args = ap.parse_args()

    _require_root()

    app = App(args)
    app.run()
