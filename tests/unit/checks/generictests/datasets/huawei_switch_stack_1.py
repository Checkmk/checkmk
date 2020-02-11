# -*- encoding: utf-8
# yapf: disable
checkname = 'huawei_switch_stack'

info = [
    [[u'1']],
    [
        [u'1', u'1'],
        [u'2', u'3'],
        [u'3', u'2'],
        [u'4', u'2'],
        [u'5', u'4'],
    ],
]

discovery = {
    '': [
        (u'1', {
            'expected_role': 'master'
        }),
        (u'2', {
            'expected_role': 'slave'
        }),
        (u'3', {
            'expected_role': 'standby'
        }),
        (u'4', {
            'expected_role': 'standby'
        }),
        (u'5', {
            'expected_role': 'unknown'
        }),
    ]
}

checks = {
    '': [
        (
            u'1',
            {
                'expected_role': 'master'
            },
            [(0, 'master', [])],
        ),
        (
            u'2',
            {
                'expected_role': 'slave'
            },
            [(0, 'slave', [])],
        ),
        (
            u'3',
            {
                'expected_role': 'standby'
            },
            [(0, 'standby', [])],
        ),
        (
            u'4',
            {
                'expected_role': 'slave'
            },
            [(2, 'Unexpected role: standby (Expected: slave)', [])],
        ),
        (
            u'5',
            {
                'expected_role': 'unknown'
            },
            [(2, 'unknown', [])],
        ),
    ]
}
