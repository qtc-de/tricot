#!/usr/bin/python3

import tricot
import pytest


config_list = [['this,is,a,simple,group,def']]
config_list.append(['now,lets,try,{conditional,orlike},group,def'])
config_list.append(['{this,it},works,also,{with,using},more,than,one'])
config_list.append(['multiple,lists', 'can,also,be,defined'])
config_list.append(['{this,it},works', 'also,{with,using},orlike'])

result_list = [[['this', 'is', 'a', 'simple', 'group', 'def']]]
result_list.append([['now', 'lets', 'try', 'conditional', 'group', 'def'],
                   ['now', 'lets', 'try', 'orlike', 'group', 'def']])
result_list.append([['this', 'works', 'also', 'with', 'more', 'than', 'one'],
                   ['this', 'works', 'also', 'using', 'more', 'than', 'one'],
                   ['it', 'works', 'also', 'with', 'more', 'than', 'one'],
                   ['it', 'works', 'also', 'using', 'more', 'than', 'one']])
result_list.append([['multiple', 'lists'], ['can', 'also', 'be', 'defined']])
result_list.append([['this', 'works'], ['also', 'with', 'orlike'],
                   ['this', 'works'], ['also', 'using', 'orlike'],
                   ['it', 'works'], ['also', 'with', 'orlike'],
                   ['it', 'works'], ['also', 'using', 'orlike']])


@pytest.mark.parametrize('config, results', zip(config_list, result_list))
def test_group_parsing(config, results):
    '''
    Check whether group specifications are parsed correctly.
    '''
    groups = tricot.utils.parse_groups(config)

    for group in groups:
        assert group in results
