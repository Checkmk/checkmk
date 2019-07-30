# -*- encoding: utf-8
# yapf: disable


checkname = 'kemp_loadmaster_services'


info = [['vs adaptive method type', '1', '100'],
        ['another vs adaptive method type', '1', '200'],
        ['yet another vs adaptive method type', '4', '100']]


discovery = {'': [('another vs adaptive method type',
                   'kemp_loadmaster_service_default_levels'),
                  ('vs adaptive method type', 'kemp_loadmaster_service_default_levels')]}


checks = {'': [('another vs adaptive method type',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 200',
                  [('conns', 200, None, None, None, None)])]),
               ('vs adaptive method type',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 100',
                  [('conns', 100, None, None, None, None)])])]}
