#!/usr/bin/python3

import tricot
import pytest


config_list = [['this,is,a,simple,group,def']]
config_list.append(['now,lets,try,{conditional,orlike},group,def'])
config_list.append(['{this,it},works,also,{with,using},more,than,one'])
config_list.append(['multiple,lists', 'can,also,be,defined'])
config_list.append(['{this,it},works', 'also,{with,using},orlike'])
config_list.append(['lets,add,*,some,wildcards'])
config_list.append(['lets,add,**,some,wildcards'])
config_list.append(['lets,*,**,some,wildcards'])
config_list.append(['**,some,wildcards'])

match_list = [[([['this', 'is', 'a', 'simple', 'group', 'def']], True), ([['nope']], False)]]
match_list.append([([['now', 'lets', 'try', 'conditional', 'group', 'def']], True),
                   ([['now', 'lets', 'try', 'orlike', 'group', 'def']], True),
                   ([['now', 'lets', 'tri', 'orlike', 'group', 'def']], False)])
match_list.append([([['this', 'works', 'also', 'with', 'more', 'than', 'one']], True),
                   ([['this', 'works', 'also', 'using', 'more', 'than', 'one']], True),
                   ([['it', 'works', 'also', 'with', 'more', 'than', 'one']], True),
                   ([['it', 'works', 'also', 'using', 'more', 'than', 'one']], True),
                   ([['ot', 'works', 'also', 'using', 'more', 'than', 'one']], False)])
match_list.append([([['aaaa', 'bbbb', 'cccc'], ['dddd', 'eeee']], False),
                   ([['aaaa', 'bbbb', 'cccc'], ['multiple', 'lists']], True),
                   ([['can', 'also', 'be', 'defined'], ['aaaa', 'bbbb']], True)])
match_list.append([([['aaaa', 'bbbb', 'cccc'], ['dddd', 'eeee']], False),
                   ([['this', 'works'], ['multiple', 'lists']], True),
                   ([['also', 'using', 'orlike'], ['aaaa', 'bbbb']], True)])
match_list.append([([['lets', 'add', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], True),
                   ([['lets', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], False)])
match_list.append([([['lets', 'add', 'hi :)', 'hi :D', 'some', 'wildcards'], ['dddd', 'eeee']], True),
                   ([['lets', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], False)])
match_list.append([([['lets', 'add', 'hi :)', 'hi :D', 'some', 'wildcards'], ['dddd', 'eeee']], True),
                   ([['lets', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], True)])
match_list.append([([['lets', 'add', 'hi :)', 'hi :D', 'some', 'wildcards'], ['dddd', 'eeee']], True),
                   ([['lets', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], True),
                   ([['aaaaa', 'hi :)', 'some', 'wildcards'], ['dddd', 'eeee']], True)])


@pytest.mark.parametrize('config, match', zip(config_list, match_list))
def test_group_matching(config, match):
    '''
    Check whether group matches are matching as expected
    '''
    for tupl in match:

        groups = tricot.utils.parse_groups(config)
        assert tricot.utils.groups_contain(groups, tupl[0]) == tupl[1]
