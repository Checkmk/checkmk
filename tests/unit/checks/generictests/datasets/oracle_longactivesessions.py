# -*- encoding: utf-8
# yapf: disable


checkname = 'oracle_longactivesessions'


info = [['orcl',
         'TUX12C',
         'Serial Number',
         'machine',
         '0',
         'osuser',
         '4800',
         '19',
         '0'],
        ['orcl',
         'TUX12C',
         'Another Serial Number',
         'machine',
         '0',
         'another osuser',
         '4800',
         '500',
         '0'],
        ['orcl1',
         'TUX12C1',
         'Yet Another Serial Number',
         'another machine',
         '0',
         'yet another osuser',
         '5800',
         '500',
         '0']]


discovery = {'': [('orcl', {}), ('orcl', {}), ('orcl1', {})]}


checks = {'': [('orcl',
                {'levels': (500, 1000)},
                [(0,
                  '2 Session (sid,serial,proc) TUX12C Another Serial Number 0 active for 8 m from machine osuser another osuser program 4800 sql_id 0 ',
                  [('count', 2, 500, 1000, None, None)])]),
               ('orcl1',
                {'levels': (500, 1000)},
                [(0,
                  '1 Session (sid,serial,proc) TUX12C1 Yet Another Serial Number 0 active for 8 m from another machine osuser yet another osuser program 5800 sql_id 0 ',
                  [('count', 1, 500, 1000, None, None)])])]}
