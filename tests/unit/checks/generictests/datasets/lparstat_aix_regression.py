checkname = 'lparstat_aix'

info = [['0.2', '1.2', '0.2', '98.6', '0.02', '9.3', '0.1', '519', '0', '101', '0.00']]

discovery = {
    '': [(None, 'lparstat_default_levels')],
    'cpu_util': [(None, 'kernel_util_default_levels')]
}

checks = {
    '': [(None, None,
          [(0, 'Physc: 0.02, Entc: 9.3%, Lbusy: 0.1, App: 519, Vcsw: 0, Phint: 101, Nsp: 0.00%',
            [('physc', 0.02, None, None, None, None), ('entc', 9.3, None, None, None, None),
             ('lbusy', 0.1, None, None, None, None), ('app', 519.0, None, None, None, None),
             ('vcsw', 0.0, None, None, None, None), ('phint', 101.0, None, None, None, None),
             ('nsp', 0.0, None, None, None, None)])])],
    'cpu_util': [
        (None, None, [(0, 'user: 0.2%, system: 1.2%, wait: 0.2%',
                            [('user', 0.2, None, None, None, None),
                             ('system', 1.2, None, None, None, None),
                             ('wait', 0.2, None, None, None, None)])]),
        (None, (0.1, 0.3), [(1, 'user: 0.2%, system: 1.2%, wait: 0.2%',
                             [('user', 0.2, None, None, None, None),
                              ('system', 1.2, None, None, None, None),
                              ('wait', 0.2, None, None, None, None)])]),
        (None, {
            'util': (0.5, 1.3)
        }, [(2, 'user: 0.2%, system: 1.2%, wait: 0.2%', [('user', 0.2, None, None, None, None),
                                                         ('system', 1.2, None, None, None, None),
                                                         ('wait', 0.2, None, None, None, None)])]),
    ]
}
