#!/usr/bin/python3

import tricot
import pytest
import requests

from pathlib import Path
from functools import partial


resolve = partial(tricot.resolve, __file__)

www_dir = 'www'
www = str(resolve(www_dir))

test_file = 'http-test-file.txt'

config_list = [{'port': 8000, 'dir': www}]
config_list.append({'port': 8000, 'dir': www})
config_list.append({'port': 999999, 'dir': www})

result = [True, True, False, False]
files = [test_file, 'nope', None, None]
status = [200, 404, None, None]


@pytest.mark.parametrize('config, result, status, file', zip(config_list, result, status, files))
def test_http_listener_plugin(config: dict, result: bool, status: int, file: str):
    '''
    Creates a HTTP listener using the specified plugin configuration. After successful creation,
    some HTTP requests using the requests module are attempted.

    Parameters:
        config          Plugin configuration
        result          Whether or not creation of the listener should succeed
        status          Expected status code from the server on HTTP requests
        file            File to request from the HTTP server

    Returns:
        None
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
    On startup, it creates the directory and a testfile that are served by the HTTP server.
    On exit, it cleanes up the corresponding files.

    Parameters:
        None

    Returns:
        None
    '''
    d = resolve(www_dir)
    d.mkdir()

    with open(d.joinpath(test_file), 'w') as f:
        f.write("Hello World :D")

    yield "wait"

    d.joinpath(test_file).unlink()
    d.rmdir()
