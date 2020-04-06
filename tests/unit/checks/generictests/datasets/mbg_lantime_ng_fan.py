# -*- encoding: utf-8
# yapf: disable


checkname = 'mbg_lantime_ng_fan'


info = [['1', '2', '1'], ['2', '2', '1'], ['3', '0', '1'], ['4', '2', '1']]


discovery = {'': [('1', None), ('2', None), ('4', None)]}


checks = {'': [('1', {}, [(2, 'off, errors: no', [])]),
               ('2', {}, [(2, 'off, errors: no', [])]),
               ('4', {}, [(2, 'off, errors: no', [])])]}