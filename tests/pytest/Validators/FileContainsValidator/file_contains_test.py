#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

file_1 = 'file-contains-test-file_1'
file_2 = 'file-contains-test-file_2'
content = '''This is a text file.'''
content2 = '''This is a text file.\nIt contains text.'''

config_list = [[{'file': file_1, 'contains': ['This is', 'text file', '.']}, {'file': file_2, 'contains': ['It', 'contains']}]]
config_list.append([{'file': file_1, 'contains': ['This as', 'xt fi', '.']}, {'file': file_2, 'contains': ['It', 'contains']}])
config_list.append([{'file': 'nope', 'contains': ['This as', 'text file', '.']}])
config_list.append([{'file': file_1, 'contains': ['This is', 'text file', '.'], 'invert': ['nope', 'nopenope']}])
config_list.append([{'file': file_1, 'contains': ['This is', 'text file', '.'], 'invert': ['is']}])
config_list.append([{'file': '${var}', 'contains': ['This ${var2}', 'text file', '.']}])

result_list = [True, False, False, True, False, True]
variable_list = [None, None, None, None, None, {'var': file_1}]
hotplug_list = [None, None, None, None, None, {'var2': 'is'}]


@pytest.mark.parametrize('config, result, variables, hotplug', zip(config_list, result_list, variable_list, hotplug_list))
def test_file_contains_validator(config: dict, result: bool, variables: dict, hotplug: dict):
    '''
    Perfors file contains validations on a list of specified filenames.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        variables   Variables to apply on the validator
        hotplug     Hotplug Variables to apply on the validator

    Returns:
        None
    '''
    val = tricot.get_validator(Path(__file__), 'file_contains', config, variables)

    dummy_command = tricot.Command(None)

    if result:
        val._run(dummy_command, hotplug)

    else:
        match = r"String '.+' was (:?not )?found in '.+'.|Specified file '.+' does not exist."
        with pytest.raises(tricot.ValidationException, match=match):
            val._run(dummy_command, hotplug)


@pytest.fixture(autouse=True)
def resource():
    '''
    Create required resources for the test and clean them up after the test.

    Parameters:
        None

    Returns:
        None
    '''
    resolve(file_1).write_text(content)
    resolve(file_2).write_text(content2)

    yield "wait"

    resolve(file_1).unlink()
    resolve(file_2).unlink()
