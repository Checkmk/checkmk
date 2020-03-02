# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'df'

info = [
    [u'C:\\', u'NTFS', u'8192620', u'7724268', u'468352', u'95%', u'C:\\'],
    [
        u'New_Volume', u'NTFS', u'10240796', u'186256', u'10054540', u'2%',
        u'E:\\'
    ],
    [
        u'New_Volume', u'NTFS', u'124929596', u'50840432', u'74089164', u'41%',
        u'F:\\'
    ]
]

discovery = {'': [(u'C:/', {"include_volume_name": False}), (u'E:/', {"include_volume_name": False}), (u'F:/', {"include_volume_name": False})]}

checks = {
    '': [
        (
            u'C:/', {
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
                    2,
                    '94.28% used (7.37 of 7.81 GB), (warn/crit at 80.0%/90.0%)',
                    [
                        (
                            u'C:/', 7543.23046875, 6400.484375, 7200.544921875,
                            0, 8000.60546875
                        ), ('fs_size', 8000.60546875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'New_Volume E:/', {
                'show_inodes': 'onlow',
                'inodes_levels': (10.0, 5.0),
                'trend_range': 24,
                'show_reserved': False,
                'show_levels': 'onmagic',
                'trend_perfdata': True,
                'levels_low': (50.0, 60.0),
                'levels': (80.0, 90.0),
                'magic_normsize': 20
            }, [
                (
                    0, '1.82% used (181.89 MB of 9.77 GB)', [
                        (
                            u'E:/', 181.890625, 8000.621875, 9000.699609375, 0,
                            10000.77734375
                        ), ('fs_size', 10000.77734375, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'E:/', {
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
                    0, '1.82% used (181.89 MB of 9.77 GB)', [
                        (
                            u'E:/', 181.890625, 8000.621875, 9000.699609375, 0,
                            10000.77734375
                        ), ('fs_size', 10000.77734375, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'F:/', {
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
                    0, '40.7% used (48.49 of 119.14 GB)', [
                        (
                            u'F:/', 49648.859375, 97601.246875,
                            109801.402734375, 0, 122001.55859375
                        ),
                        ('fs_size', 122001.55859375, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
