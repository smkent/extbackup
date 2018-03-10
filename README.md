# extbackup

External backup disk creation

This is [smkent][smkent]'s personal backup creation utility. It is published for
illustrative purposes only. I am not responsible for any damage or data loss.

---

Backups are created using `rsync` and stored on a partition encrypted using
cryptsetup and LUKS.

Backup files can be versioned or stored as a single copy. Versioning is
performed based on the backup creation time, hard-linking unchanged files using
using `rsync`'s `--link-dest` option. Single copy backup is a good option for
larger files for which older versions should not be retained.

If MySQL is present on the system, a dump of all databases is performed and
stored on the backup destination.

## Repository setup

First, install [pipenv][pipenv]:

```sh
pip install pipenv
```

Then, set up the repository:

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

To restore files, use `rsync -avHSAX` to preserve all attributes and properties.

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

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

See [`LICENSE`](/LICENSE) for the full license text.


[pipenv]: https://docs.pipenv.org/
[smkent]: https://github.com/smkent
