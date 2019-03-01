# yapf: disable
checkname = 'lparstat_aix'

info = [
    [
        u'System', u'configuration:', u'type=Shared', u'mode=Uncapped', u'smt=4', u'lcpu=8',
        u'mem=16384MB', u'psize=4', u'ent=1.00'
    ],
    [
        u'%user', u'%sys', u'%wait', u'%idle', u'physc', u'%entc', u'lbusy', u'app', u'vcsw',
        u'phint', u'%nsp'
    ],
    [u'this line is ignored'],
    ['0.2', '1.2', '0.2', '98.6', '0.02', '9.3', '0.1', '519', '0', '101', '0.00'],
]

discovery = {'': [(None, {})], 'cpu_util': [(None, {})]}

checks = {
    '': [(None, None, [
        (0, 'Physc: 0.02', [('physc', 0.02, None, None, None, None)]),
        (0, 'Entc: 9.3%', [('entc', 9.3, None, None, None, None)]),
        (0, 'Lbusy: 0.1', [('lbusy', 0.1, None, None, None, None)]),
        (0, 'App: 519.0', [('app', 519.0, None, None, None, None)]),
        (0, 'Vcsw: 0.0', [('vcsw', 0.0, None, None, None, None)]),
        (0, 'Phint: 101.0', [('phint', 101.0, None, None, None, None)]),
        (0, 'Nsp: 0.0%', [('nsp', 0.0, None, None, None, None)]),
    ]),],
    'cpu_util': [
        (None, None, [
            (0, 'User: 0.2%', [('user', 0.2)]),
            (0, 'System: 1.2%', [('system', 1.2)]),
            (0, 'Wait: 0.2%', [('wait', 0.2)]),
            (0, 'Total CPU: 1.6%', [('util', 1.5999999999999999, None, None, 0, None)]),
            (0, '100% corresponding to entitled processing capacity: 1.00 CPUs',
             [('cpu_entitlement', 1.0)]),
            (0, "", [('cpu_entitlement_util', 0.016)]),
        ]),
        (None, (0.1, 0.3), [
            (0, 'User: 0.2%', [('user', 0.2)]),
            (0, 'System: 1.2%', [('system', 1.2)]),
            (1, 'Wait: 0.2% (warn/crit at 0.1%/0.3%)', [('wait', 0.2, 0.1, 0.3)]),
            (0, 'Total CPU: 1.6%', [('util', 1.5999999999999999, None, None, 0, None)]),
            (0, '100% corresponding to entitled processing capacity: 1.00 CPUs',
             [('cpu_entitlement', 1.0)]),
            (0, "", [('cpu_entitlement_util', 0.016)]),
        ]),
        (None, {
            'util': (0.5, 1.3)
        }, [
            (0, 'User: 0.2%', [('user', 0.2)]),
            (0, 'System: 1.2%', [('system', 1.2)]),
            (0, 'Wait: 0.2%', [('wait', 0.2)]),
            (2, 'Total CPU: 1.6% (warn/crit at 0.5%/1.3%)', [('util', 1.5999999999999999, 0.5, 1.3,
                                                              0, None)]),
            (0, '100% corresponding to entitled processing capacity: 1.00 CPUs',
             [('cpu_entitlement', 1.0)]),
            (0, "", [('cpu_entitlement_util', 0.016)]),
        ]),
    ]
}
