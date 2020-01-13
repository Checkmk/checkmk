# -*- encoding: utf-8
# yapf: disable


checkname = 'fortigate_memory_base'


info = [
    [u'19', u'1887424'],
]


discovery = {
    '': [(None, 'fortigate_memory_base_default_levels')],
}


checks = {
    '': [
        (None, (70, 80), [
            (0, 'Used: 19.0% - 350.21 MB of 1.80 GB', [
                ('mem_used', 367217213.44, 1352905523.1999998, 1546177740.8000002, 0, 1932722176),
            ]),
        ]),
        (None, {"levels": (15., 85.)}, [
            (1, 'Used: 19.0% - 350.21 MB of 1.80 GB (warn/crit at 15.0%/85.0% used)', [
                ('mem_used', 367217213.44, 289908326.4, 1642813849.6, 0, 1932722176)
            ]),
        ]),
        (None, {"levels": (-85., -15.)}, [
            (1, 'Used: 19.0% - 350.21 MB of 1.80 GB (warn/crit below 85.0%/15.0% free)', [
                ('mem_used', 367217213.44, 289908326.4000001, 1642813849.6, 0, 1932722176),
            ]),
        ]),
        (None, {"levels": (367217200, 1565504900)}, [
            (1, 'Used: 19.0% - 350.21 MB of 1.80 GB (warn/crit at 350.21 MB/1.46 GB used)', [
                ('mem_used', 367217213.44, 367217200.0, 1565504900.0, 0, 1932722176),
            ]),
        ]),
        (None, {"levels": (-1717986918, -1024**2)}, [
            (1, 'Used: 19.0% - 350.21 MB of 1.80 GB (warn/crit below 1.60 GB/1.00 MB free)', [
                ('mem_used', 367217213.44, 214735258.0, 1931673600.0, 0, 1932722176),
            ]),
        ]),
    ],
}
