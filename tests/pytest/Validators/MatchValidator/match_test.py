#!/usr/bin/python3

import os
import tricot
import pytest

content = 'Pancake'

config_list = [{'ignore_case': False, 'value': 'Pancake'}]
config_list.append({'ignore_case': False, 'value': 'Fancake'})
config_list.append({'ignore_case': False, 'value': 'pAncAkE'})
config_list.append({'ignore_case': True, 'value': 'pAncAkE'})
config_list.append({'ignore_case': False, 'value': '${var}'})
config_list.append({'ignore_case': False, 'value': '${var1}${var2}'})

result_list = [True, False, False, True, True, True]
variable_list = [None, None, None, None, {'var': 'Pancake'}, {'var1': 'Pan'}]
hotplug_list = [None, None, None, None, None, {'var2': 'cake'}]


@pytest.mark.parametrize('config, result, variables, hotplug', zip(config_list, result_list, variable_list, hotplug_list))
def test_contains_validator(config: dict, result: bool, variables: dict, hotplug: dict):
    '''
    '''
    val = tricot.get_validator(None, 'match', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.stdout = content

    if result:
        val._run(dummy_command, hotplug)

    else:
        with pytest.raises(tricot.ValidationException, match=r"String '.+' does not match command output."):
            val._run(dummy_command, hotplug)
