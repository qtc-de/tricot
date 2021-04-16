#!/usr/bin/python3

import os
import tricot
import pytest
import requests

from pathlib import Path


www_dir = 'www'
test_file = 'http-test-file.txt'

config_list = [{'port': 8000, 'dir': 'www'}]
config_list.append({'port': 8000, 'dir': 'www'})
config_list.append({'port': 999999, 'dir': 'www'})
config_list.append({'port': 8000, 'dir': 'wwwwww'})

result = [True, True, False, False]
files = [test_file, 'nope', None, None]
status = [200, 404, None, None]


def resolve(path: str) -> Path:
    '''
    '''
    return Path(__file__).parent.joinpath(path)


@pytest.mark.parametrize('config, result, status, file', zip(config_list, result, status, files))
def test_contains_validator(config: dict, result: bool, status: int, file: str):
    '''
    '''
    if not result:
        error_match = r"Specified port '.+' is invalid. Needs to be between 0-65535."
        error_match += r"|Specified directory '.+' does not exist."

        with pytest.raises(tricot.plugin.PluginError, match=error_match):
            plug = tricot.get_plugin(Path(__file__), 'http_listener', config, {})
            plug.run()

        return

    else:
        plug = tricot.get_plugin(Path(__file__), 'http_listener', config, {})
        plug.run()

    r = requests.get(f'http://127.0.0.1:8000/{file}')
    assert r.status_code == status

    if status == 200:
        assert 'Hello World' in r.text

    plug.stop()


@pytest.fixture(autouse=True)
def resource():
    '''
    '''
    d = resolve(www_dir)
    d.mkdir()

    with open(d.joinpath(test_file), 'w') as f:
        f.write("Hello World :D")

    yield "wait"

    d.joinpath(test_file).unlink()
    d.rmdir()
