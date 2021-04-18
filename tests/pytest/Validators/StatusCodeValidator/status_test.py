#!/usr/bin/python3

import tricot
import pytest


status_code = [0, 1, 0, 2, 55]
config_list = [0, 1, 1, 0, '${var}']
result_list = [True, True, False, False, True]
variables = {'var': 55}


@pytest.mark.parametrize('status, config, result', zip(status_code, config_list, result_list))
def test_status_code_validator(status: int, config: bool, result: bool):
    '''
    Simulates some command status and performs status validations on it.

    Parameters:
        status      Current command status
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'status', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.status = status

    if result:
        val._run(dummy_command)

    else:
        match = r"Obtained status code '.+' does not match the expected code '.+'."
        with pytest.raises(tricot.ValidationException, match=match):
            val._run(dummy_command)
