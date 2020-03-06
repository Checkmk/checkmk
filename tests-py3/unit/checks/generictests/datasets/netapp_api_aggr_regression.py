# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'netapp_api_aggr'

info = [
    [
        'aggregation aggr0_sas_mirror', 'size-available 30436616933376',
        'size-total 80672545427456'
    ],
    [
        'aggregation aggr1_sata', 'size-available 32045210935296',
        'size-total 128001905786880'
    ]
]

discovery = {'': [('aggr0_sas_mirror', {}), ('aggr1_sata', {})]}

checks = {
    '': [
        (
            'aggr0_sas_mirror', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    0, '62.27% used (45.69 of 73.37 TB)', [
                        (
                            'aggr0_sas_mirror', 47908714.765625,
                            61548267.690625, 69241801.15195313, 0,
                            76935334.61328125
                        ),
                        ('fs_size', 76935334.61328125, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'aggr1_sata', {
                'trend_range': 24,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'magic_normsize': 20,
                'show_inodes': 'onlow',
                'levels': (80.0, 90.0),
                'show_reserved': False,
                'levels_low': (50.0, 60.0),
                'trend_perfdata': True
            }, [
                (
                    0, '74.97% used (87.27 of 116.42 TB)', [
                        (
                            'aggr1_sata', 91511435.3671875, 97657704.0,
                            109864917.0, 0, 122072130.0
                        ), ('fs_size', 122072130.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
