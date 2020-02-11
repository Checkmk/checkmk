# -*- encoding: utf-8
# yapf: disable
checkname = 'emc_ecs_mem'

info = [
    [
        u'foobar', u'8388604', u'604', u'64313712', u'3715272', u'876',
        u'16000', u'3213064', u'51260', u'15342316', u'1',
        u'some error message'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (None, { 'levels': (150.0, 200.0) }, [
            (1, u'Error: foobar', []),
            (1, u'some error message', []),
            (0, 'Total (RAM + Swap): 89.19% - 54.70 GB of 61.33 GB RAM', [
                ('swapused', 8191.40625, None, None, 0, 8191.99609375),
                ('ramused', 47822.7734375, None, None, 0, 62806.359375),
                ('memused', 56014.1796875, 94209.5390625, 125612.71875, 0, 70998.35546875),
            ]),
            (0, 'RAM: 76.14% - 46.70 GB of 61.33 GB', []),
            (0, 'Swap: 99.99% - 8.00 GB of 8.00 GB', []),
            (2, '', [
                ('swap_used', 8388000, 8372604.0, 8372604.0, None, None),
            ]),
            (0, '', [
                ('mem_lnx_cached', 15342316, None, None, None, None),
                ('mem_lnx_buffers', 51260, None, None, None, None),
                ('mem_lnx_shmem', 3213064, None, None, None, None),
            ]),
        ]),
    ],
}
