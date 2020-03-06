# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'emc_ecs_mem'

info = [
    [
        u'swap', u'8388604', u'604', u'64313712', u'3715272', u'876', u'16000',
        u'3213064', u'51260', u'15342316', u'1', u'some error message'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'levels': (150.0, 200.0)
            }, [
                (1, u'some error message', []),
                (
                    0, 'Total (RAM + Swap): 89.19% - 54.70 GB of 61.33 GB RAM',
                    [
                        ('swap_used', 8589312000, None, None, 0, 8589930496),
                        ('mem_used', 50145812480, None, None, 0, 65857241088),
                        (
                            'mem_used_percent', 76.14320255686688, None, None,
                            0, 100.0
                        ),
                        (
                            'mem_lnx_total_used', 58735124480, 98785861632.0,
                            131714482176.0, 0, 74447171584
                        )
                    ]
                ), (0, 'RAM: 76.14% - 46.70 GB of 61.33 GB', []),
                (0, 'Swap: 99.99% - 8.00 GB of 8.00 GB', []),
                (
                    2, '',
                    [('swap_used', 8388000, 8372604.0, 8372604.0, None, None)]
                ),
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
