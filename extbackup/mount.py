import os
import subprocess
import tempfile


def _list_dir(dir_name):
    return [fn for fn in os.listdir(dir_name) if fn not in ['.keep']]


def mount(target, source=None, bind=False):
    if bind and not source:
        raise Exception('source is required with bind')
    if not os.path.isdir(target):
        raise Exception('{} does not exist'.format(source))
    if os.path.ismount(target):
        return
    if len(_list_dir(target)) > 0:
        raise Exception('{} is not empty'.format(source))
    cmd = ['mount']
    if bind:
        cmd += ['--bind']
    if source:
        cmd += [source]
    cmd += [target]
    if source:
        print('Mounting {} at {}'.format(source, target))
    else:
        print('Mounting {}'.format(target))
    subprocess.check_call(cmd)
    if not bind:
        if not os.path.ismount(target):
            raise Exception('{} not mounted'.format(target))
    return True


def unmount(target):
    if not os.path.isdir(target):
        raise Exception('{} does not exist'.format(target))
    print('Unmounting {}'.format(target))
    subprocess.check_call(['umount', target])
    if len(_list_dir(target)) > 0:
        raise Exception('{} is not empty'.format(target))
    if os.path.ismount(target):
        raise Exception('{} is still mounted'.format(target))


class Mount(object):
    def __init__(self, mount_point):
        self.mount_point = mount_point
        self.should_unmount = False

    def __enter__(self):
        mount(target=self.mount_point)
        self.should_unmount = True

    def __exit__(self, exc_type, value, traceback):
        if self.should_unmount:
            unmount(self.mount_point)
            self.should_unmount = False


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
        bind_dir = os.path.join(
            self.temp_dir, bind_name or os.path.basename(target) or 'root')
        os.mkdir(bind_dir)
        mount(bind_dir, source=target, bind=True)
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
        if os.path.isdir(path):
            unmount(path)
            os.rmdir(path)
