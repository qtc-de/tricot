#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path


content = '''This is a text file.
It contains some contents.
It is used for testing tricot.
It is basically a replacement for command output.
'''

config_list = [{'ignore_case': False, 'match': ['This is .+ file', 'It .. [ab]{2}sically'], 'invert': ['Pancake']}]
config_list.append({'ignore_case': False, 'match': [r'This \w+ a text file', 'It is basically'], 'invert': ['t.xt']})
config_list.append({'ignore_case': False, 'match': [r'This \w+ a text file', 'It is basically'], 'invert': [r't\wis']})
config_list.append({'ignore_case': True, 'match': [r'This \w+ a text file', 'It is basically'], 'invert': [r't\wis']})
config_list.append({'ignore_case': True, 'match': ['This is a [ETX]{4} file', 'It is basically']})
config_list.append({'dotall': True, 'match': [r'file\..It', r'tricot\..It']})
config_list.append({'multiline': True, 'match': ['^It contains', r'tricot\.$']})
config_list.append({'ignore_case': '${var1}', 'match': ['${var2}', '${var3}']})

result_list = [True, False, True, False, True, True, True, True]
variable_list = [None, None, None, None, None, None, None, {'var1': True, 'var2': 'This .. . text', 'var3': 'comm.+output'}]


@pytest.mark.parametrize('config, result, variables', zip(config_list, result_list, variable_list))
def test_regex_validator(config: dict, result: bool, variables: dict):
    '''
    Simulates some command output and performs contains validations on it.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        variables   Variables to apply on the validator

    Returns:
        None
    '''
    val = tricot.get_validator(Path(__file__), 'regex', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.stdout = content

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"Regex '.+' was (:?not )?found in command output."):
            val._run(dummy_command)
