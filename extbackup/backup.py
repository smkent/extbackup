import contextlib
import datetime
import os
import shutil
import socket
import subprocess
import sys
import tempfile

from .fstab import fstab_mount_points
from .mount import BindMounts
from .mount import Mount
from .rsync import RsyncPaths

MOUNT_DIR = '/mnt/backup-external'
TIMESTAMP_FORMAT = '%Y%m%d-%H%M'


class ExternalBackup(object):
    def __init__(self, pretend=False, config_file=None):
        self.pretend = pretend
        self.config_file = config_file
        self.mounts = fstab_mount_points()
        self.rsync = None

    @property
    def hostname(self):
        hostname = socket.gethostname()
        if not hostname:
            raise Exception('Unable to determine system hostname')
        return hostname

    @property
    def target(self):
        if not hasattr(self, '_target'):
            if not os.path.ismount(MOUNT_DIR):
                raise Exception('{} is not mounted'.format(MOUNT_DIR))
            target = os.path.join(MOUNT_DIR, self.hostname)
            if not os.path.isdir(target):
                print('Creating directory {}'.format(target))
                os.mkdir(target)
            os.chmod(target, 0o0700)
            self._target = target
        return self._target

    def backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.rsync = RsyncPaths(self.config_file, temp_dir)
            # Mount all required filesystems
            with contextlib.ExitStack() as stack:
                for mount_point in self.mounts:
                    stack.enter_context(Mount(mount_point))
                # Create bind mounts
                with BindMounts(mounts=self.mounts) as bind_mounts:
                    self._backup_run(bind_mounts.temp_dir)

    def _backup_run(self, bind_dir):
        print('Backing up {} to {}'.format(self.hostname, self.target))
        self._backup_versioned(bind_dir)
        self._backup_single(bind_dir)
        self._backup_mysql()

    def _backup_versioned(self, bind_dir):
        versioned_dir = datetime.datetime.now().strftime(TIMESTAMP_FORMAT)
        target = os.path.join(self.target, versioned_dir)
        if os.path.isdir(target):
            raise Exception('{} already exists'.format(target))
        self._runcmd(
            self._rsync_cmd(bind_dir, target,
                            link_dest=self._find_prev_version(),
                            single=False),
            ignore_exit_codes=[24])
        # Copy rsync configuration files to backup directory
        if not self.pretend:
            self.rsync.copy_config(os.path.join(target, 'rsync-config'))

    def _backup_single(self, bind_dir):
        self._runcmd(
            self._rsync_cmd(bind_dir, os.path.join(self.target, 'single'),
                            single=True),
            ignore_exit_codes=[24])

    def _backup_mysql(self):
        if self.pretend:
            return
        try:
            subprocess.check_call(['which', 'mysqldump'],
                                  stderr=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            print('mysqldump not found, skipping MySQL backup')
            return
        with tempfile.TemporaryDirectory() as mysql_dir:
            backup_file = os.path.join(mysql_dir, 'mysqldump.sql')
            with open(backup_file, 'w') as f:
                self._runcmd(['mysqldump', '--all-databases'], stdout=f)
            self._runcmd(['gzip', backup_file])
            backup_file = '{}.gz'.format(backup_file)
            shutil.copy(backup_file, os.path.join(
                self.target, os.path.basename(backup_file)))

    def _find_prev_version(self):
        for fn in sorted(os.listdir(self.target), reverse=True):
            if fn in ['single']:
                continue
            full_path = os.path.join(self.target, fn)
            if os.path.isdir(full_path):
                return full_path

    def _runcmd(self, cmd, stdout=None, ignore_exit_codes=None):
        print('+ {}'.format(' '.join(cmd)), file=sys.stderr)
        try:
            subprocess.check_call(cmd, stdout=stdout)
        except subprocess.CalledProcessError as e:
            if ignore_exit_codes and e.returncode in ignore_exit_codes:
                return
            raise

    def _rsync_cmd(self, source, dest, link_dest=None, single=False):
        rsync_cmd = [
            'ionice', '-c', '3',
            'nice', '-n', '19',
            'rsync', '-P', '-avHSAX', '--numeric-ids',
            '--delete', '--delete-excluded',
        ]
        rsync_cmd += self.rsync.get_exclude_include_args(single)
        if link_dest:
            rsync_cmd.append('--link-dest={}'.format(link_dest))
        # Add trailing slashes to source path
        rsync_cmd += [os.path.join(source, ''), dest]
        if self.pretend:
            rsync_cmd.append('--dry-run')
        return rsync_cmd
