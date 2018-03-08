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

MAPPER_NAME = 'backup_offsite'


class Action(enum.Enum):
    BACKUP = 'backup'
    MOUNT = 'mount'
    UNMOUNT = 'unmount'


class App(object):
    def __init__(self, args):
        self.args = args
        self.external_backup = ExternalBackup(pretend=args.pretend,
                                              config_file=args.config_file)

    def run(self):
        if self.args.action == Action.BACKUP:
            self.external_backup.backup()
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
