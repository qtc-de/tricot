#!/usr/bin/python3

import tricot
import pytest


content = '''This is a text file.
It contains some contents.
It is used for testing tricot.
It is basically a replacement for command output.
'''

config_list = [{'ignore_case': False, 'values': ['This is a text file', 'It is basically'], 'invert': ['Pancake']}]
config_list.append({'ignore_case': False, 'values': ['This is a text file', 'It is basically'], 'invert': ['This']})
config_list.append({'ignore_case': False, 'values': ['This is a text file', 'It is basically'], 'invert': ['this']})
config_list.append({'ignore_case': True, 'values': ['this is a text file', 'it is basically'], 'invert': ['this']})
config_list.append({'ignore_case': True, 'values': ['this is a tuxt file', 'it is basically'], 'invert': ['this']})
config_list.append({'ignore_case': True, 'values': ['this is a text file', 'it is basically']})
config_list.append({'ignore_case': True, 'values': ['this is a ${var} file', 'it ${var2} ${var3}']})
config_list.append({'ignore_case': True, 'values': ['this is a text file', 'it is ${var3}']})

result_list = [True, False, True, False, False, True, True, False]
variable_list = [None, None, None, None, None, None, {'var': 'text', 'var2': 'is'}, None]
hotplug_list = [None, None, None, None, None, None, {'var3': 'basically'}, {'var3': 'basicalli'}]


@pytest.mark.parametrize('config, result, variables, hotplug', zip(config_list, result_list, variable_list, hotplug_list))
def test_contains_validator(config: dict, result: bool, variables: dict, hotplug: dict):
    '''
    Simulates some command output and performs contains validations on it.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        variables   Variables to apply on the validator
        hotplug     Hotplug Variables to apply on the validator

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'contains', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.stdout = content

    if result:
        val._run(dummy_command, hotplug)

    else:
        with pytest.raises(tricot.ValidationException, match=r"String '.+' was (:?not )?found in command output."):
            val._run(dummy_command, hotplug)
