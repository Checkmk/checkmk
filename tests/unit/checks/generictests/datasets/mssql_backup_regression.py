# yapf: disable

checkname = "mssql_backup"


info = [
     ['MSSQL_SQL0x4', 'master', '2016-07-08 20:20:27', 'D'],
     ['MSSQL_SQL0x4', 'model', '2016-07-08 20:20:28', 'D'],
     ['MSSQL_SQL0x4', 'model', '2016-07-12 09:09:42', 'L'],
     ['MSSQL_SQL0x4', 'model', '2016-07-11 20:20:07', 'I'],
     ['MSSQL_SQL0x4', 'msdb', '2016-07-08', '20:20:43', 'D'],
     ['MSSQL_SQL0x4', 'msdb', '-', '-', '-', 'no backup found'],
     ['MSSQL_SQL0x4', 'foo'],
     ['MSSQL_SQL0x4', 'bar', '12345678'],
     ['MSSQL_Parrot', 'Polly', '-', '-', '-', 'ERROR: Polly has no crackers']
]

extra_sections = {
    '': [{u'SQL0x4 master': {'DBname': u'master',
                             'Instance': u'MSSQLSERVER',
                             'Recovery': u'SIMPLE',
                             'Status': u'ONLINE',
                             'auto_close': u'0',
                             'auto_shrink': u'0'},
          u'SQL0x4 model': {'DBname': u'model',
                            'Instance': u'MSSQLSERVER',
                            'Recovery': u'FULL',
                            'Status': u'ONLINE',
                            'auto_close': u'0',
                            'auto_shrink': u'0'},
          u'SQL0x4 msdb': {'DBname': u'msdb',
                           'Instance': u'MSSQLSERVER',
                           'Recovery': u'SIMPLE',
                           'Status': u'ONLINE',
                           'auto_close': u'0',
                           'auto_shrink': u'0'},
          u'SQL0x4 foo': {},
          u'SQL0x4 bar': None,
          u'Parrot Polly': {'DBname': u'Polly' },
        }]
}

discovery = {
    '': [
        ("MSSQL_SQL0x4 master", {}),
        ("MSSQL_SQL0x4 model", {}),
        ("MSSQL_SQL0x4 msdb", {}),
        ("MSSQL_SQL0x4 bar", {}),
        ("MSSQL_Parrot Polly", {}),
    ],
    'per_type': [],
}
