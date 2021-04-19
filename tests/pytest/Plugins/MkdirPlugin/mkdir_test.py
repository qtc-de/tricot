#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

test_dir = 'mkdir-test-dir'
test_dir2 = 'mkdir-test-dir2'

config_list = [{'dirs': [test_dir, test_dir2]}]
config_list.append({'dirs': [test_dir]})
config_list.append({'dirs': [test_dir, test_dir2], 'cleanup': True})
config_list.append({'dirs': [test_dir, test_dir2], 'cleanup': True, 'force': True})
config_list.append({'dirs': ['${var1}', '${hvar}'], 'cleanup': '${var2}', 'force': True})

created_list = [[test_dir, test_dir2]]
created_list.append([test_dir])
created_list.append([test_dir, test_dir2])
created_list.append([test_dir, test_dir2])
created_list.append([test_dir, test_dir2])

cleaned_list = [[]]
cleaned_list.append([])
cleaned_list.append([test_dir2])
cleaned_list.append([test_dir, test_dir2])
cleaned_list.append([test_dir, test_dir2])

variables = {'var1': test_dir, 'var2': True}
hotplug = {'hvar': test_dir2}


@pytest.mark.parametrize('config, created, cleaned', zip(config_list, created_list, cleaned_list))
def test_mkdir_plugin(config: dict, created: list, cleaned: list):
    '''
    Attempts to create some test directories and optionally tries to delete them.

    Parameters:
        config          Plugin configuration
        created         List of filenames that should be created
        cleaned         List of filenames that should be removed

    Returns:
        None
    '''
    plug = tricot.get_plugin(Path(__file__), 'mkdir', config, variables)
    plug._run(hotplug)

    f = resolve(test_dir).joinpath("test")
    f.touch()

    for item in created:
        item = resolve(item)
        assert item.is_dir()

    plug.stop()

    for item in cleaned:
        item = resolve(item)
        assert item.is_dir() is False


@pytest.fixture(autouse=True)
def resource():
    '''
    Removes leftover directories that were not cleaned by the plugin.

    Parameters:
        None

    Returns:
        None
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
