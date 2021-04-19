#!/usr/bin/python3

import tricot
import pytest


runtime = [4.5, 2, 2, 33, 55]

config_list = [{'lt': 5, 'gt': 4}]
config_list.append({'lt': 1})
config_list.append({'gt': 4})
config_list.append({'eq': 33})
config_list.append({'lt': '${var1}', '${var2}': 1})

result_list = [True, False, False, True, True]
variables = {'var1': 100, 'var2': 'gt'}


@pytest.mark.parametrize('runtime, config, result', zip(runtime, config_list, result_list))
def test_runtime_validator(runtime: int, config: bool, result: bool):
    '''
    Simulates a command runtime and performs runtime validations on it.

    Parameters:
        runtime     Current command runtime
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'runtime', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.runtime = runtime

    if result:
        val._run(dummy_command)

    else:
        match = r"Command execution took \d+(:?\.\d+)?s \(expected: runtime [=<>]{1,2} \d+(:?\.\d+)?s\)"
        with pytest.raises(tricot.ValidationException, match=match):
            val._run(dummy_command)
