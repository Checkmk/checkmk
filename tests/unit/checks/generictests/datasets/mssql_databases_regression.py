# yapf: disable

checkname = 'mssql_databases'


info = [['MSSQL_MSSQL46', 'CorreLog_Report_T', 'ONLINE', 'FULL', '0', '0'],
        ['MSSQL_MSSQL46', 'master', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL_MSSQL46', 'msdb', 'ONLINE', 'SIMPLE', '0', '0'],
        ['MSSQL_MSSQL46', 'NOC_ALARM_T', 'ONLINE', 'FULL', '0', '1'],
        ['MSSQL_MSSQL46', 'test_autoclose', 'ONLINE', 'FULL', '1', '0'],
        ['MSSQL_MSSQL46', 'test_autoclose', 'RECOVERY', 'PENDING', 'FULL', '1', '0']]


discovery = {'': [('MSSQL_MSSQL46 CorreLog_Report_T', {}),
                  ('MSSQL_MSSQL46 NOC_ALARM_T', {}),
                  ('MSSQL_MSSQL46 master', {}),
                  ('MSSQL_MSSQL46 msdb', {}),
                  ('MSSQL_MSSQL46 test_autoclose', {})]}


checks = {'': [('MSSQL_MSSQL46 CorreLog_Report_T',
                {},
                [(0, 'Status: ONLINE', []),
                 (0, 'Recovery: FULL', []),
                 (0, 'Auto close: off', []),
                 (0, 'Auto shrink: off', [])]),
               ('MSSQL_MSSQL46 NOC_ALARM_T',
                {},
                [(0, 'Status: ONLINE', []),
                 (0, 'Recovery: FULL', []),
                 (0, 'Auto close: off', []),
                 (1, 'Auto shrink: on', [])]),
               ('MSSQL_MSSQL46 master',
                {},
                [(0, 'Status: ONLINE', []),
                 (0, 'Recovery: SIMPLE', []),
                 (0, 'Auto close: off', []),
                 (0, 'Auto shrink: off', [])]),
               ('MSSQL_MSSQL46 msdb',
                {},
                [(0, 'Status: ONLINE', []),
                 (0, 'Recovery: SIMPLE', []),
                 (0, 'Auto close: off', []),
                 (0, 'Auto shrink: off', [])]),
               ('MSSQL_MSSQL46 test_autoclose',
                {},
                [(0, 'Status: ONLINE', []),
                 (0, 'Recovery: FULL', []),
                 (1, 'Auto close: on', []),
                 (0, 'Auto shrink: off', [])])]}
