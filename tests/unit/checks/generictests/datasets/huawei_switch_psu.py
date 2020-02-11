# -*- encoding: utf-8
# yapf: disable
checkname = 'huawei_switch_psu'

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
        [u'69206035', u'POWER Card 2/PWR1'],
        [u'69206038', u'POWER Card 2/PWR2'],  # Info missing in the second list
        [u'69206045', u'MPU Board 3'],
        [u'69206048', u'POWER Card 3/PWR1'],
    ],
    [
        [u'67108867', u'3'],
        [u'67108869', u'3'],
        [u'68157445', u'3'],
        [u'68157449', u'3'],
        [u'68173836', u'3'],
        [u'68190220', u'3'],
        [u'68239373', u'3'],
        [u'68255757', u'2'],
        [u'68272141', u'3'],
        [u'69206021', u'3'],
        [u'69222412', u'3'],
        [u'69206025', u'3'],
        [u'69206035', u'7'],
        [u'69206045', u'3'],
        [u'69206048', u'3'],
    ],
]

discovery = {
    '': [
        ('1/1', {}),
        ('1/2', {}),
        ('2/1', {}),
        ('2/2', {}),
        ('3/1', {}),
    ]
}

checks = {
    '': [
        (
            '1/1',
            {},
            [(
                0,
                'State: enabled',
                [],
            )],
        ),
        (
            '1/2',
            {},
            [(
                2,
                'State: disabled',
                [],
            )],
        ),
        (
            '2/1',
            {},
            [(
                2,
                'State: unknown (7)',
                [],
            )],
        ),
        (
            '2/2',
            {},
            [],
        ),
        (
            '3/1',
            {},
            [(
                0,
                'State: enabled',
                [],
            )],
        ),
    ]
}
