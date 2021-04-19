#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

file_1 = 'cleanup-test-one'
file_2 = 'cleanup-test-two'
test_dir = 'cleanup-test'
files = [file_1, file_2, test_dir]

config_list = [{'items': [file_1, file_2]}]
config_list.append({'items': [test_dir, file_2]})
config_list.append({'items': [f'{test_dir}/{file_1}', f'{test_dir}/{file_2}', test_dir, file_2]})
config_list.append({'items': [test_dir, file_1], 'force': True})
config_list.append({'items': [test_dir, 'nope'], 'force': True})
config_list.append({'items': ['${var1}', '${hvar}'], 'force': '${var2}'})

files_deleted = [[file_1, file_2]]
files_deleted.append([file_2])
files_deleted.append([test_dir, file_2])
files_deleted.append([test_dir, file_1])
files_deleted.append([test_dir])
files_deleted.append([test_dir, file_1])

variables = {'var1': test_dir, 'var2': True}
hotplug = {'hvar': file_1}


@pytest.mark.parametrize('config, files_deleted', zip(config_list, files_deleted))
def test_cleanup_plugin(config: dict, files_deleted: list):
    '''
    Attempts to cleanup the specified directories and checks whether they are no longer
    existent.

    Parameters:
        config          Plugin configuration
        files_deleted   List of files that should be deleted
    '''
    plug = tricot.get_plugin(Path(__file__), 'cleanup', config, variables)
    plug._run(hotplug)
    plug.stop()

    for file in files:

        file = resolve(file)

        if file.name in files_deleted:
            assert file.exists() is False

        else:
            assert file.exists()


@pytest.fixture(autouse=True)
def resource():
    '''
    Creates the files and directories for cleanup actions of the plugin.
    On exit, it also removes leftovers that have not been cleaned up.

    Parameters:
        None

    Returns:
        None
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
