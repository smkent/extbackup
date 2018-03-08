import os

import mock
import pytest

from extbackup.main import Action
from extbackup.main import App
from extbackup.main import MAPPER_NAME
from extbackup.main import MOUNT_DIR

MOCK_TEMP_DIR = '/tmp/tmp.unittest'
MOCK_MOUNT_POINT = '/test-mount-point'
MOCK_BIND_MOUNT = os.path.join(MOCK_TEMP_DIR,
                               os.path.basename(MOCK_MOUNT_POINT))
MOCK_DIR_CONTENTS = ['.keep', 'some_file.txt']


@pytest.fixture
def mock_exists():
    with mock.patch('os.path.exists') as patched_object:
        yield patched_object


@pytest.fixture
def mock_ismount():
    with mock.patch('os.path.ismount') as patched_object:
        yield patched_object


@pytest.fixture
def mock_stat_isblk():
    with mock.patch('stat.S_ISBLK') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_call():
    with mock.patch('subprocess.check_call') as patched_object:
        yield patched_object


@pytest.fixture
def mock_mount():
    with mock.patch('extbackup.main.mount') as mock_mount:
        yield mock_mount


@pytest.fixture
def mock_unmount():
    with mock.patch('extbackup.main.unmount') as mock_unmount:
        yield mock_unmount


@pytest.fixture(autouse=True)
def mock_root():
    with mock.patch('os.getuid') as mock_getuid:
        mock_getuid.return_value = 0
        yield mock_getuid


class TestApp(object):
    def test_mount(self, mock_exists, mock_stat_isblk,
                   mock_mount, mock_call):
        mock_exists.side_effect = [True, False]
        mock_stat_isblk.return_value = True
        with mock.patch('os.stat'):
            app = App(mock.MagicMock(action=Action.MOUNT,
                                     device='/dev/unittest0'))
            app.run()
        mock_call.assert_called_once_with(
            ['cryptsetup', 'luksOpen', '/dev/unittest0', MAPPER_NAME])
        mock_mount.assert_called_once_with(
            MOUNT_DIR, source=os.path.join('/dev/mapper', MAPPER_NAME))

    def test_mount_doesnt_exist(self, mock_exists, mock_stat_isblk, mock_mount,
                                mock_call):
        mock_exists.side_effect = [True, False]
        mock_stat_isblk.return_value = False
        with mock.patch('os.stat'):
            app = App(mock.MagicMock(action=Action.MOUNT,
                                     device='/dev/unittest0'))
            with pytest.raises(Exception):
                app.run()
        mock_mount.assert_not_called()
        mock_call.assert_not_called()

    def test_mount_mapper_exists(self, mock_exists, mock_stat_isblk,
                                 mock_mount, mock_call):
        mock_exists.side_effect = [True, True]
        mock_stat_isblk.return_value = True
        with mock.patch('os.stat'):
            app = App(mock.MagicMock(action=Action.MOUNT,
                                     device='/dev/unittest0'))
            app.run()
        mock_call.assert_not_called()
        mock_mount.assert_called_once_with(
            MOUNT_DIR, source=os.path.join('/dev/mapper', MAPPER_NAME))

    def test_unmount(self, mock_ismount, mock_exists, mock_unmount,
                     mock_call):
        mock_ismount.return_value = True
        mock_exists.return_value = True
        app = App(mock.MagicMock(action=Action.UNMOUNT))
        app.run()
        mock_unmount.assert_called_once_with(MOUNT_DIR)
        mock_call.assert_called_once_with(
            ['cryptsetup', 'luksClose', MAPPER_NAME])

    def test_unmount_not_mounted(self, mock_ismount, mock_exists, mock_unmount,
                                 mock_call):
        mock_ismount.return_value = False
        mock_exists.return_value = True
        app = App(mock.MagicMock(action=Action.UNMOUNT))
        app.run()
        mock_unmount.assert_not_called()
        mock_call.assert_called_once_with(
            ['cryptsetup', 'luksClose', MAPPER_NAME])

    def test_unmount_not_mounted_no_mapper(self, mock_ismount, mock_exists,
                                           mock_unmount, mock_call):
        mock_ismount.return_value = False
        mock_exists.return_value = False
        app = App(mock.MagicMock(action=Action.UNMOUNT))
        app.run()
        mock_unmount.assert_not_called()
        mock_call.assert_not_called()
