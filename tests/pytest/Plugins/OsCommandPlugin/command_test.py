#!/usr/bin/python3

import tricot
import pytest
import timeit

from pathlib import Path

test_dir = 'mkdir-test-dir'


def resolve(path: str) -> Path:
    '''
    '''
    return Path(__file__).parent.joinpath(path)


def test_plain():
    '''
    '''
    config = {'cmd': ['mkdir', test_dir]}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
    plug._run()

    r = resolve(test_dir)
    assert r.is_dir()
    r.rmdir()


def test_fail():
    '''
    '''
    config = {'cmd': ['nopenopenope']}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()


def test_fail2():
    '''
    '''
    config = {'cmd': ['cat', 'nopenopenope']}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()


def test_ignore():
    '''
    '''
    config = {'cmd': ['cat', 'nopenopenopenope'], 'ignore_error': True}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
    plug._run()


def test_timeout():
    '''
    '''
    config = {'cmd': ['sleep', '5'], 'timeout': 1}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
    with pytest.raises(tricot.plugin.PluginException, match=r"PluginException"):
        plug._run()


def test_background():
    '''
    '''
    config = {'cmd': ['sleep', '5'], 'background': True}

    plug = tricot.get_plugin(Path(__file__), 'os_command', config, {})
        
    timer = timeit.Timer(lambda: plug._run())
    assert timer.timeit(number=1) < 1
