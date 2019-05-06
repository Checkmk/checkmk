# yapf: disable


checkname = 'oracle_dataguard_stats'


info = [['TESTDB',
         'TESTDBU2',
         'PHYSICAL STANDBYapply finish time',
         '+00 00:00:00.000',
         'NOT ALLOWED',
         'ENABLED',
         'MAXIMUM',
         'PERFORMANCE',
         'DISABLED',
         '',
         '',
         '',
         'APPLYING_LOG'],
        ['TUX12C', 'TUXSTDB', 'PHYSICAL STANDBY', 'transport lag', '+00 00:00:00'],
        ['TUX12C', 'TUXSTDB', 'PHYSICAL STANDBY', 'apply lag', '+00 00:28:57'],
        ['TUX12C',
         'TUXSTDB',
         'PHYSICAL STANDBY',
         'apply finish time',
         '+00 00:00:17.180'],
        ['TUX12C', 'TUXSTDB', 'PHYSICAL STANDBY', 'estimated startup time', '20']]


discovery = {'': [('TESTDB.TESTDBU2', {}), ('TUX12C.TUXSTDB', {})]}


checks = {'': [('TESTDB.TESTDBU2',
                {'apply_lag': (3600, 14400)},
                [(0, 'Database Role physical standbyapply finish time', []),
                 (0, 'Protection Mode performance', []),
                 (0, 'Broker maximum', [])]),
               ('TUX12C.TUXSTDB',
                {'apply_lag': (3600, 14400)},
                [
                 (0, 'Database Role physical standby', []),
                 (0,
                  'apply finish time 17.0 s',
                  [('apply_finish_time', 17, None, None, None, None)]),
                 (0,
                  'apply lag 28 m',
                  [('apply_lag', 1737, 3600, 14400, None, None)]),
                 (0,
                  'transport lag 0.00 s',
                  [('transport_lag', 0, None, None, None, None)]),
])]}
