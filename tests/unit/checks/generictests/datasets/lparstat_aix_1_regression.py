

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


discovery = {'': [(None, {})],
             'cpu_util': [(None, {})]}


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
            (0, 'user: 0.20%', [('user', 0.2)]),
            (0, 'system: 0.40%', [('system', 0.4)]),
            (0, 'wait: 0.00%', [('wait', 0.0)]),
            (0, 'total cpu: 0.60%', [('util', 0.6000000000000001, None, None, 0, None)]),
        ]),
    ],
}
