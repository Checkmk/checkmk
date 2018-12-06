

checkname = 'filestats'


info = [
    ['{"ref_time": 1544177476.487188}'],
    ['[[[count_only ok subsection]]]'],
    ['{"count": 23}'],
    ['[[[count_only broken subsection]]]'],
    ['{"foobar": 42}'],
    ['[[[count_only complete mess]]]'],
    ['{"fooba2adrs: gh'],
    ['[[[count_only empty subsection]]]'],
    ['{}'],
]


discovery = {'': [],
             'count_only': [('broken subsection', {}),
                            ('complete mess', {}),
                            ('empty subsection', {}),
                            ('ok subsection', {})]}


checks = {'count_only': [('broken subsection', 'default', []),
                         ('complete mess', 'default', []),
                         ('empty subsection', 'default', []),
                         ('ok subsection', 'default',
                          [(0, 'Files in total: 23',
                            [('filestats_count', 23, None, None, None, None)])])]}
