# -*- encoding: utf-8
# yapf: disable
checkname = 'emc_ecs_mem'

info = [
    [
        u'swap', u'8388604', u'8388604', u'64313712', u'3715272', u'12103876',
        u'16000', u'3213064', u'51260', u'15342316', u'0', u''
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (
                    0,
                    '35.16 GB used (this is 57.3% of 61.33 GB RAM + 8.00 GB SWAP)',
                    [
                        ('ramused', 36003.4375, None, None, 0, 62806.359375),
                        ('swapused', 0.0, None, None, 0, 8191.99609375),
                        (
                            'memused', 36003.4375, 94209.5390625, 125612.71875, 0,
                            70998.35546875
                        )
                    ]
                ),
                (0, '', [('swap_used', 0, 8372604.0, 8372604.0, None, None)]),
                (
                    0, '', [
                        ('mem_lnx_cached', 15342316, None, None, None, None),
                        ('mem_lnx_buffers', 51260, None, None, None, None),
                        ('mem_lnx_shmem', 3213064, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
