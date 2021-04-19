#!/usr/bin/python3

import tricot
import pytest


content = '''This is a text file.
It contains some contents.
It is used for testing tricot.
It is basically a replacement for command output.
'''

config_list = [{'ignore_case': False, 'values': ['It', 'for'], 'counts': [3, 2]}]
config_list.append({'ignore_case': False, 'values': ['It', 'for'], 'counts': [2, 2]})
config_list.append({'ignore_case': False, 'values': ['ii', 'for'], 'counts': [3, 2]})
config_list.append({'ignore_case': True, 'values': ['EX', 'FOR'], 'counts': [1, 2]})
config_list.append({'ignore_case': True, 'values': ['${var1}', 'FOR'], 'counts': ['${var2}', 2]})

result_list = [True, False, False, True, True]
variable_list = [None, None, None, None, {'var2': 1}]
hotplug_list = [None, None, None, None, {'var1': 'EX'}]


@pytest.mark.parametrize('config, result, variables, hotplug', zip(config_list, result_list, variable_list, hotplug_list))
def test_count_validator(config: dict, result: bool, variables: dict, hotplug: dict):
    '''
    Simulates some command output and performs count validations on it.

    Parameters:
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)
        variables   Variables to apply on the validator
        hotplug     Hotplug Variables to apply on the validator

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'count', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.stdout = content

    if result:
        val._run(dummy_command, hotplug)

    else:
        match = r"String '.+' was found \d+ times, but was expected \d+ times."
        with pytest.raises(tricot.ValidationException, match=match):
            val._run(dummy_command, hotplug)
