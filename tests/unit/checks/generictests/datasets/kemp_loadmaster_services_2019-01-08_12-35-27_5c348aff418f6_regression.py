# -*- encoding: utf-8
# yapf: disable


checkname = u'kemp_loadmaster_services'


info = [['Foo', '1', '0'], ['Bar', '8', '0']]


discovery = {'': [('Bar', 'kemp_loadmaster_service_default_levels'),
                  ('Foo', 'kemp_loadmaster_service_default_levels')]}


checks = {'': [('Bar',
                (1500, 2000),
                [(3, 'Status: unknown[8]', []),
                 (0,
                  'Active connections: 0',
                  [('conns', 0, None, None, None, None)])]),
               ('Foo',
                (1500, 2000),
                [(0, 'Status: in service', []),
                 (0,
                  'Active connections: 0',
                  [('conns', 0, None, None, None, None)])])]}