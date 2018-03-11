import os

import pytest
from unittest import mock

from extbackup.fstab import fstab_mount_points


@pytest.fixture
def mock_isdir():
    with mock.patch('os.path.isdir') as patched_object:
        yield patched_object


@pytest.mark.parametrize(['fstab', 'isdir', 'expected_mount_points'], [
    (
        # Empty fstab
        '', [], ['/'],
    ),
    (
        # fstab containing root
        '/dev/root / ext4 auto 0 0', [True], ['/'],
    ),
    (
        # Multiple mount points
        os.linesep.join([
            '/dev/root / ext4 auto 0 0',
            '/dev/sda1 /boot ext4 auto 0 0',
            '/dev/sda2 /var ext4 auto 0 0',
            '/dev/sda3 /mnt/unittest ext4 auto 0 0',
        ]),
        [True, True, True, True],
        ['/', '/boot', '/mnt/unittest', '/var'],
    ),
    (
        # Lines with comments
        os.linesep.join([
            '',
            '# Line with only a comment',
            '/dev/sda1 /mnt/unittest ext4 auto 0 0  # Trailing comment',
        ]),
        [True],
        ['/', '/mnt/unittest'],
    ),
    (
        # Entries with multiple spaces between fields
        '/dev/sda1    /mnt/unittest       ext4   auto   0   0',
        [True],
        ['/', '/mnt/unittest'],
    ),
    (
        # Duplicate mount point
        os.linesep.join([
            '/dev/sda1 /mnt/unittest ext4 auto 0 0',
            '/dev/sda2 /mnt/unittest ext4 auto 0 0',
        ]),
        [True, True],
        ['/', '/mnt/unittest'],
    ),
    (
        # Nonexistent
        '/dev/sda1 /mnt/unittest ext4 auto 0 0',
        [False],
        ['/'],
    ),
    (
        # No mount point
        os.linesep.join([
            '/dev/sda1 /mnt/unittest ext4 auto 0 0',
            '/dev/sda2 None ext4 auto 0 0',
        ]),
        [True],
        ['/', '/mnt/unittest'],
    ),
])
def test_fstab(fstab, isdir, expected_mount_points, mock_isdir):
    mock_isdir.side_effect = isdir
    with mock.patch('builtins.open', mock.mock_open(read_data=fstab)):
        assert fstab_mount_points() == expected_mount_points
