#!/usr/bin/python3

import tricot
import pytest


content1 = 'Test'
content2 = content1 + '\n\nTest'
content3 = content2 + '\nTest'

outputs = [content1, content2, content2, content3, content3]
configs = [{'count': 1}, {'count': 3}, {'ignore_empty': True, 'count': 2}, {'count': 4}, {'count': 99}]
results = [True, True, True, True, False]

@pytest.mark.parametrize('output, config, result', zip(outputs, configs, results))
def test_status_code_validator(output: int, config: dict, result: bool):
    '''
    Simulates some command output and performs line count validation on it.

    Parameters:
        output      Current command output
        count       Expected line count
        result      Expected result (Success or Failure)

    Returns:
        None
    '''
    val = tricot.get_validator(None, 'line_count', config, {})

    dummy_command = tricot.Command(None)
    dummy_command.stdout = output

    if result:
        val._run(dummy_command)

    else:
        match = r"Command output has '\d+' line\(s\), but '\d+' lines were expected."
        with pytest.raises(tricot.ValidationException, match=match):
            val._run(dummy_command)
