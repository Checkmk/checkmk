# -*- encoding: utf-8
# yapf: disable
checkname = 'haproxy'

info = [
    [
        u'https_t3test.tgic.de', u'FRONTEND', u'', u'', u'0', u'0', u'2000',
        u'0', u'0', u'0', u'0', u'0', u'0', u'', u'', u'', u'', u'OPEN', u'',
        u'', u'', u'', u'', u'', u'', u'', u'1', u'2', u'0', u'', u'', u'',
        u'0', u'0', u'0', u'0', u'', u'', u'', u'0', u'0', u'0', u'0', u'0',
        u'0', u'', u'0', u'0', u'0', u'', u'', u'0', u'0', u'0', u'0', u'',
        u'', u'', u'', u'', u'', u'', u''
    ],
    [
        u'https_t3test.tgic.de', u'BACKEND', u'0', u'0', u'0', u'0', u'200',
        u'0', u'0', u'0', u'0', u'0', u'', u'0', u'0', u'0', u'0', u'UP', u'0',
        u'0', u'0', u'', u'0', u'363417', u'0', u'', u'1', u'2', u'0', u'',
        u'0', u'', u'1', u'0', u'', u'0', u'', u'', u'', u'0', u'0', u'0',
        u'0', u'0', u'0', u'', u'', u'', u'', u'0', u'0', u'0', u'0', u'0',
        u'0', u'-1', u'', u'', u'0', u'0', u'0', u'0', u''
    ],
    [
        u't3test', u't3test', u'0', u'0', u'0', u'0', u'', u'0', u'0', u'0',
        u'', u'0', u'', u'0', u'0', u'0', u'0', u'UP', u'1', u'1', u'0', u'0',
        u'0', u'363417', u'0', u'', u'1', u'3', u'1', u'', u'0', u'', u'2',
        u'0', u'', u'0', u'L4OK', u'', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'', u'', u'', u'0', u'0', u'', u'', u'', u'', u'-1', u'',
        u'', u'0', u'0', u'0', u'0', u''
    ],
    [
        u'BLABLABFO', u'ELEADC05', u'0', u'0', u'0', u'5', u'', u'841',
        u'483793', u'1386127', u'', u'0', u'', u'0', u'751', u'0', u'0', u'UP',
        u'1', u'1', u'0', u'0', u'0', u'38624', u'0', u'', u'1', u'5', u'2',
        u'', u'841', u'', u'2', u'0', u'', u'4', u'L4OK', u'', u'0', u'', u'',
        u'', u'', u'', u'', u'0', u'', u'', u'', u'90', u'751', u'', u'', u'',
        u'', u'169', u'', u'', u'0', u'0', u'0', u'3073', u''
    ],
    [
        u'BLABLABLABLA', u'FRONTEND', u'', u'', u'0', u'0', u'2000', u'0',
        u'0', u'0', u'0', u'0', u'0', u'', u'', u'', u'', u'OPEN', u'', u'',
        u'', u'', u'', u'', u'', u'', u'1', u'2', u'0', u'', u'', u'', u'0',
        u'0', u'0', u'0', u'', u'', u'', u'0', u'0', u'0', u'0', u'0', u'0',
        u'', u'0', u'0', u'0', u'', u'', u'0', u'0', u'0', u'0', u'', u'', u'',
        u'', u'', u'', u'', u''
    ],
    [
        u'LDAP', u'IP.IP.IP.IP', u'', u'', u'0', u'32', u'250', u'5892',
        u'3365040', u'9470591', u'0', u'0', u'0', u'', u'', u'', u'', u'OPEN',
        u'', u'', u'', u'', u'', u'', u'', u'', u'1', u'3', u'1', u'', u'',
        u'', u'3', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'',
        u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'',
        u'', u'', u'', u''
    ],
    [
        u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'',
        u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'', u'',
        u'', u'', u'', u''
    ]
]

discovery = {
    '': [],
    'frontend': [(u'BLABLABLABLA', {}), (u'https_t3test.tgic.de', {})],
    'server': [(u'BLABLABFO/ELEADC05', {}), (u't3test/t3test', {})]
}

checks = {
    'frontend': [
        (
            u'BLABLABLABLA', None, [  # handle old params
                (0, u'Status: OPEN', []),
                (
                    0, 'Session Rate: 0.00', [
                        ('session_rate', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'BLABLABLABLA', {}, [
                (0, u'Status: OPEN', []),
                (
                    0, 'Session Rate: 0.00', [
                        ('session_rate', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'https_t3test.tgic.de', {}, [
                (0, u'Status: OPEN', []),
                (
                    0, 'Session Rate: 0.00', [
                        ('session_rate', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'server': [
        (
            u'BLABLABFO/ELEADC05', None, [  # handle old params
                (0, u'Status: UP', []),
                (0, 'Active', []),
                (0, u'Layer Check: L4OK', []),
                (0, 'Up since 10 h', []),
            ]
        ),
        (
            u'BLABLABFO/ELEADC05', {}, [
                (0, u'Status: UP', []),
                (0, 'Active', []),
                (0, u'Layer Check: L4OK', []),
                (0, 'Up since 10 h', []),
            ]
        ),
        (
            u't3test/t3test', {}, [
                (0, u'Status: UP', []),
                (0, 'Active', []),
                (0, u'Layer Check: L4OK', []),
                (0, 'Up since 4.2 d', []),
            ]
        )
    ]
}
