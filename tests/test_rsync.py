import os

import pytest
from unittest import mock

from extbackup.rsync import RsyncPaths

MOCK_TEMP_DIR = '/tmp/tmp.unittest'
MOCK_CONFIG_PATH = '.extbackup'
MOCK_DESTINATION_DIR = '/tmp/unittest_copy'

MOCK_CONFIG_FILE = '''
include: |
  /**

exclude: |
  /home/
  /root/

include-single: |
  - *

exclude-single: |
'''

MOCK_CONFIG_FILE_PARTIAL = '''
exclude: |
  /home/
  /root/

exclude-single: |
'''

MOCK_CONFIG_FILE_INVALID_SECTION = '''
invalid-section: |
  - *
'''


@pytest.fixture(autouse=True)
def mock_mkdir():
    with mock.patch('os.mkdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_exists():
    with mock.patch('os.path.exists') as patched_object:
        yield patched_object


@pytest.fixture
def mock_isdir():
    with mock.patch('os.path.isdir') as patched_object:
        yield patched_object


@pytest.fixture
def mock_isfile():
    with mock.patch('os.path.isfile') as patched_object:
        yield patched_object


@pytest.fixture(autouse=True)
def mock_shutil_copy():
    with mock.patch('shutil.copy') as patched_object:
        yield patched_object


def test_rsync_paths(mock_isfile, mock_isdir, mock_exists, mock_mkdir,
                     mock_shutil_copy):
    mock_isdir.return_value = False
    mock_exists.return_value = False
    mock_isfile.return_value = True
    with mock.patch('builtins.open',
                    mock.mock_open(read_data=MOCK_CONFIG_FILE)) as mock_open:
        rsync = RsyncPaths(MOCK_CONFIG_PATH, MOCK_TEMP_DIR)
        mock_open.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR, 'rsync-include'), 'w'),
                mock.call(os.path.join(MOCK_TEMP_DIR, 'rsync-exclude'), 'w'),
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       'rsync-include-single'), 'w'),
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       'rsync-exclude-single'), 'w'),
            ],
            any_order=True)
        assert rsync.get_exclude_include_args() == [
            '--exclude-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-exclude')),
            '--include-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-include')),
        ]
        assert rsync.get_exclude_include_args(single=True) == [
            '--exclude-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-exclude-single')),
            '--include-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-include-single')),
        ]
        rsync.copy_config(MOCK_DESTINATION_DIR)
        mock_mkdir.assert_called_once_with(MOCK_DESTINATION_DIR)
        assert mock_shutil_copy.call_count == 4
        mock_shutil_copy.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR, paths_file),
                          MOCK_DESTINATION_DIR)
                for paths_file in [
                        'rsync-exclude',
                        'rsync-exclude-single',
                        'rsync-include',
                        'rsync-include-single',
                ]
            ],
            any_order=True)


def test_rsync_paths_partial(mock_isfile, mock_isdir, mock_exists, mock_mkdir,
                             mock_shutil_copy):
    mock_isdir.return_value = False
    mock_exists.return_value = False
    mock_isfile.side_effect = [True, True]
    with mock.patch('builtins.open',
                    mock.mock_open(read_data=MOCK_CONFIG_FILE_PARTIAL)) \
            as mock_open:
        rsync = RsyncPaths(MOCK_CONFIG_PATH, MOCK_TEMP_DIR)
        mock_open.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR, 'rsync-exclude'), 'w'),
                mock.call(os.path.join(MOCK_TEMP_DIR,
                                       'rsync-exclude-single'), 'w'),
            ],
            any_order=True)
        assert rsync.get_exclude_include_args() == [
            '--exclude-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-exclude')),
        ]
        assert rsync.get_exclude_include_args(single=True) == [
            '--exclude-from={}'.format(
                os.path.join(MOCK_TEMP_DIR, 'rsync-exclude-single')),
        ]
        rsync.copy_config(MOCK_DESTINATION_DIR)
        mock_mkdir.assert_called_once_with(MOCK_DESTINATION_DIR)
        assert mock_shutil_copy.call_count == 2
        mock_shutil_copy.assert_has_calls(
            [
                mock.call(os.path.join(MOCK_TEMP_DIR, paths_file),
                          MOCK_DESTINATION_DIR)
                for paths_file in [
                        'rsync-exclude',
                        'rsync-exclude-single',
                ]
            ],
            any_order=True)


def test_rsync_paths_invalid_section():
    with mock.patch('builtins.open', mock.mock_open(
                        read_data=MOCK_CONFIG_FILE_INVALID_SECTION)) \
            as mock_open:
        RsyncPaths(MOCK_CONFIG_PATH, MOCK_TEMP_DIR)
        mock_open.assert_called_once_with(MOCK_CONFIG_PATH, 'r')


def test_rsync_paths_copy_config_destination_exists(mock_isdir, mock_exists,
                                                    mock_mkdir,
                                                    mock_shutil_copy):
    mock_isdir.return_value = False
    mock_exists.return_value = True
    with mock.patch('builtins.open', mock.mock_open(
                        read_data=MOCK_CONFIG_FILE_INVALID_SECTION)) \
            as mock_open:
        rsync = RsyncPaths(MOCK_CONFIG_PATH, MOCK_TEMP_DIR)
        mock_open.assert_called_once_with(MOCK_CONFIG_PATH, 'r')
        with pytest.raises(Exception):
            rsync.copy_config(MOCK_DESTINATION_DIR)
        mock_mkdir.assert_not_called()
        mock_shutil_copy.assert_not_called()


def test_rsync_empty_config_file():
    with mock.patch('builtins.open', mock.mock_open(read_data='')) \
            as mock_open:
        with pytest.raises(Exception):
            RsyncPaths(MOCK_CONFIG_PATH, MOCK_TEMP_DIR)
            mock_open.assert_called_once_with(MOCK_CONFIG_PATH, 'r')
