import os
import subprocess
import tempfile


class Mount(object):
    def __init__(self, mount_point):
        self.mount_point = mount_point
        self.should_unmount = False

    def __enter__(self):
        if not os.path.ismount(self.mount_point):
            if not os.path.isdir(self.mount_point):
                raise Exception('{} does not exist'.format(self.mount_point))
            if len(self._list_dir()) > 0:
                raise Exception('{} is not empty'.format(self.mount_point))
            print('Mounting {}'.format(self.mount_point))
            subprocess.check_call(['mount', self.mount_point])
            self.should_unmount = True

    def __exit__(self, exc_type, value, traceback):
        if not self.should_unmount:
            return
        if not os.path.ismount(self.mount_point):
            raise Exception('{} is not mounted')
        print('Unmounting {}'.format(self.mount_point))
        subprocess.check_call(['umount', self.mount_point])
        if len(self._list_dir()) > 0:
            raise Exception('{} is not empty'.format(self.mount_point))
        if os.path.ismount(self.mount_point):
            raise Exception('{} is still mounted'.format(self.mount_point))
        self.should_unmount = False

    def _list_dir(self):
        return [
            fn for fn in os.listdir(self.mount_point)
            if fn not in ['.keep']
        ]


class BindMounts(object):
    def __init__(self, mounts=[]):
        self.mounts = mounts
        self.temp_dir = None

    def __enter__(self):
        try:
            self.temp_dir = tempfile.mkdtemp(
                prefix='{}.'.format(self.__class__.__name__))
            for mountpoint in self.mounts:
                self.mount(mountpoint)
            return self
        except:  # noqa: E722
            self._cleanup()
            raise

    def __exit__(self, exc_type, value, traceback):
        self._cleanup()

    def mount(self, target, bind_name=None):
        if not os.path.ismount(target):
            raise Exception('{} is not a mount point'.format(target))
        bind_name = bind_name or os.path.basename(target) or 'root'
        bind_dir = os.path.join(self.temp_dir, bind_name)
        print('Mounting {} at {}'.format(target, bind_dir))
        os.mkdir(bind_dir)
        subprocess.check_call(['mount', '--bind', target, bind_dir])
        return bind_dir

    def _cleanup(self):
        if self.temp_dir and os.path.isdir(self.temp_dir):
            self._cleanup_mounts()
            self._remove_temp_dir()

    def _remove_temp_dir(self):
        print('Removing temporary directory {}'.format(self.temp_dir))
        os.rmdir(self.temp_dir)

    def _cleanup_mounts(self):
        for entry in os.listdir(self.temp_dir):
            self._unmount(os.path.join(self.temp_dir, entry))
        self._check_proc_mounts(unmount=True)
        if len(os.listdir(self.temp_dir)) > 0:
            raise Exception('Mounts directory {} is not empty'
                            .format(self.temp_dir))

    def _check_proc_mounts(self, unmount=False):
        for mount_line in open('/proc/mounts', 'r').readlines():
            mount_dest = mount_line.strip().split(' ', 2)[1]
            if mount_dest.startswith(self.temp_dir):
                if unmount:
                    self._unmount(mount_dest)
                else:
                    raise Exception('{} still mounted!'.format(mount_dest))
        if unmount:
            self._check_proc_mounts(unmount=False)

    def _unmount(self, path):
        if not os.path.isdir(path):
            return
        try:
            print('Unmounting {}'.format(path))
            subprocess.check_call(['umount', path], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print('Warning: Error {} unmounting {}: {}'
                  .format(path, e.returncode, e.output))
        if os.path.ismount(path):
            raise Exception('{} is still a mount point after umount'
                            .format(path))
        if len(os.listdir(path)) > 0:
            raise Exception('{} is not empty after umount'.format(path))
        os.rmdir(path)
