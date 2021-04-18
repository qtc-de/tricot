#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

file_1 = 'file-exists-test-one'
file_2 = 'file-exists-test-two'

config_list = [{'files': [file_1, file_2]}]
config_list.append({'files': [file_1, file_2], 'invert': ['nope']})
config_list.append({'files': [file_2], 'invert': [file_1]})
config_list.append({'files': ['nope'], 'invert': ['nope']})
config_list.append({'files': [file_1, file_2], 'cleanup': True})

result_list = [True, True, False, False, True]
file_deleted = [False, False, False, False, True]


@pytest.mark.parametrize('config, result, deleted', zip(config_list, result_list, file_deleted))
def test_file_exists_validator(config: dict, result: bool, deleted: bool):
    '''
    Takes file lists as argument and performs file exists validations on them.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        deleted     Whether or not the files should be deleted by the cleanup action.

    Returns:
        None
    '''
    val = tricot.get_validator(Path(__file__), 'file_exists', config, {})

    dummy_command = tricot.Command([])

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"File '.+' does (:?not )?exist."):
            val._run(dummy_command)

        return

    for filename in config['files']:
        if deleted:
            assert not resolve(filename).is_file()

        else:
            assert resolve(filename).is_file()


@pytest.fixture(autouse=True)
def resource():
    '''
    Creates required ressources and cleans them up (if not already
    done by the validator).

    Parameters:
        None

    Returns:
        None
    '''
    resolve(file_1).touch()
    resolve(file_2).touch()

    yield "wait"

    resolve(file_1).unlink(missing_ok=True)
    resolve(file_2).unlink(missing_ok=True)
