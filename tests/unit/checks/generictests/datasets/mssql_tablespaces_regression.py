# yapf: disable

checkname = 'mssql_tablespaces'


info = [
    ['MSSQL_SQLEXPRESS', 'master', '5.25', 'MB', '1.59', 'MB', '2464',
     'KB', '1096', 'KB', '1024', 'KB', '344', 'KB'],
]


discovery = {
    '': [
        ('MSSQL_SQLEXPRESS master', {}),
    ],
}


checks = {
    '': [
        ('MSSQL_SQLEXPRESS master', {}, [
            (0, 'Size: 5.25 MB', [('size', 5505024.0, None, None, None, None)]),
            (0, 'Unallocated space: 1.59 MB, 30.3%', []),
            (0, 'Reserved space: 2.41 MB, 45.8%', []),
            (0, 'Data: 1.07 MB, 20.4%', []),
            (0, 'Indexes: 1.00 MB, 19.0%', []),
            (0, 'Unused: 344.00 kB, 6.4%', []),
        ]),
        ('MSSQL_SQLEXPRESS master', {"size": (3*1024**2, 6*1024**2)}, [
            (1, 'Size: 5.25 MB (warn/crit at 3.00 MB/6.00 MB)', [('size', 5505024.0, 3*1024**2, 6*1024**2, None, None)]),
            (0, 'Unallocated space: 1.59 MB, 30.3%', []),
            (0, 'Reserved space: 2.41 MB, 45.8%', []),
            (0, 'Data: 1.07 MB, 20.4%', []),
            (0, 'Indexes: 1.00 MB, 19.0%', []),
            (0, 'Unused: 344.00 kB, 6.4%', []),
        ]),
    ],
}
