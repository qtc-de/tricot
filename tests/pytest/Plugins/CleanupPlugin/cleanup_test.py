#!/usr/bin/python3

import os
import tricot
import pytest

from pathlib import Path

file_1 = 'cleanup-test-one'
file_2 = 'cleanup-test-two'
test_dir = 'cleanup-test'

config_list = [{'items': [file_1, file_2]}]
config_list.append({'items': [test_dir, file_2]})
config_list.append({'items': [f'{test_dir}/{file_1}', f'{test_dir}/{file_2}', test_dir, file_2]})
config_list.append({'items': [test_dir, file_1], 'force': True})
config_list.append({'items': [test_dir, 'nope'], 'force': True})

files = [file_1, file_2, test_dir]
files_deleted = [[file_1, file_2]]
files_deleted.append([file_2])
files_deleted.append([test_dir, file_2])
files_deleted.append([test_dir, file_1])
files_deleted.append([test_dir])


def resolve(path: str) -> Path:
    '''
    '''
    return Path(__file__).parent.joinpath(path)


@pytest.mark.parametrize('config, files_deleted', zip(config_list, files_deleted))
def test_contains_validator(config: dict, files_deleted: list):
    '''
    '''
    plug = tricot.get_plugin(Path(__file__), 'cleanup', config, {})
    plug.stop()

    for file in files:

        if file in files_deleted:
            assert os.path.exists(file) == False

        else:
            assert os.path.exists(file) == True


@pytest.fixture(autouse=True)
def resource():
    '''
    '''
    resolve(file_1).touch()
    resolve(file_2).touch()
    d = resolve(test_dir)

    d.mkdir()
    d.joinpath(file_1).touch()
    d.joinpath(file_2).touch()

    yield "wait"

    resolve(file_1).unlink(missing_ok=True)
    resolve(file_2).unlink(missing_ok=True)
    d.joinpath(file_1).unlink(missing_ok=True)
    d.joinpath(file_2).unlink(missing_ok=True)

    if d.is_dir():
        d.rmdir()
