import os

import mock
import pytest
import subprocess

from extbackup.mount import Mount
from extbackup.mount import BindMounts

MOCK_TEMP_DIR = '/tmp/tmp.unittest'
MOCK_MOUNT_POINT = '/test-mount-point'


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
    with mock.patch("builtins.open",
                    mock.mock_open(read_data="")) as mock_file:
        yield mock_file


class TestMount(object):
    def test_mount_previously_unmounted(self, mock_call, mock_listdir,
                                        mock_isdir, mock_ismount):
        mock_listdir.return_value = ['.keep']
        mock_isdir.return_value = True
        mock_ismount.side_effect = [False, True, False]
        with Mount(MOCK_MOUNT_POINT):
            pass
        mock_call.assert_has_calls([
            mock.call(['mount', MOCK_MOUNT_POINT]),
            mock.call(['umount', MOCK_MOUNT_POINT]),
        ])
        assert mock_call.call_count == 2

    def test_mount_previously_mounted(self, mock_call, mock_listdir,
                                      mock_isdir, mock_ismount):
        mock_listdir.return_value = []
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        with Mount(MOCK_MOUNT_POINT):
            pass
        mock_call.assert_not_called()

    def test_mount_does_not_exist(self, mock_call, mock_listdir,
                                  mock_isdir, mock_ismount):
        mock_listdir.return_value = []
        mock_isdir.return_value = False
        mock_ismount.return_value = False
        with pytest.raises(Exception):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_not_called()

    def test_mount_directory_not_empty(self, mock_call, mock_listdir,
                                       mock_isdir, mock_ismount):
        mock_listdir.return_value = ['.keep', 'some_file.txt']
        mock_isdir.return_value = True
        mock_ismount.return_value = False
        with pytest.raises(Exception):
            with Mount(MOCK_MOUNT_POINT):
                pass
        mock_call.assert_not_called()


class TestBindMounts(object):
    def test_bind_mounts_no_mounts(self, mock_call, mock_listdir,
                                   mock_isdir, mock_ismount, mock_mkdir,
                                   mock_rmdir, mock_mkdtemp):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.return_value = []
        mock_isdir.return_value = True
        mock_ismount.return_value = False
        with BindMounts():
            pass
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_called_with(MOCK_TEMP_DIR)
        mock_call.assert_not_called()

    def test_bind_mounts_with_mounts(self, mock_call, mock_listdir,
                                     mock_isdir, mock_ismount, mock_mkdir,
                                     mock_rmdir, mock_mkdtemp,
                                     mock_open_file):
        def _bind_dir_name(mountpoint):
            return os.path.basename(mountpoint) or 'root'

        mock_mountpoints = [MOCK_MOUNT_POINT, '/mnt/other-mount-point', '/']
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.side_effect = (
            [
                # Mounts directory list
                [_bind_dir_name(m) for m in mock_mountpoints],
            ] +
            [
                # Mount point list after unmount
                []
            ] * len(mock_mountpoints) +
            [
                # Mounts directory list after _unmount
                []
            ]
        )
        mock_isdir.side_effect = (
            # Start of _cleanup_mounts
            [True] +
            # In _unmount prior to umount
            [True] * len(mock_mountpoints) +
            # End of _cleanup_mounts
            [False])
        mock_ismount.return_value = True
        with BindMounts() as m:
            for mountpoint in mock_mountpoints:
                m.mount(mountpoint)
        mock_call.assert_has_calls(
            [
                mock.call(['mount', '--bind', mountpoint,
                           os.path.join(
                               MOCK_TEMP_DIR,
                               _bind_dir_name(mountpoint))])
                for mountpoint in mock_mountpoints
            ] +
            [
                mock.call(['umount',
                           os.path.join(
                               MOCK_TEMP_DIR,
                               _bind_dir_name(mountpoint))],
                          stderr=subprocess.STDOUT)
                for mountpoint in mock_mountpoints
            ]
        )
        assert mock_call.call_count == (len(mock_mountpoints) * 2)
        mock_mkdir.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       _bind_dir_name(mountpoint)))
                for mountpoint in mock_mountpoints
            ]
        )
        assert mock_mkdir.call_count == len(mock_mountpoints)
        mock_rmdir.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       _bind_dir_name(mountpoint)))
                for mountpoint in mock_mountpoints
            ] +
            [
                mock.call(MOCK_TEMP_DIR),
            ]
        )
        assert mock_rmdir.call_count == 1 + len(mock_mountpoints)

    def test_bind_mounts_cleanup_fail(self, mock_call, mock_listdir,
                                      mock_isdir, mock_ismount, mock_mkdir,
                                      mock_rmdir, mock_mkdtemp,
                                      mock_open_file):
        def _bind_dir_name(mountpoint):
            return os.path.basename(mountpoint) or 'root'

        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_listdir.side_effect = ([
            # Mounts directory list
            [_bind_dir_name(MOCK_MOUNT_POINT)],
            # Mount point list after unmount
            ['file.txt'],
            # Mounts directory list after _unmount
            [_bind_dir_name(MOCK_MOUNT_POINT)]
        ])
        mock_isdir.side_effect = ([
            True,  # Start of _cleanup_mounts
            True,  # In _unmount prior to umount
            True,  # End of _cleanup_mounts
        ])
        mock_ismount.return_value = True
        with pytest.raises(Exception):
            with BindMounts() as m:
                m.mount(MOCK_MOUNT_POINT)

        mock_call.assert_has_calls([
            mock.call(['mount', '--bind', MOCK_MOUNT_POINT,
                       os.path.join(
                           MOCK_TEMP_DIR,
                           _bind_dir_name(MOCK_MOUNT_POINT))]),
            mock.call(['umount',
                       os.path.join(
                           MOCK_TEMP_DIR,
                           _bind_dir_name(MOCK_MOUNT_POINT))],
                      stderr=subprocess.STDOUT)
        ])
        assert mock_call.call_count == 2
        mock_mkdir.assert_called_once_with(
            os.path.join(MOCK_TEMP_DIR, _bind_dir_name(MOCK_MOUNT_POINT)))
        mock_rmdir.assert_not_called()
