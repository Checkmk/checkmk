# yapf: disable


checkname = 'mysql_capacity'


info = [['[[]]'],
        ['information_schema', '147456', '0'],
        ['mysql', '665902', '292'],
        ['performance_schema', '0', '0'],
        ['test', '409255936', '54525952']]


discovery = {
    '': [
        ('mysql:test', {}),
    ],
}


checks = {
    '': [
        (
            'mysql:test',
            {},
            [(0, 'Size: 390.3 MB', [('database_size', 409255936, None, None, None, None)])]
        ),
        (
            'mysql:test',
            (40960, 51200),
            [
                (
                    2,
                    'Size: 390.3 MB (warn/crit at 40 kB/50 kB)',
                    [('database_size', 409255936, 40960, 51200, None, None)]
                )
            ]
        ),
        (
            'mysql:test',
            (40960000000, 51200000000),
            [
                (
                    0,
                    'Size: 390.3 MB',
                    [('database_size', 409255936, 40960000000, 51200000000, None, None)]
                )
            ]
        ),
    ],
}
