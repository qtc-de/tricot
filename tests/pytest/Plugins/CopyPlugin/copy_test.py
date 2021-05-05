#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

test_dir = 'copy-test-dir'
test_dir2 = 'copy-test-dir2'
test_file = 'copy-test-file'
test_file2 = 'copy-test-file2'


config_list = [
                    {
                     'from': [test_file, f'{test_dir2}/{test_file}'],
                     'to': [test_dir, f'{test_dir}/{test_file2}']
                    }
              ]
config_list.append(
                    {
                     'from': [test_file, f'{test_dir2}/{test_file}'],
                     'to': [test_dir, f'{test_dir}/{test_file2}'],
                     'cleanup': True
                    }
                  )
config_list.append(
                    {
                     'from': [test_dir2],
                     'to': [test_dir],
                     'cleanup': True,
                    }
                  )
config_list.append(
                    {
                     'from': [test_dir2],
                     'to': [f'{test_dir}/{test_dir}'],
                     'cleanup': True,
                    }
                  )

created_list = [[f'{test_dir}/{test_file}', f'{test_dir}/{test_file2}']]
created_list.append([f'{test_dir}/{test_file}', f'{test_dir}/{test_file2}'])
created_list.append([f'{test_dir}/{test_dir2}'])
created_list.append([f'{test_dir}/{test_dir}'])

cleaned_list = [False]
cleaned_list.append(True)
cleaned_list.append(True)
cleaned_list.append(True)


@pytest.mark.parametrize('config, created, cleanup', zip(config_list, created_list, cleaned_list))
def test_copy_plugin(config: dict, created: list, cleanup: bool):
    '''
    Attempts to copy some files around and optionally tries to delete them.

    Parameters:
        config          Plugin configuration
        created         List of filenames that should be created
        cleanup         Whether copied files should be removed during the stop action

    Returns:
        None
    '''
    plug = tricot.get_plugin(Path(__file__), 'copy', config, {})
    plug._run()

    for item in created:
        item = resolve(item)
        assert item.exists()

    plug._stop()

    if cleanup:
        for item in created:
            item = resolve(item)
            assert item.exists() is False


@pytest.fixture(autouse=True)
def resource():
    '''
    Creates some files to copy and removes possible leftovers.

    Parameters:
        None

    Returns:
        None
    '''
    dir1 = resolve(test_dir)
    dir2 = resolve(test_dir2)
    file = resolve(test_file)
    file2 = dir2.joinpath(test_file)

    dir1.mkdir()
    dir2.mkdir()
    file.touch()
    file2.touch()

    yield "wait"

    file3 = dir1.joinpath(test_file)
    file4 = dir1.joinpath(test_file2)
    file5 = dir1.joinpath(file2)

    file.unlink(missing_ok=True)
    file2.unlink(missing_ok=True)
    file3.unlink(missing_ok=True)
    file4.unlink(missing_ok=True)
    file5.unlink(missing_ok=True)

    dir3 = dir1.joinpath(test_dir)
    dir4 = dir1.joinpath(test_dir2)

    if dir3.is_dir():
        dir3.rmdir()

    if dir4.is_dir():
        dir4.rmdir()

    if dir1.is_dir():
        dir1.rmdir()

    if dir2.is_dir():
        dir2.rmdir()
