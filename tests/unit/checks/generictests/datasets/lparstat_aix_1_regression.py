

checkname = 'lparstat_aix'


info = [
    ['System Config line is currently not used'],
    [u'%user', u'%sys', u'%wait', u'%idle', u'physc', u'%entc', u'lbusy',
     u'vcsw', u'phint', u'%nsp', u'%utcyc'],
    [u'#', u'-----', u'-----', u'------', u'------', u'-----', u'-----',
     u'------', u'-----', u'-----', u'-----', u'------'],
    [u'0.2', u'0.4', u'0.0', u'99.3', u'0.02', u'1.7', u'0.0', u'215',
     u'3', u'101', u'0.64'],
]


discovery = {'': [(None, 'lparstat_default_levels')],
             'cpu_util': [(None, 'kernel_util_default_levels')]}


checks = {
    '': [
        (None, (5, 10), [
            (0, u'Physc: 0.02', [(u'physc', 0.02, None, None, None, None)]),
            (0, u'Entc: 1.7%', [(u'entc', 1.7, None, None, None, None)]),
            (0, u'Lbusy: 0.0', [(u'lbusy', 0.0, None, None, None, None)]),
            (0, u'Vcsw: 215.0', [(u'vcsw', 215.0, None, None, None, None)]),
            (0, u'Phint: 3.0', [(u'phint', 3.0, None, None, None, None)]),
            (0, u'Nsp: 101.0%', [(u'nsp', 101.0, None, None, None, None)]),
            (0, u'Utcyc: 0.64%', [(u'utcyc', 0.64, None, None, None, None)]),
        ]),
    ],
    'cpu_util': [
        (None, None, [
            (0, 'user: 0.2%, system: 0.4%, wait: 0.0%', [
                ('user', 0.2, None, None, None, None),
                ('system', 0.4, None, None, None, None),
                ('wait', 0.0, None, None, None, None),
            ]),
        ]),
    ],
}
