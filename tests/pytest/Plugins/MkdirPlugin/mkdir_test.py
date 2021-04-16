#!/usr/bin/python3

import os
import tricot
import pytest

from pathlib import Path

test_dir = 'mkdir-test-dir'
test_dir2 = 'mkdir-test-dir2'

config_list = [{'dirs': [test_dir, test_dir2]}]
config_list.append({'dirs': [test_dir]})
config_list.append({'dirs': [test_dir, test_dir2], 'cleanup': True})
config_list.append({'dirs': [test_dir, test_dir2], 'cleanup': True, 'force': True})

created_list = [[test_dir, test_dir2]]
created_list.append([test_dir])
created_list.append([test_dir, test_dir2])
created_list.append([test_dir, test_dir2])

cleaned_list = [[]]
cleaned_list.append([])
cleaned_list.append([test_dir2])
cleaned_list.append([test_dir, test_dir2])


def resolve(path: str) -> Path:
    '''
    '''
    return Path(__file__).parent.joinpath(path)


@pytest.mark.parametrize('config, created, cleaned', zip(config_list, created_list, cleaned_list))
def test_contains_validator(config: dict, created: list, cleaned: list):
    '''
    '''
    plug = tricot.get_plugin(Path(__file__), 'mkdir', config, {})
    plug.run()

    f = resolve(test_dir).joinpath("test")
    f.touch()

    for item in created:
        item = resolve(item)
        assert item.is_dir()

    plug.stop()

    for item in cleaned:
        item = resolve(item)
        assert item.is_dir() == False


@pytest.fixture(autouse=True)
def resource():
    '''
    '''
    yield "wait"

    f = resolve(test_dir).joinpath("test")
    f.unlink(missing_ok=True)

    r = resolve(test_dir)
    r2 = resolve(test_dir2)

    if r.is_dir():
        r.rmdir()

    if r2.is_dir():
        r2.rmdir()
