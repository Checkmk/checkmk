# -*- encoding: utf-8
# yapf: disable
checkname = 'msoffice_licenses'

info = [
    [u'sx:MYLICENSE1', u'55', u'0', u'55'],
    [u'sx:MYLICENSE2', u'1000000', u'0', u''], [u'sx:MYLICENSE3'],
    [u'sx:MYLICENSE4', u'130', u'0', u'120'],
    [u'sx:MYLICENSE5', u'10000', u'0', u'1'],
    [u'sx:MYLICENSE6', u'6575', u'0', u'6330'],
    [u'sx:MYLICENSE7', u'3800', u'0', u'3756'],
    [u'sx:MYLICENSE8', u'10000', u'0', u'1424'],
    [u'sx:MYLICENSE9', u'10000', u'0', u'4'],
    [u'sx:MYLICENSE10', u'10000', u'0', u'5'],
    [u'sx:MYLICENSE11', u'100', u'0', u'46'],
    [u'sx:MYLICENSE12', u'1000000', u'0', u'194'],
    [u'sx:MYLICENSE12', u'5925', u'0', u'1'],
    [u'sx:MYLICENSE12', u'3600', u'0', u'5'],
    [u'sx:MYLICENSE13', u'10665', u'0', u'10461'],
    [u'sx:MYLICENSE13', u'840', u'0', u'803'],
    [u'sx:MYLICENSE14', u'0', u'0',
     u'2'], [u'sx:MYLICENSE15', u'0', u'0', u'0'],
    [u'sx:MYLICENSE16', u'5', u'1', u'4']
]

discovery = {
    '': [
        (u'sx:MYLICENSE1', {}),
        (u'sx:MYLICENSE10', {}), (u'sx:MYLICENSE11', {}),
        (u'sx:MYLICENSE12', {}), (u'sx:MYLICENSE13', {}),
        (u'sx:MYLICENSE14', {}), (u'sx:MYLICENSE15', {}),
        (u'sx:MYLICENSE16', {}), (u'sx:MYLICENSE4', {}),
        (u'sx:MYLICENSE5', {}), (u'sx:MYLICENSE6', {}), (u'sx:MYLICENSE7', {}),
        (u'sx:MYLICENSE8', {}), (u'sx:MYLICENSE9', {})
    ]
}

checks = {
    '': [
        (
            u'sx:MYLICENSE1', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 55 of 55', [
                        ('licenses', 55, None, None, None, None),
                        ('licenses_total', 55, None, None, None, None)
                    ]
                ),
                (
                    2, 'Usage: 100% (warn/crit at 80.0%/90.0%)', [
                        ('license_percentage', 100.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE10', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 5 of 10000', [
                        ('licenses', 5, None, None, None, None),
                        ('licenses_total', 10000, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 0.05%', [
                        ('license_percentage', 0.05, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE11', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 46 of 100', [
                        ('licenses', 46, None, None, None, None),
                        ('licenses_total', 100, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 46.0%', [
                        ('license_percentage', 46.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE12', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 194 of 1000000', [
                        ('licenses', 194, None, None, None, None),
                        ('licenses_total', 1000000, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 0.02%', [
                        ('license_percentage', 0.0194, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE13', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 10461 of 10665', [
                        ('licenses', 10461, None, None, None, None),
                        ('licenses_total', 10665, None, None, None, None)
                    ]
                ),
                (
                    2, 'Usage: 98.09% (warn/crit at 80.0%/90.0%)', [
                        (
                            'license_percentage', 98.08720112517581, 80.0,
                            90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE14', {
                'usage': (80, 90)
            }, [(0, 'No active licenses', [])]
        ),
        (
            u'sx:MYLICENSE15', {
                'usage': (80, 90)
            }, [(0, 'No active licenses', [])]
        ),
        (
            u'sx:MYLICENSE16', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 4 of 5', [
                        ('licenses', 4, None, None, None, None),
                        ('licenses_total', 5, None, None, None, None)
                    ]
                ),
                (
                    1, 'Usage: 80.0% (warn/crit at 80.0%/90.0%)', [
                        ('license_percentage', 80.0, 80.0, 90.0, 0.0, 100.0)
                    ]
                ), (0, ' Warning units: 1', [])
            ]
        ),
        (
            u'sx:MYLICENSE4', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 120 of 130', [
                        ('licenses', 120, None, None, None, None),
                        ('licenses_total', 130, None, None, None, None)
                    ]
                ),
                (
                    2, 'Usage: 92.31% (warn/crit at 80.0%/90.0%)', [
                        (
                            'license_percentage', 92.3076923076923, 80.0, 90.0,
                            0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE5', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 1 of 10000', [
                        ('licenses', 1, None, None, None, None),
                        ('licenses_total', 10000, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 0.01%', [
                        ('license_percentage', 0.01, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE6', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 6330 of 6575', [
                        ('licenses', 6330, None, None, None, None),
                        ('licenses_total', 6575, None, None, None, None)
                    ]
                ),
                (
                    2, 'Usage: 96.27% (warn/crit at 80.0%/90.0%)', [
                        (
                            'license_percentage', 96.27376425855513, 80.0,
                            90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE7', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 3756 of 3800', [
                        ('licenses', 3756, None, None, None, None),
                        ('licenses_total', 3800, None, None, None, None)
                    ]
                ),
                (
                    2, 'Usage: 98.84% (warn/crit at 80.0%/90.0%)', [
                        (
                            'license_percentage', 98.84210526315789, 80.0,
                            90.0, 0.0, 100.0
                        )
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE8', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 1424 of 10000', [
                        ('licenses', 1424, None, None, None, None),
                        ('licenses_total', 10000, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 14.24%', [
                        ('license_percentage', 14.24, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        ),
        (
            u'sx:MYLICENSE9', {
                'usage': (80, 90)
            }, [
                (
                    0, 'Consumed: 4 of 10000', [
                        ('licenses', 4, None, None, None, None),
                        ('licenses_total', 10000, None, None, None, None)
                    ]
                ),
                (
                    0, 'Usage: 0.04%', [
                        ('license_percentage', 0.04, 80.0, 90.0, 0.0, 100.0)
                    ]
                )
            ]
        )
    ]
}
