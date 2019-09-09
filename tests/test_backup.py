import os

import pytest
from unittest import mock

from extbackup.backup import ExternalBackup
from extbackup.backup import MOUNT_DIR

MOCK_HOSTNAME = 'testhost1'


@pytest.fixture
def mock_gethostname():
    with mock.patch('socket.gethostname') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_chmod():
    with mock.patch('os.chmod') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_mkdir():
    with mock.patch('os.mkdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_isdir():
    with mock.patch('os.path.isdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_ismount():
    with mock.patch('os.path.ismount') as patched_object:
        yield patched_object


def test_hostname(mock_gethostname):
    hostname = MOCK_HOSTNAME
    mock_gethostname.return_value = hostname
    backup = ExternalBackup()
    assert backup.hostname == hostname


def test_hostname_bad(mock_gethostname):
    mock_gethostname.return_value = None
    backup = ExternalBackup()
    with pytest.raises(Exception):
        assert backup.hostname


def test_target_drive_not_mounted(mock_chmod, mock_mkdir,
                                  mock_ismount, mock_isdir,
                                  mock_gethostname):
    mock_ismount.return_value = False
    mock_isdir.return_value = True
    backup = ExternalBackup()
    with pytest.raises(Exception):
        assert backup.target
    mock_gethostname.assert_not_called()
    mock_chmod.assert_not_called()
    mock_mkdir.assert_not_called()


@pytest.mark.parametrize(['dir_exists'], [
    (True,),
    (False,),
])
def test_target_exists(dir_exists, mock_chmod, mock_mkdir,
                       mock_ismount, mock_isdir, mock_gethostname):
    mock_ismount.return_value = True
    mock_isdir.return_value = dir_exists
    hostname = MOCK_HOSTNAME
    mock_gethostname.return_value = hostname
    backup = ExternalBackup()
    target = backup.target
    assert target == os.path.join(MOUNT_DIR, MOCK_HOSTNAME)
    mock_chmod.assert_called_once_with(target, 0o0700)
    if dir_exists:
        mock_mkdir.assert_not_called()
    else:
        mock_mkdir.assert_called_once_with(target)
