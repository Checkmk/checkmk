# -*- encoding: utf-8
# yapf: disable


checkname = u'mssql_instance'


info = [[u'MSSQL_MSSQLSERVER', u'config', u'10.50.6000.34', u'Standard Edition', u''],
        [u'MSSQL_ABC', u'config', u'10.50.6000.34', u'Standard Edition', u''],
        [u'MSSQL_ABCDEV', u'config', u'10.50.6000.34', u'Standard Edition', u''],
        [u'MSSQL_MSSQLSERVER', u'state', u'1', u''],
        [u'MSSQL_ABC', u'state', u'1', u''],
        [u'MSSQL_ABCDEV',
         u'state',
         u'0',
         u'[DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.'],
        [u'Hier kommt eine laaaangre Fehlermeldung'],
        [u'die sich ueber                mehrere             Zeilen ersteckt']]


discovery = {'': [(u'ABC', {}), (u'ABCDEV', {}), (u'MSSQLSERVER', {})]}


checks = {'': [(u'ABC', {}, [(0, u'Version: 10.50.6000.34 - Standard Edition', [])]),
               (u'ABCDEV',
                {},
                [(2,
                  u'Failed to connect to database ([DBNETLIB][ConnectionOpen (Connect()).]SQL Server existiert nicht oder Zugriff verweigert.)',
                  []),
                 (0, u'Version: 10.50.6000.34 - Standard Edition', [])]),
               (u'MSSQLSERVER',
                {},
                [(0, u'Version: 10.50.6000.34 - Standard Edition', [])])]}
