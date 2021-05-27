#!/usr/bin/python3

import tricot
import pytest


content1 = 'Test'
content2 = content1 + '\n\nTest'
content3 = content2 + '\nTest'
content4 = content3 + '\n\n\n'
content5 = '\n\n\n' + content3
content6 = content5 + content4

outputs = [content1, content2, content2, content3, content3, content4, content4, content5, content5, content6, content6]

configs = [{'count': 1}]
configs.append({'count': 3})
configs.append({'ignore_empty': True, 'count': 2})
configs.append({'count': 4})
configs.append({'count': 99})
configs.append({'count': 4})
configs.append({'count': 7, 'keep_trailing': True})
configs.append({'count': 4})
configs.append({'count': 7, 'keep_leading': True})
configs.append({'count': 7})
configs.append({'count': 13, 'keep_leading': True, 'keep_trailing': True})

results = [True, True, True, True, False, True, True, True, True, True, True]


@pytest.mark.parametrize('output, config, result', zip(outputs, configs, results))
def test_line_count_validator(output: int, config: dict, result: bool):
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
