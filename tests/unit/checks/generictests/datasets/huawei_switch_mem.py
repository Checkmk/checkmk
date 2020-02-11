# -*- encoding: utf-8
# yapf: disable
checkname = 'huawei_switch_mem'

info = [
    [
        [u'67108867', u'HUAWEI S6720 Routing Switch'],
        [u'67108869', u'Board slot 0'],
        [u'68157445', u'Board slot 1'],
        [u'68157449', u'MPU Board 1'],
        [u'68173836', u'Card slot 1/1'],
        [u'68190220', u'Card slot 1/2'],
        [u'68239373', u'POWER Card 1/PWR1'],
        [u'68255757', u'POWER Card 1/PWR2'],
        [u'68272141', u'FAN Card 1/FAN1'],
        [u'69206021', u'Board slot 2'],
        [u'69222412', u'Card slot 2/1'],
        [u'69206025', u'MPU Board 2'],
        [u'69206045', u'MPU Board 3'],
        [u'69206055', u'MPU Board 4'],  # Info missing in second array
    ],
    [
        [u'67108867', u'0'],
        [u'67108869', u'0'],
        [u'68157445', u'0'],
        [u'68157449', u'22'],
        [u'68173836', u'0'],
        [u'68190220', u'0'],
        [u'68239373', u'0'],
        [u'68255757', u'0'],
        [u'68272141', u'0'],
        [u'69206021', u'0'],
        [u'69222412', u'0'],
        [u'69206025', u'85'],
        [u'69206045', u'95'],
    ],
]

discovery = {
    '': [
        ('1', {}),
        ('2', {}),
        ('3', {}),
        ('4', {}),
    ]
}

checks = {
    '': [
        (
            '1',
            {
                'levels': (80.0, 90.0)
            },
            [(
                0,
                'Usage: 22.0%',
                [('mem_used_percent', 22.0, 80.0, 90.0, None, None)],
            )],
        ),
        (
            '2',
            {
                'levels': (80.0, 90.0)
            },
            [(
                1,
                'Usage: 85.0% (warn/crit at 80.0%/90.0%)',
                [('mem_used_percent', 85.0, 80.0, 90.0, None, None)],
            )],
        ),
        (
            '3',
            {
                'levels': (80.0, 90.0)
            },
            [(
                2,
                'Usage: 95.0% (warn/crit at 80.0%/90.0%)',
                [('mem_used_percent', 95.0, 80.0, 90.0, None, None)],
            )],
        ),
        (
            '4',
            {
                'levels': (80.0, 90.0)
            },
            [],
        ),
    ]
}
