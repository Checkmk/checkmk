# pylint: disable=invalid-name

checkname = 'filestats'


info = [
    ["some garbage in the first line (should be ignored)"],
    ["[[[count_only ok subsection]]]"],
    ["{'type': 'summary', 'count': 23}"],
    ["[[[count_only missing count]]]"],
    ["{'type': 'summary', 'foobar': 42}"],
    ["[[[count_only complete mess]]]"],
    ["{'fooba2adrs: gh"],
    ["[[[count_only empty subsection]]]"],
    ["{}"],
]


discovery = {
    '': [
        ('ok subsection', {}),
        ('missing count', {}),
        ('complete mess', {}),
        ('empty subsection', {})
        ]
}


checks = {
    '': [
        ('broken subsection', 'default', []),
        ('complete mess', 'default', []),
        ('empty subsection', 'default', []),
        ('ok subsection', 'default', [
            (0, 'Files in total: 23',
             [('file_count', 23, None, None, None, None)])])
        ]
}
