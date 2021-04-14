#!/usr/bin/python3

import os
import tricot
import pytest

from pathlib import Path


file_1 = 'file-exists-test-one'
file_2 = 'file-exists-test-two'

config_list = [{'files': [file_1, file_2]}]
config_list.append({'files': [file_1, file_2], 'invert': ['nope']})
config_list.append({'files': [file_2], 'invert': [file_1]})
config_list.append({'files': ['nope'], 'invert': ['nope']})
config_list.append({'files': [file_1, file_2], 'cleanup': True})

result_list = [True, True, False, False, True]
file_deleted = [False, False, False, False, True]


@pytest.mark.parametrize('config, result, deleted', zip(config_list, result_list, file_deleted))
def test_contains_validator(config: dict, result: bool, deleted: bool):
    '''
    '''
    val = tricot.get_validator(Path(__file__), 'file_exists', config, {})
    Path(file_1).touch()
    Path(file_2).touch()

    dummy_command = tricot.Command([])

    if result:
        val._run(dummy_command)

    else:
        with pytest.raises(tricot.ValidationException, match=r"File '.+' does (:?not )?exist."):
            val._run(dummy_command)

    if deleted:
        assert not os.path.isfile(file_1)

    else:
        assert os.path.isfile(file_2)
