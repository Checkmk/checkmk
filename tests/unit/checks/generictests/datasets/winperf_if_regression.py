checkname = 'winperf_if'

info = [[u'1457449582.48', u'510'],
        [u'2', u'instances:', u'TEAM:F[o]O_123-BAR', u'TEAM:F[o]O_123-BAR__2'],
        [u'-122', u'235633280233', u'654530712228', u'bulk_count'],
        [u'-110', u'242545296', u'495547559', u'bulk_count'],
        [u'-244', u'104845218', u'401387884', u'bulk_count'],
        [u'-58', u'137700078', u'94159675', u'bulk_count'],
        [u'10', u'10000000000', u'10000000000', u'large_rawcount'],
        [u'-246', u'102711323759', u'558990881384', u'bulk_count'],
        [u'14', u'104671447', u'400620918', u'bulk_count'],
        [u'16', u'173771', u'766966', u'bulk_count'], [u'18', u'0', u'0', u'large_rawcount'],
        [u'20', u'0', u'0', u'large_rawcount'], [u'22', u'0', u'0', u'large_rawcount'],
        [u'-4', u'132921956474', u'95539830844', u'bulk_count'],
        [u'26', u'137690798', u'94151631', u'bulk_count'], [u'28', u'9280', u'8044', u'bulk_count'],
        [u'30', u'0', u'0', u'large_rawcount'], [u'32', u'0', u'0', u'large_rawcount'],
        [u'34', u'0', u'0', u'large_rawcount'], [u'1086', u'0', u'0', u'large_rawcount'],
        [u'1088', u'0', u'0', u'large_rawcount'], [u'1090', u'0', u'0', u'bulk_count'],
        [u'1092', u'0', u'0', u'bulk_count'], [u'1094', u'0', u'0', u'large_rawcount']]

discovery = {
    '': [('1', "{'state': ['1'], 'speed': 10000000000}"),
         ('2', "{'state': ['1'], 'speed': 10000000000}")]
}

checks = {
    '': [('1', {
        'errors': (0.01, 0.1),
        'state': ['1'],
        'speed': 10000000000
    }, [(0, u'[TEAM:F[o]O 123-BAR] (Connected) 10.00 Gbit/s', [])]),
         ('2', {
             'errors': (0.01, 0.1),
             'state': ['1'],
             'speed': 10000000000
         }, [(0, u'[TEAM:F[o]O 123-BAR 2] (Connected) 10.00 Gbit/s', [])])]
}
