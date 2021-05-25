#!/usr/bin/python3

import tricot
import pytest

from pathlib import Path
from functools import partial


test_dir = 'mkdir-test-dir'
resolve = partial(tricot.resolve, __file__)


def test_cleanup_command_plain():
    '''
    Test if plain command execution is working by creating a directory.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['mkdir', test_dir]}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    plug.stop()

    r = resolve(test_dir)
    assert r.is_dir()
    r.rmdir()


def test_cleanup_command_variable():
    '''
    Test if plain command execution is working by creating a directory.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['mkdir', '${var}']}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {'var': test_dir})
    plug.stop()

    r = resolve(test_dir)
    assert r.is_dir()
    r.rmdir()


def test_cleanup_command_hotplug():
    '''
    Test if plain command execution is working by creating a directory.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['mkdir', '${var}']}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    plug._run({'var': test_dir})
    plug._stop()

    r = resolve(test_dir)
    assert r.is_dir()
    r.rmdir()


def test_cleanup_command_fail():
    '''
    Test if a wrong command specification leads to a PluginException.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['nopenopenope']}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()
        plug._stop()


def test_cleanup_command_fail2():
    '''
    Test that a command that exits with a non zero status code leads to an error.

    Parameters:
            None

    Returns:
            None
    '''
    config = {'cmd': ['cat', 'nopenopenope']}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()
        plug._stop()


def test_cleanup_command_ignore():
    '''
    Test that a command that exits with a non zero status code is ignored then
    'ignore_error' was specified.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['cat', 'nopenopenopenope'], 'ignore_error': True}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    plug.stop()


def test_cleanup_command_timeout():
    '''
    Test that plugins timeout correctly and throw a PluginException.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['sleep', '5'], 'timeout': 1}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()
        plug._stop()


def test_cleanup_command_shell():
    '''
    Test if plain command execution is working by creating a directory in shell mode.

    Parameters:
        None

    Returns:
        None
    '''
    config = {'cmd': ['echo', 'hi', '&&', 'mkdir', test_dir], 'shell': True}

    plug = tricot.get_plugin(Path(__file__), 'cleanup_command', config, {})
    plug.stop()

    r = resolve(test_dir)
    assert r.is_dir()
    r.rmdir()


@pytest.fixture(autouse=True)
def resource():
    '''
    Handle cleanup of temporary created directories.

    Parameters:
        None

    Returns:
        None
    '''
    yield "wait"

    d = resolve(test_dir)
    if d.is_dir():
        d.rmdir()
