import os

import mock
import pytest
import subprocess

from extbackup.mount import Mount
from extbackup.mount import BindMounts

MOCK_TEMP_DIR = '/tmp/tmp.unittest'
MOCK_MOUNT_POINT = '/test-mount-point'
MOCK_BIND_MOUNT = os.path.join(MOCK_TEMP_DIR,
                               os.path.basename(MOCK_MOUNT_POINT))
MOCK_DIR_CONTENTS = ['.keep', 'some_file.txt']


@pytest.fixture
def mock_isdir():
    with mock.patch('os.path.isdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_ismount():
    with mock.patch('os.path.ismount') as patched_object:
        yield patched_object


@pytest.fixture
def mock_listdir():
    with mock.patch('os.listdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_mkdir():
    with mock.patch('os.mkdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_rmdir():
    with mock.patch('os.rmdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_call():
    with mock.patch('subprocess.check_call') as patched_object:
        yield patched_object


@pytest.fixture
def mock_mkdtemp():
    with mock.patch('tempfile.mkdtemp') as patched_object:
        yield patched_object


@pytest.fixture
def mock_open_file():
    with mock.patch('builtins.open',
                    mock.mock_open(read_data='')) as mock_file:
        yield mock_file


class TestMount(object):
    def test_enter_previously_mounted(self, mock_call, mock_listdir,
                                      mock_isdir, mock_ismount):
        mock_listdir.return_value = MOCK_DIR_CONTENTS
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        with mock.patch.object(Mount, '__exit__'):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_not_called()

    def test_enter_previously_unmounted(self, mock_call, mock_listdir,
                                        mock_isdir, mock_ismount):
        mock_listdir.return_value = ['.keep']
        mock_isdir.return_value = True
        mock_ismount.side_effect = [False, True]
        with mock.patch.object(Mount, '__exit__'):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_called_once_with(['mount', MOCK_MOUNT_POINT])

    def test_enter_does_not_exist(self, mock_call, mock_listdir,
                                  mock_isdir, mock_ismount):
        mock_listdir.return_value = []
        mock_isdir.return_value = False
        mock_ismount.side_effect = [False, True]
        with mock.patch.object(Mount, '__exit__'):
            with pytest.raises(Exception):
                with Mount(MOCK_MOUNT_POINT):
                    pass
        mock_call.assert_not_called()

    def test_enter_directory_not_empty(self, mock_call, mock_listdir,
                                       mock_isdir, mock_ismount):
        mock_listdir.return_value = MOCK_DIR_CONTENTS
        mock_isdir.return_value = True
        mock_ismount.side_effect = [False, True]
        with mock.patch.object(Mount, '__exit__'):
            with pytest.raises(Exception):
                with Mount(MOCK_MOUNT_POINT):
                    pass
        mock_call.assert_not_called()

    def test_exit_previously_mounted(self, mock_call, mock_listdir,
                                     mock_ismount):
        def _configure_mount(mount):
            mount.should_unmount = False
        mock_listdir.return_value = []
        mock_ismount.side_effect = [True, False]
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_not_called()

    def test_exit_previously_unmounted(self, mock_call, mock_listdir,
                                       mock_ismount):
        def _configure_mount(mount):
            mount.should_unmount = True
        mock_listdir.return_value = []
        mock_ismount.side_effect = [True, False]
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_called_once_with(['umount', MOCK_MOUNT_POINT])

    def test_exit_mount_missing(self, mock_call, mock_listdir,
                                mock_ismount):
        def _configure_mount(mount):
            mount.should_unmount = True
        mock_ismount.return_value = False
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with pytest.raises(Exception):
                with Mount(MOCK_MOUNT_POINT):
                    pass
        mock_call.assert_not_called()

    def test_exit_not_empty_after_unmount(self, mock_call, mock_listdir,
                                          mock_ismount):
        def _configure_mount(mount):
            mount.should_unmount = True
        mock_ismount.side_effect = [True, False]
        mock_listdir.return_value = MOCK_DIR_CONTENTS
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with pytest.raises(Exception):
                with Mount(MOCK_MOUNT_POINT):
                    pass
        mock_call.assert_called_once_with(['umount', MOCK_MOUNT_POINT])

    def test_exit_still_mounted(self, mock_call, mock_listdir,
                                mock_ismount):
        def _configure_mount(mount):
            mount.should_unmount = True
        mock_ismount.return_value = True
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with pytest.raises(Exception):
                with Mount(MOCK_MOUNT_POINT):
                    pass
        mock_call.assert_called_once_with(['umount', MOCK_MOUNT_POINT])


class TestBindMounts(object):
    def _bind_dir_name(self, mountpoint):
        return os.path.basename(mountpoint) or 'root'

    def test_no_mounts(self, mock_call, mock_listdir, mock_isdir, mock_ismount,
                       mock_mkdir, mock_rmdir, mock_mkdtemp):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.return_value = []
        mock_isdir.return_value = True
        mock_ismount.return_value = False
        with BindMounts():
            pass
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_called_with(MOCK_TEMP_DIR)
        mock_call.assert_not_called()

    def test_enter_with_mounts(self, mock_call, mock_listdir, mock_isdir,
                               mock_ismount, mock_mkdir, mock_rmdir,
                               mock_mkdtemp):
        mock_mountpoints = [MOCK_MOUNT_POINT, '/mnt/other-mount-point', '/']
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
                # Mounts directory list
                [self._bind_dir_name(m) for m in mock_mountpoints],
            ]
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with BindMounts() as m:
                for mountpoint in mock_mountpoints:
                    m.mount(mountpoint)
        assert mock_call.call_count == len(mock_mountpoints)
        mock_call.assert_has_calls(
            [
                mock.call(['mount', '--bind', mountpoint,
                           os.path.join(
                               MOCK_TEMP_DIR,
                               self._bind_dir_name(mountpoint))])
                for mountpoint in mock_mountpoints
            ])
        assert mock_mkdir.call_count == len(mock_mountpoints)
        mock_mkdir.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       self._bind_dir_name(mountpoint)))
                for mountpoint in mock_mountpoints
            ])
        mock_cleanup.assert_not_called()

    def test_enter_mkdtemp_fail(self, mock_call, mock_listdir, mock_isdir,
                                mock_ismount, mock_mkdir, mock_rmdir,
                                mock_mkdtemp):
        mock_mkdtemp.side_effect = Exception
        mock_listdir.side_effect = []
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, 'mount') as mock_mount, \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_call.assert_not_called()
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()
        mock_mount.assert_not_called()
        mock_cleanup.assert_called_once_with()

    def test_enter_not_mountpoint(self, mock_call, mock_listdir, mock_isdir,
                                  mock_ismount, mock_mkdir, mock_rmdir,
                                  mock_mkdtemp):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
                # Mounts directory list
                [self._bind_dir_name(MOCK_TEMP_DIR)],
            ]
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_call.assert_not_called()
        mock_mkdir.assert_not_called()
        mock_cleanup.assert_called_once_with()

    def test_exit_with_mounts(self, mock_call, mock_listdir, mock_isdir,
                              mock_ismount, mock_mkdir, mock_rmdir,
                              mock_open_file):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_mountpoints = [MOCK_MOUNT_POINT, '/mnt/other-mount-point', '/']
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [self._bind_dir_name(m) for m in mock_mountpoints],
            ] +
            [
                # Mount point list after unmount
                []
            ] * len(mock_mountpoints) +
            [
                # Mounts directory list after _unmount
                []
            ])
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [True] * len(mock_mountpoints))
        # Mount status after unmount
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__enter__', _mock_enter):
            with BindMounts(mounts=mock_mountpoints):
                pass
        assert mock_call.call_count == len(mock_mountpoints)
        mock_call.assert_has_calls(
            [
                mock.call(['umount',
                           os.path.join(
                               MOCK_TEMP_DIR,
                               self._bind_dir_name(mountpoint))],
                          stderr=subprocess.STDOUT)
                for mountpoint in mock_mountpoints
            ])
        mock_mkdir.assert_not_called()
        assert mock_rmdir.call_count == 1 + len(mock_mountpoints)
        mock_rmdir.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       self._bind_dir_name(mountpoint)))
                for mountpoint in mock_mountpoints
            ] +
            [
                mock.call(MOCK_TEMP_DIR),
            ])

    def test_exit_unmount_not_dir(self, mock_call, mock_listdir, mock_isdir,
                                  mock_ismount, mock_mkdir, mock_rmdir,
                                  mock_open_file):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [self._bind_dir_name(MOCK_MOUNT_POINT)],
            ] +
            [
                # Mount point list after unmount
                MOCK_DIR_CONTENTS,
            ])
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [False])
        # Mount status after unmount
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__enter__', _mock_enter):
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_call.assert_not_called()
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()

    def test_exit_umount_fail(self, mock_call, mock_listdir, mock_isdir,
                              mock_ismount, mock_mkdir, mock_rmdir,
                              mock_open_file):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [self._bind_dir_name(MOCK_MOUNT_POINT)],
            ] +
            [
                # Mount point list after unmount
                MOCK_DIR_CONTENTS,
            ])
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [True])
        # Mount status after unmount
        mock_ismount.return_value = True
        # umount call failure
        mock_call.side_effect = subprocess.CalledProcessError(1, ['umount'])
        with mock.patch.object(BindMounts, '__enter__', _mock_enter):
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        assert mock_call.call_count == 1
        mock_call.assert_called_once_with(['umount', MOCK_BIND_MOUNT],
                                          stderr=subprocess.STDOUT)
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()

    def test_exit_umount_still_mounted(self, mock_call, mock_listdir,
                                       mock_isdir, mock_ismount, mock_mkdir,
                                       mock_rmdir, mock_open_file):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [self._bind_dir_name(MOCK_MOUNT_POINT)],
            ] +
            [
                # Mount point list after unmount
                MOCK_DIR_CONTENTS,
            ])
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [True])
        # Mount status after unmount
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__enter__', _mock_enter):
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        assert mock_call.call_count == 1
        mock_call.assert_called_once_with(['umount', MOCK_BIND_MOUNT],
                                          stderr=subprocess.STDOUT)
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()

    def test_exit_umount_directory_not_empty(self, mock_call, mock_listdir,
                                             mock_isdir, mock_ismount,
                                             mock_mkdir, mock_rmdir,
                                             mock_open_file):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [self._bind_dir_name(MOCK_MOUNT_POINT)],
            ] +
            [
                # Mount point list after unmount
                MOCK_DIR_CONTENTS,
            ])
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [True])
        # Mount status after unmount
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__enter__', _mock_enter):
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        assert mock_call.call_count == 1
        mock_call.assert_called_once_with(['umount', MOCK_BIND_MOUNT],
                                          stderr=subprocess.STDOUT)
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()

    @pytest.mark.parametrize(['proc_mount_present_after_unmount'], [
        (False, ),  # Successful unmount
        (True, ),   # Failed unmount
    ])
    def test_exit_proc_mounts(self,
                              proc_mount_present_after_unmount,
                              mock_call, mock_listdir, mock_isdir,
                              mock_ismount, mock_mkdir, mock_rmdir,
                              mock_mkdtemp):
        def _mock_enter(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR

        def _invoke_bind_mounts():
            with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                pass

        proc_data = '/ {} ext4 rw 0 0'.format(MOCK_BIND_MOUNT)
        with mock.patch('builtins.open', create=True) as mock_open:
            mock_open.side_effect = [
                mock.mock_open(read_data=proc_data).return_value,
                mock.mock_open(
                    read_data=(proc_data if proc_mount_present_after_unmount
                               else '')).return_value
            ]
            mock_listdir.side_effect = (
                [
                    # Mounts directory list
                    [],
                ] +
                [
                    # Mount point list after unmount
                    [],
                ] +
                [
                    # Mounts directory list after _unmount
                    []
                ])
            mock_isdir.side_effect = (
                # Start of _cleanup_mounts
                [True] +
                # In _unmount prior to umount
                [True])
            # Mount status after unmount
            mock_ismount.return_value = False
            with mock.patch.object(BindMounts, '__enter__', _mock_enter):
                if proc_mount_present_after_unmount:
                    with pytest.raises(Exception):
                        _invoke_bind_mounts()
                else:
                    _invoke_bind_mounts()
            assert mock_call.call_count == 1
            mock_call.assert_called_once_with(['umount', MOCK_BIND_MOUNT],
                                              stderr=subprocess.STDOUT)
            mock_mkdir.assert_not_called()
            if proc_mount_present_after_unmount:
                mock_rmdir.assert_called_once_with(MOCK_BIND_MOUNT)
            else:
                assert mock_rmdir.call_count == 2
                mock_rmdir.assert_has_calls([
                    mock.call(MOCK_BIND_MOUNT),
                    mock.call(MOCK_TEMP_DIR),
                ])
