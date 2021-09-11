#!/usr/bin/python3

import re
import tricot
import pytest


content = '''
This is some example text to test the regex extractor.
Here is a good example for a match group: 1000:false
Hello,Hi,Huhu,Hola,Hoi,Hihi
2000:true
'''

config_list = [{'pattern': r'(\d+):(.+)', 'variable': 'test'}]
config_list.append({'pattern': r'(\d+):FALSE', 'variable': 'test'})
config_list.append({'pattern': r'(\d+):FALSE', 'ignore_case': True, 'variable': 'test'})
config_list.append({'pattern': r'(\d+):false$', 'variable': 'test'})
config_list.append({'pattern': r'(\d+):false$', 'multiline': True, 'variable': 'test'})
config_list.append({'pattern': r'(\d+):(.+)Hello', 'variable': 'test'})
config_list.append({'pattern': r'(\d+):(.+)Hello', 'dotall': True, 'variable': 'test'})
config_list.append({'pattern': r'^([^,\n]+),([^,]+),([^,]+),([^,]+),([^,]+),([^,\n]+)$', 'multiline': True, 'variable': 'test'})

result_list = list()
result_list.append({'test': '1000:false', 'test-0': '1000:false', 'test-0-0': '1000:false', 'test-0-1': '1000',
                    'test-0-2': 'false', 'test-1': '2000:true', 'test-1-0': '2000:true', 'test-1-1': '2000', 'test-1-2': 'true'})
result_list.append(dict())
result_list.append({'test': '1000:false', 'test-0': '1000:false', 'test-0-0': '1000:false', 'test-0-1': '1000'})
result_list.append(dict())
result_list.append({'test': '1000:false', 'test-0': '1000:false', 'test-0-0': '1000:false', 'test-0-1': '1000'})
result_list.append(dict())
result_list.append({'test': '1000:false\nHello', 'test-0': '1000:false\nHello', 'test-0-0': '1000:false\nHello',
                    'test-0-1': '1000', 'test-0-2': 'false\n'})
result_list.append({'test': 'Hello,Hi,Huhu,Hola,Hoi,Hihi', 'test-0': 'Hello,Hi,Huhu,Hola,Hoi,Hihi', 'test-0-0': 'Hello,Hi,Huhu,Hola,Hoi,Hihi',
                    'test-0-1': 'Hello', 'test-0-2': 'Hi', 'test-0-3': 'Huhu', 'test-0-4': 'Hola', 'test-0-5': 'Hoi', 'test-0-6': 'Hihi'})

@pytest.mark.parametrize('config, result', zip(config_list, result_list))
def test_regex_extractor(config: dict, result: dict):
    '''
    Simulates some command output and tries to extract values from it.

    Parameters:
        config      Validator configuration
        result      Extractor configuration

    Returns:
        None
    '''
    ext = tricot.get_extractor(None, 'regex', config, {})

    dummy_command = tricot.Command(None)
    dummy_command.stdout = content

    hotplug = {}

    if not result:

        match = r"RegexExtractor did not find pattern '{}' within the output.".format(config['pattern'])
        with pytest.raises(tricot.ExtractException, match=re.escape(match)):
            ext._extract(dummy_command, hotplug)

    else:
        ext._extract(dummy_command, hotplug)

        for key, value in result.items():
            assert hotplug[key] == value
