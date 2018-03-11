import os


def fstab_mount_points():
    mount_points = {'/'}
    with open('/etc/fstab', 'r') as f:
        print('Loading fstab')
        for line in f.readlines():
            if '#' in line:
                line = line.split('#', 1)[0]
            line = line.strip()
            if not line:
                continue
            mount_point = line.split()[1]
            if mount_point.lower() == 'none':
                continue
            if os.path.isdir(mount_point):
                print('Found mount point: {}'.format(mount_point))
                mount_points.add(mount_point)
    return sorted(list(mount_points))
