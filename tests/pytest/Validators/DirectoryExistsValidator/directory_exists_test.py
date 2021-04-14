#!/usr/bin/python3

import os
import tricot
import pytest

from pathlib import Path


dir_1 = 'directory-validator-test'
dir_2 = 'test'
merged = dir_1 + '/' + dir_2

config_list = [{'dirs': [merged, dir_1]}]
config_list.append({'dirs': [merged, dir_1], 'invert': ['nope']})
config_list.append({'dirs': ['nope'], 'invert': ['nope']})
config_list.append({'invert': [dir_1]})
config_list.append({'dirs': [dir_1], 'cleanup': True})
config_list.append({'dirs': [merged, dir_1], 'cleanup': True})
config_list.append({'dirs': [dir_1], 'cleanup': True, 'force': True})

result_list = [True, True, False, False, True, True, True]
directory_deleted = [False, False, False, False, False, True, True]


@pytest.mark.parametrize('config, result, deleted', zip(config_list, result_list, directory_deleted))
def test_contains_validator(config: dict, result: bool, deleted: bool):
    '''
    '''
    val = tricot.get_validator(Path(__file__), 'dir_exists', config, {})
    os.makedirs(merged, exist_ok=True)

    dummy_command = tricot.Command([])

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"Directory '.+' does (:?not )?exist."):
            val._run(dummy_command)

    if deleted:
        assert not os.path.isdir(dir_1)

    else:
        assert os.path.isdir(dir_1)
