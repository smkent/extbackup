import os

import mock
import pytest
import subprocess

import extbackup.mount
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


@pytest.fixture(autouse=True)
def mock_mkdir():
    with mock.patch('os.mkdir') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_rmdir():
    with mock.patch('os.rmdir') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_call():
    with mock.patch('subprocess.check_call') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_mkdtemp():
    with mock.patch('tempfile.mkdtemp') as patched_object:
        yield patched_object


@pytest.fixture
def mock_open_file():
    with mock.patch('builtins.open',
                    mock.mock_open(read_data='')) as mock_file:
        yield mock_file


@pytest.fixture
def mock_mount():
    with mock.patch('extbackup.mount._mount') as mock_mount:
        yield mock_mount


@pytest.fixture
def mock_unmount():
    with mock.patch('extbackup.mount._unmount') as mock_unmount:
        yield mock_unmount


class TestHelpers(object):

    @pytest.mark.parametrize(['source'], [
        (None,),
        ('/dev/unittest0',)
    ])
    @pytest.mark.parametrize(['isdir',
                              'ismount',
                              'listdir',
                              'call_effect',
                              'expected_exception',
                              'expected_call',
                              'expected_return'], [
        # Success
        (True, [False, True], ['.keep'], None, None, True, True),
        # Already mounted
        (True, [True, True], ['.keep'], None, None, False, None),
        # Directory missing
        (False, [False, False], ['.keep'], None, Exception, False, None),
        # Directory not empty
        (True, [False, True], MOCK_DIR_CONTENTS, None, Exception, False, None),
        # Mount command failure
        (True, [False, True], ['.keep'],
         subprocess.CalledProcessError(1, ['unmount']),
         subprocess.CalledProcessError, True, None),
        # Mount failure
        (True, [False, False], ['.keep'], None, Exception, True, None),
    ])
    def test_mount(self, source, isdir, ismount, listdir, call_effect,
                   expected_exception, expected_call, expected_return,
                   mock_ismount, mock_listdir, mock_isdir, mock_call):
        mock_isdir.return_value = isdir
        mock_ismount.side_effect = ismount
        mock_listdir.return_value = listdir
        if call_effect:
            mock_call.side_effect = call_effect
        if expected_exception:
            with pytest.raises(expected_exception):
                extbackup.mount._mount(
                    MOCK_MOUNT_POINT, source=source)
        else:
            assert extbackup.mount._mount(
                MOCK_MOUNT_POINT, source=source) == expected_return
        if expected_call:
            cmd = ['mount']
            if source:
                cmd += [source]
            cmd += [MOCK_MOUNT_POINT]
            mock_call.assert_called_once_with(cmd)
        else:
            mock_call.assert_not_called()

    def test_mount_bind(self, mock_ismount, mock_listdir, mock_isdir,
                        mock_call):
        source = '/dev/unittest0'
        mock_ismount.return_value = False
        assert extbackup.mount._mount(
            MOCK_MOUNT_POINT, source=source, bind=True) is True
        mock_call.assert_called_once_with(['mount', '--bind', source,
                                           MOCK_MOUNT_POINT])

    def test_mount_bind_no_source(self, mock_ismount, mock_listdir, mock_isdir,
                                  mock_call):
        with pytest.raises(Exception):
            extbackup.mount._mount(
                MOCK_MOUNT_POINT, source=None, bind=True)
        mock_call.assert_not_called()

    @pytest.mark.parametrize(['isdir',
                              'ismount',
                              'listdir',
                              'call_effect',
                              'expected_exception',
                              'expected_call'], [
        # Success
        (True, False, ['.keep'], None, None, True),
        # Directory missing
        (False, False, ['.keep'], None, Exception, False),
        # Unmount command failure
        (True, True, ['.keep'],
         subprocess.CalledProcessError(1, ['unmount']),
         subprocess.CalledProcessError, True),
        # Directory not empty after unmount
        (True, False, MOCK_DIR_CONTENTS, None, Exception, True),
        # Still mounted after unmount
        (True, True, ['.keep'], None, Exception, True),
    ])
    def test_unmount(self, isdir, ismount, listdir, expected_exception,
                     expected_call, call_effect,
                     mock_ismount, mock_listdir, mock_isdir, mock_call):
        mock_isdir.return_value = isdir
        mock_ismount.return_value = ismount
        mock_listdir.return_value = listdir
        if call_effect:
            mock_call.side_effect = call_effect
        if expected_exception:
            with pytest.raises(expected_exception):
                extbackup.mount._unmount(MOCK_MOUNT_POINT)
        else:
            extbackup.mount._unmount(MOCK_MOUNT_POINT)
        if expected_call:
            mock_call.assert_called_once_with(['umount', MOCK_MOUNT_POINT])
        else:
            mock_call.assert_not_called()


