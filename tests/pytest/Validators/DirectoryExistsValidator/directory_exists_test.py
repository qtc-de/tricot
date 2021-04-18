#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

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
def test_directory_exists_validator(config: dict, result: bool, deleted: bool):
    '''
    Creates some test directories and verifies that the Validator validates them correctly.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        deleted     List of directories that should be deleted by the cleanup action

    Returns:
        None
    '''
    val = tricot.get_validator(Path(__file__), 'dir_exists', config, {})

    dummy_command = tricot.Command([])

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"Directory '.+' does (:?not )?exist."):
            val._run(dummy_command)

        return

    for dirname in config.get('dirs', []):
        if deleted:
            assert not resolve(dirname).is_dir()

        else:
            assert resolve(dirname).is_dir()


@pytest.fixture(autouse=True)
def resource():
    '''
    Create required resources and clean them up after the test (if not already done
    by the validator).

    Parameters:
        None

    Returns:
        None
    '''
    resolve(merged).mkdir(parents=True, exist_ok=True)

    yield "wait"

    if resolve(merged).is_dir():
        resolve(merged).rmdir()

    if resolve(dir_1).is_dir():
        resolve(dir_1).rmdir()
