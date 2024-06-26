#!/usr/bin/env python3

from __future__ import annotations

import os
import pathlib
import hashlib
import requests

from tricot.logging import Logger


class ResourceValidationException(Exception):
    '''
    '''


class Resource:
    '''
    The resource class represents an additional resource that
    is required for tricot to run. These can be specified within
    tricot configuration files.
    '''

    def __init__(self, attrs: dict) -> None:
        '''
        Initialize the resource with attributes taken from the
        yaml file.
        
        Parameters:
            attrs           attributes to initialize the resource with

        Returns:
            None
        '''
        self.url = None
        self.path = None
        self.hash = None
        self.mode = None

        for key, value in attrs.items():

            if key == 'path':
                self.path = value

            elif key == 'url':
                self.url = value

            elif key == 'hash':
                self.hash = value

            elif key == 'mode':
                self.mode = value

            else:
                raise ResourceValidationException('Unknown resource attribute:' + key)

        if self.path is None:
            raise ResourceValidationException('Required "path" attribute is missing.')


    def validate(self) -> None:
        '''
        Validates whether the resource has the correct state.
        Missing files are downloaded if url attribute was specified.
        Files with incorrect permissions are adjusted.

        Parameters:
            None

        Returns:
            None
        '''
        path = pathlib.Path(self.path).expanduser()

        if not path.is_file():

            if not self.url:
                raise ResourceValidationException(f'{path}: does not exist.')
            
            Logger.print_mixed_yellow('Downloading missing resource from:', self.url)
            r = requests.get(self.url)
            
            if r.status_code != 200:
                raise ResourceValidationException(f'{self.url}: did not return 200.')

            Logger.print_mixed_blue('Writing resource data to:', str(path))
            path.write_bytes(r.content)

        if self.hash:

            triggered = False
            content = path.read_bytes()

            for hash_type in ['md5', 'sha1', 'sha256', 'sha512']:

                hash_value = self.hash.get(hash_type)

                if hash_value is not None:

                    triggered = True
                    computed = hashlib.new(hash_type, content).hexdigest()

                    if computed != hash_value:
                        raise ResourceValidationException(f'{path}: {computed} != {hash_value}')

            if not triggered:
                raise ResourceValidationException('hash attribute contains no valid hash types.')

        if self.mode:
            Logger.print_mixed_blue('Adjusting permissions of resource to:', self.mode)
            os.chmod(path, int(self.mode, 8))
