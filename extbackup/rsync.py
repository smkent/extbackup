from __future__ import print_function

import os
import shutil

import yaml


class RsyncPaths(object):
    CONFIG_SECTIONS = ['include', 'exclude',
                       'include-single', 'exclude-single']

    def __init__(self, config_file, config_directory):
        self.config_file = config_file
        self.config_directory = config_directory
        self.paths_files = {}
        self._configure()

    @property
    def config(self):
        if not hasattr(self, '_config'):
            print('Loading {}'.format(self.config_file))
            with open(self.config_file, 'r') as f:
                self._config = yaml.load(f)
                if not self._config:
                    raise Exception('No configuration loaded')
        return self._config

    def copy_config(self, destination):
        if not os.path.isdir(destination):
            if os.path.exists(destination):
                raise Exception('{} exists and is not a directory'
                                .format(destination))
            os.mkdir(destination)
        for file_path in self.paths_files.values():
            shutil.copy(file_path, destination)

    def get_exclude_include_args(self, single=False):
        out_args = []
        for paths_type in ['exclude', 'include']:
            paths_file = self._paths_file(paths_type, single)
            if not paths_file:
                continue
            if os.path.isfile(paths_file):
                out_args.append('--{}-from={}'
                                .format(paths_type, paths_file))
        return out_args

    def _configure(self):
        for section in self.CONFIG_SECTIONS:
            if section not in self.config:
                continue
            paths_file = os.path.join(self.config_directory,
                                      'rsync-{}'.format(section))
            with open(paths_file, 'w') as f:
                print(self.config[section].strip(), file=f)
            self.paths_files[section] = paths_file

    def _paths_file(self, paths_type, single):
        return self.paths_files.get('{}-single'.format(paths_type)
                                    if single else paths_type)
