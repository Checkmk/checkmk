# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'solaris_mem'

info = [
    [
        u'Memory:', u'128G', u'phys', u'mem,', u'42G', u'free', u'mem,',
        u'19G', u'total', u'swap,', u'19G', u'free', u'swap'
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
                    'Total (RAM + Swap): 67.19% - 86.00 GB of 128.00 GB RAM', [
                        ('swap_used', 0, None, None, 0, 20401094656),
                        ('mem_used', 92341796864, None, None, 0, 137438953472),
                        ('mem_used_percent', 67.1875, None, None, 0, 100.0),
                        (
                            'mem_lnx_total_used', 92341796864, 206158430208.0,
                            274877906944.0, 0, 157840048128
                        )
                    ]
                ), (0, 'RAM: 67.19% - 86.00 GB of 128.00 GB', []),
                (0, 'Swap: 0% - 0.00 B of 19.00 GB', [])
            ]
        )
    ]
}
