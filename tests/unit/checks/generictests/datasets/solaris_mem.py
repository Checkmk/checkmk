# -*- encoding: utf-8
# yapf: disable
checkname = 'solaris_mem'

info = [
    [
        u'Memory:', u'128G', u'phys', u'mem,', u'42G', u'free', u'mem,',
        u'19G', u'total', u'swap,', u'19G', u'free', u'swap'
    ]
]

discovery = {
    '': [
        (None, {}),
    ],
}

checks = {
    '': [
        (None, {'levels': (150.0, 200.0)}, [
            (0, '86.00 GB used (86.00 GB RAM + 0.00 B SWAP, this is 67.2% of 128.00 GB RAM + 19.00 GB SWAP)', [
                ('swapused', 0.0, None, None, 0, 19456.0),
                ('ramused', 88064.0, None, None, 0, 131072.0),
                ('memused', 88064.0, 196608.0, 262144.0, 0, 150528.0),
            ]),
        ]),
    ],
}
