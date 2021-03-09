# yapf: disable
checkname = 'cisco_mem'

info = [['Processor', '27086628', '46835412', '29817596'],
        ['I/O', '12409052', '2271012', '2086880'], ['Driver text', '40', '1048536', '1048532']]

discovery = {'': [('I/O', {}), ('Processor', {})]}

checks = {
    '': [('I/O', {
        'levels': (80.0, 90.0)
    }, [(1, '84.5% (11.83 MB) of 14 MB used (warning at 80%)', [('mem_used', 84.52995845249721,
                                                                    80.0, 90.0, 0, 100)])]),
         ('Processor', {
             'levels': (80.0, 90.0)
         }, [(0, '36.6% (25.83 MB) of 70.5 MB used', [('mem_used', 36.64215435612978, 80.0, 90.0,
                                                        0, 100)])])]
}
