#!/usr/bin/python3

import os
import tricot
import pytest

status_code = [0, 1, 0, 2, 55]
config_list = [0, 1, 1, 0, '${var}']
result_list = [True, True, False, False, True]
variables = {'var': 55}

@pytest.mark.parametrize('status, config, result', zip(status_code, config_list, result_list))
def test_contains_validator(status: int, config: bool, result: bool):
    '''
    '''
    val = tricot.get_validator(None, 'status', config, variables)

    dummy_command = tricot.Command(None)
    dummy_command.status = status

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"Obtained status code '.+' does not match the expected code '.+'."):
            val._run(dummy_command)
