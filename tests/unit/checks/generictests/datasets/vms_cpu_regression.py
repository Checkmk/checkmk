checkname = 'vms_cpu'

info = [['1', '99.17', '0.54', '0.18', '0.00']]

discovery = {'': [(None, 'vms_cpu_default_levels')]}

checks = {
    '': [
        (None, None, [(0, 'user: 0.5%, system: 0.1%, wait: 0.2%',
                       [('user', 0.54, None, None, None, None),
                        ('system', 0.10999999999999827, None, None, None, None),
                        ('wait', 0.18, 0, 0, None, None)])]),
        (None, (0.1, 0.5), [(1, 'user: 0.5%, system: 0.1%, wait: 0.2%',
                             [('user', 0.54, None, None, None, None),
                              ('system', 0.10999999999999827, None, None, None, None),
                              ('wait', 0.18, 0.1, 0.5, None, None)])]),
    ]
}