class TestMount(object):
    def test_enter(self, mock_mount):
        with mock.patch.object(Mount, '__exit__',
                               mock.MagicMock(return_value=None)):
            mount = Mount(MOCK_MOUNT_POINT)
            with mount:
                assert mount.should_unmount is True
            mock_mount.assert_called_once_with(target=MOCK_MOUNT_POINT)

    @pytest.mark.parametrize(['should_unmount'], [
        (True,),
        (False,),
    ])
    def test_exit(self, should_unmount, mock_unmount):
        def _configure_mount(mount):
            mount.should_unmount = should_unmount
        with mock.patch.object(Mount, '__enter__', _configure_mount):
            with Mount(MOCK_MOUNT_POINT):
                pass
            if should_unmount:
                mock_unmount.assert_called_once_with(MOCK_MOUNT_POINT)
            else:
                mock_unmount.assert_not_called()


class TestBindMounts(object):
    def _bind_dir_name(self, mountpoint):
        return os.path.basename(mountpoint) or 'root'

    def test_no_mounts(self, mock_mkdtemp, mock_ismount, mock_listdir,
                       mock_mkdir, mock_rmdir, mock_open_file,
                       mock_mount, mock_unmount):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_ismount.return_value = False
        mock_listdir.return_value = []
        with BindMounts():
            pass
        mock_mkdir.assert_not_called()
        mock_rmdir.assert_not_called()
        mock_mount.assert_not_called()
        mock_unmount.assert_not_called()

    def test_enter_success(self, mock_mkdtemp, mock_ismount, mock_mkdir,
                           mock_mount):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                pass
        mock_cleanup.assert_not_called()
        mock_mkdir.assert_called_once_with(MOCK_BIND_MOUNT)
        mock_mount.assert_called_once_with(MOCK_BIND_MOUNT,
                                           source=MOCK_MOUNT_POINT,
                                           bind=True)

    def test_enter_mkdtemp_fail(self, mock_mkdtemp, mock_ismount, mock_mkdir,
                                mock_mount):
        mock_mkdtemp.side_effect = Exception
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_cleanup.assert_called_once_with()
        mock_mkdir.assert_not_called()
        mock_mount.assert_not_called()

    def test_enter_not_mount_point(self, mock_mkdtemp, mock_ismount,
                                   mock_mkdir, mock_mount):
        mock_mkdtemp.return_value = MOCK_TEMP_DIR
        mock_ismount.return_value = False
        with mock.patch.object(BindMounts, '__exit__'), \
                mock.patch.object(BindMounts, '_cleanup') as mock_cleanup:
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_cleanup.assert_called_once_with()
        mock_mkdir.assert_not_called()
        mock_mount.assert_not_called()

    @pytest.mark.parametrize(['temp_dir'], [
        (None,),
        (MOCK_TEMP_DIR,),
    ])
    def test_exit_no_temp_dir(self, temp_dir, mock_unmount, mock_isdir):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = temp_dir
        mock_isdir.return_value = False
        with mock.patch.object(BindMounts, '__enter__',
                               _configure_bind_mounts):
            with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                pass
        mock_unmount.assert_not_called()

    def test_exit_success(self, mock_unmount, mock_listdir, mock_isdir,
                          mock_ismount, mock_open_file):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
            [self._bind_dir_name(MOCK_MOUNT_POINT)],
            [],
        ]
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__enter__',
                               _configure_bind_mounts):
            with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                pass
        mock_unmount.assert_called_once_with(MOCK_BIND_MOUNT)

    def test_exit_success_multiple_mounts(self, mock_unmount, mock_listdir,
                                          mock_isdir, mock_ismount,
                                          mock_open_file):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_mountpoints = [MOCK_MOUNT_POINT, '/mnt/other-mount-point', '/']
        mock_listdir.side_effect = [
            [self._bind_dir_name(mountpoint)
             for mountpoint in mock_mountpoints],
            [],
        ]
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__enter__',
                               _configure_bind_mounts):
            with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                pass
        mock_unmount.assert_has_calls([
            mock.call(os.path.join(MOCK_TEMP_DIR,
                                   self._bind_dir_name(mountpoint)))
            for mountpoint in mock_mountpoints
        ])

    def test_exit_mounts_directory_not_empty(self, mock_unmount, mock_listdir,
                                             mock_isdir, mock_ismount,
                                             mock_open_file):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
            [self._bind_dir_name(MOCK_MOUNT_POINT)],
            MOCK_DIR_CONTENTS,
        ]
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        with mock.patch.object(BindMounts, '__enter__',
                               _configure_bind_mounts):
            with pytest.raises(Exception):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
        mock_unmount.assert_called_once_with(MOCK_BIND_MOUNT)

    def test_exit_unmount_proc_mounts(self, mock_unmount, mock_listdir,
                                      mock_isdir, mock_ismount):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
            [self._bind_dir_name(MOCK_MOUNT_POINT)],
            [],
        ]
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        proc_data = '/ {} ext4 rw 0 0'.format(MOCK_BIND_MOUNT)
        with mock.patch('builtins.open', create=True) as mock_open:
            mock_open.side_effect = [
                mock.mock_open(read_data=proc_data).return_value,
                mock.mock_open(read_data='').return_value,
            ]
            with mock.patch.object(BindMounts, '__enter__',
                                   _configure_bind_mounts):
                with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                    pass
            assert mock_unmount.call_count == 2
            mock_unmount.assert_has_calls([
                mock.call(MOCK_BIND_MOUNT),
                mock.call(MOCK_BIND_MOUNT),
            ])

    def test_exit_unmount_proc_mounts_fail(self, mock_unmount, mock_listdir,
                                           mock_isdir, mock_ismount):
        def _configure_bind_mounts(bind_mounts):
            bind_mounts.temp_dir = MOCK_TEMP_DIR
        mock_listdir.side_effect = [
            [self._bind_dir_name(MOCK_MOUNT_POINT)],
            [],
        ]
        mock_isdir.return_value = True
        mock_ismount.return_value = True
        proc_data = '/ {} ext4 rw 0 0'.format(MOCK_BIND_MOUNT)
        with mock.patch('builtins.open', create=True) as mock_open:
            mock_open.side_effect = [
                mock.mock_open(read_data=proc_data).return_value,
                mock.mock_open(read_data=proc_data).return_value,
            ]
            with mock.patch.object(BindMounts, '__enter__',
                                   _configure_bind_mounts):
                with pytest.raises(Exception):
                    with BindMounts(mounts=[MOCK_MOUNT_POINT]):
                        pass
            assert mock_unmount.call_count == 2
            mock_unmount.assert_has_calls([
                mock.call(MOCK_BIND_MOUNT),
                mock.call(MOCK_BIND_MOUNT),
            ])
