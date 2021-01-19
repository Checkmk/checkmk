# -*- encoding: utf-8
# yapf: disable


checkname = 'mssql_counters'


info = [[None,
         u'SQLServer:Databases',
         u'data_file(s)_size_(kb)',
         u'ReviewInSight',
         u'4160'],
        [None,
         u'SQLServer:Databases',
         u'log_file(s)_size_(kb)',
         u'ReviewInSight',
         u'2104'],
        [None,
         u'SQLServer:Databases',
         u'log_file(s)_used_size_(kb)',
         u'ReviewInSight',
         u'642']]


discovery = {'': [],
             'cache_hits': [],
             'file_sizes': [(u'SQLServer ReviewInSight', {})],
             'locks': [],
             'locks_per_batch': [],
             'pageactivity': [],
             'sqlstats': [],
             'transactions': []}


checks = {'file_sizes': [(u'SQLServer ReviewInSight',
                          {'log_files_used': (90.0, 95.0)},
                          [(0,
                            'Data files: 4.06 MB',
                            [('data_files', 4259840.0, None, None, None, None)]),
                           (0,
                            'Log files total: 2.05 MB',
                            [('log_files', 2154496.0, None, None, None, None)]),
                           (0,
                            'Log files used: 642 kB, 30.51%',
                            [('log_files_used', 657408.0, 90.0, 95.0, None, None)])])]}
