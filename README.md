# extbackup

External backup disk creation utility

Backups are created using `rsync` and stored on a partition encrypted using
cryptsetup and LUKS.

Backup files can be versioned or stored as a single copy. Versioning is
performed based on the backup creation time, hard-linking unchanged files using
using `rsync`'s `--link-dest` option. Single copy backup is a good option for
larger files for which older versions should not be retained.

## Repository setup

```sh
make
```

This will create the `extbackup` executable in the `bin` subdirectory.

## Disk partition creation

Create an encrypted partition by running (replace `/dev/device` with the disk
partition block device):

```sh
extbackup -d /dev/device create
```

## Backup configuration

Backups use `rsync`'s include and exclude filter rules to determine what to
include in the backup. Configure the contents of these filters by creating a
config file at `~/.extbackup` (or other location specified using `extbackup`'s
`--config` option).

The filters config file should be a YAML file such as the following example:

```yaml
include: |
  /**

exclude: |
  /path/to/exclude
  /another/path/to/exclude
  /single/path

include-single: |
  /
  /single/
  /single/path/**
  - *

exclude-single: |
  /single/path/exclude/file

# vim: ft=yaml
```

The `include` and `exclude` sections are paths that apply to versioned backups,
while the `include-single` and `exclude-single` sections apply to single-copy
backups.

For details on how these filters work, see the `FILTER RULES` section in the
`rsync` man page.


## Backup creation

First, mount the backup disk partition (replace `/dev/device` with the disk
partition block device):

```sh
extbackup mount -d /dev/device
```

Create the backup (optionally add `-p`/`--pretend` to perform a dry run):
```sh
extbackup backup
```

Once the backup is complete, unmount the backup disk partition:

```sh
extbackup unmount
```

## Recovery from backup

Recovery is a manual process.

First, unlock and mount the backup disk:
```sh
cryptsetup luksOpen /dev/device backup-external
mount /dev/mapper/backup-external /mnt/backup-external
```

The backup is now available under `/mnt/backup-external`.

To restore files, using `rsync -avHSAX /path/to/source /path/to/destination` to
preserve all attributes and properties.

When finished, re-lock and unmount the backup disk:
```sh
umount /dev/mapper/backup
cryptsetup luksClose backup
```

## Development

### Run unit tests and test code style
```sh
make test
```
