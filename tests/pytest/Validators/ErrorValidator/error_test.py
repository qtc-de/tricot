#!/usr/bin/python3

import tricot
import pytest


status_code = [0, 1, 0, 1, 0]
config_list = [False, False, True, True, '${var}']
result_list = [True, False, False, True, True]
variables = {'var': False}


@pytest.mark.parametrize('status, config, result', zip(status_code, config_list, result_list))
def test_error_validator(status: int, config: bool, result: bool):
    '''
    Simulates some command status codes and performs error validations on them.

    Parameters:
        status      Current command status code
        config      Validator configuration
        result      Validation result (True = No Exception, False = Exception)

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'error', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.status = status

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"Obtained (:?no )?error, despite (:?no )?error was expected."):
            val._run(dummy_command)
