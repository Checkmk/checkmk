# -*- encoding: utf-8
# yapf: disable


checkname = 'hp_fan'


info = [['0', '2', '5'], ['1', '3', '3'], ['2', '4', '1']]


discovery = {'': [('2/0', None), ('3/1', None), ('4/2', None)]}


checks = {'': [('2/0', {}, [(0, 'ok', [])]),
               ('3/1', {}, [(1, 'underspeed', [])]),
               ('4/2', {}, [(2, 'removed', [])])]}