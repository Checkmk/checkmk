#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'zfsget'

info = [
    [u'DataStorage', u'name', u'DataStorage', u'-'],
    [u'DataStorage', u'quota', u'0', u'default'],
    [u'DataStorage', u'used', u'7560117312', u'-'],
    [u'DataStorage', u'available', u'3849844262352', u'-'],
    [u'DataStorage', u'mountpoint', u'/mnt/DataStorage', u'default'],
    [u'DataStorage', u'type', u'filesystem', u'-'],
    [u'DataStorage/ ISO-File ', u'name', u'DataStorage/ ISO-File ', u'-'],
    [u'DataStorage/ ISO-File ', u'quota', u'0', u'default'],
    [u'DataStorage/ ISO-File ', u'used', u'180048', u'-'],
    [u'DataStorage/ ISO-File ', u'available', u'3849844262352', u'-'],
    [
        u'DataStorage/ ISO-File ', u'mountpoint',
        u'/mnt/DataStorage/ ISO-File ', u'default'
    ], [u'DataStorage/ ISO-File ', u'type', u'filesystem', u'-'],
    [u'DataStorage/Server1a', u'name', u'DataStorage/Server1a', u'-'],
    [u'DataStorage/Server1a', u'quota', u'0', u'default'],
    [u'DataStorage/Server1a', u'used', u'7558161336', u'-'],
    [u'DataStorage/Server1a', u'available', u'3849844262352', u'-'],
    [
        u'DataStorage/Server1a', u'mountpoint', u'/mnt/DataStorage/Server1a',
        u'default'
    ], [u'DataStorage/Server1a', u'type', u'filesystem', u'-'],
    [u'freenas-boot', u'name', u'freenas-boot', u'-'],
    [u'freenas-boot', u'quota', u'0', u'default'],
    [u'freenas-boot', u'used', u'800454656', u'-'],
    [u'freenas-boot', u'available', u'28844803072', u'-'],
    [u'freenas-boot', u'mountpoint', u'none', u'local'],
    [u'freenas-boot', u'type', u'filesystem', u'-'],
    [u'freenas-boot/ROOT', u'name', u'freenas-boot/ROOT', u'-'],
    [u'freenas-boot/ROOT', u'quota', u'0', u'default'],
    [u'freenas-boot/ROOT', u'used', u'799748608', u'-'],
    [u'freenas-boot/ROOT', u'available', u'28844803072', u'-'],
    [
        u'freenas-boot/ROOT', u'mountpoint', u'none',
        u'inherited from freenas-boot'
    ], [u'freenas-boot/ROOT', u'type', u'filesystem', u'-'],
    [
        u'freenas-boot/ROOT/Initial-Install', u'name',
        u'freenas-boot/ROOT/Initial-Install', u'-'
    ], [u'freenas-boot/ROOT/Initial-Install', u'quota', u'0', u'default'],
    [u'freenas-boot/ROOT/Initial-Install', u'used', u'1024', u'-'],
    [u'freenas-boot/ROOT/Initial-Install', u'available', u'28844803072', u'-'],
    [u'freenas-boot/ROOT/Initial-Install', u'mountpoint', u'legacy', u'local'],
    [u'freenas-boot/ROOT/Initial-Install', u'type', u'filesystem', u'-'],
    [
        u'freenas-boot/ROOT/default', u'name', u'freenas-boot/ROOT/default',
        u'-'
    ], [u'freenas-boot/ROOT/default', u'quota', u'0', u'default'],
    [u'freenas-boot/ROOT/default', u'used', u'799717888', u'-'],
    [u'freenas-boot/ROOT/default', u'available', u'28844803072', u'-'],
    [u'freenas-boot/ROOT/default', u'mountpoint', u'legacy', u'local'],
    [u'freenas-boot/ROOT/default', u'type', u'filesystem', u'-'],
    [u'test2', u'name', u'test2', u'-'],
    [u'test2', u'quota', u'0', u'default'],
    [u'test2', u'used', u'9741332480', u'-'],
    [u'test2', u'available', u'468744720384', u'-'],
    [u'test2', u'mountpoint', u'/mnt/test2', u'default'],
    [u'test2', u'type', u'filesystem', u'-'],
    [u'test2/ISO-File', u'name', u'test2/ISO-File', u'-'],
    [u'test2/ISO-File', u'quota', u'0', u'default'],
    [u'test2/ISO-File', u'used', u'2060898304', u'-'],
    [u'test2/ISO-File', u'available', u'468744720384', u'-'],
    [u'test2/ISO-File', u'mountpoint', u'/mnt/test2/ISO-File', u'default'],
    [u'test2/ISO-File', u'type', u'filesystem', u'-'],
    [u'test2/Server1', u'name', u'test2/Server1', u'-'],
    [u'test2/Server1', u'quota', u'0', u'default'],
    [u'test2/Server1', u'used', u'7675715584', u'-'],
    [u'test2/Server1', u'available', u'468744720384', u'-'],
    [u'test2/Server1', u'mountpoint', u'/mnt/test2/Server1', u'default'],
    [u'test2/Server1', u'type', u'filesystem', u'-'],
    [u'test2/iocage', u'name', u'test2/iocage', u'-'],
    [u'test2/iocage', u'quota', u'0', u'default'],
    [u'test2/iocage', u'used', u'647168', u'-'],
    [u'test2/iocage', u'available', u'468744720384', u'-'],
    [u'test2/iocage', u'mountpoint', u'/mnt/test2/iocage', u'default'],
    [u'test2/iocage', u'type', u'filesystem', u'-'],
    [u'test2/iocage/download', u'name', u'test2/iocage/download', u'-'],
    [u'test2/iocage/download', u'quota', u'0', u'default'],
    [u'test2/iocage/download', u'used', u'90112', u'-'],
    [u'test2/iocage/download', u'available', u'468744720384', u'-'],
    [
        u'test2/iocage/download', u'mountpoint', u'/mnt/test2/iocage/download',
        u'default'
    ], [u'test2/iocage/download', u'type', u'filesystem', u'-'],
    [u'test2/iocage/images', u'name', u'test2/iocage/images', u'-'],
    [u'test2/iocage/images', u'quota', u'0', u'default'],
    [u'test2/iocage/images', u'used', u'90112', u'-'],
    [u'test2/iocage/images', u'available', u'468744720384', u'-'],
    [
        u'test2/iocage/images', u'mountpoint', u'/mnt/test2/iocage/images',
        u'default'
    ], [u'test2/iocage/images', u'type', u'filesystem', u'-'],
    [u'test2/iocage/jails', u'name', u'test2/iocage/jails', u'-'],
    [u'test2/iocage/jails', u'quota', u'0', u'default'],
    [u'test2/iocage/jails', u'used', u'90112', u'-'],
    [u'test2/iocage/jails', u'available', u'468744720384', u'-'],
    [
        u'test2/iocage/jails', u'mountpoint', u'/mnt/test2/iocage/jails',
        u'default'
    ], [u'test2/iocage/jails', u'type', u'filesystem', u'-'],
    [u'test2/iocage/log', u'name', u'test2/iocage/log', u'-'],
    [u'test2/iocage/log', u'quota', u'0', u'default'],
    [u'test2/iocage/log', u'used', u'90112', u'-'],
    [u'test2/iocage/log', u'available', u'468744720384', u'-'],
    [u'test2/iocage/log', u'mountpoint', u'/mnt/test2/iocage/log', u'default'],
    [u'test2/iocage/log', u'type', u'filesystem', u'-'],
    [u'test2/iocage/releases', u'name', u'test2/iocage/releases', u'-'],
    [u'test2/iocage/releases', u'quota', u'0', u'default'],
    [u'test2/iocage/releases', u'used', u'90112', u'-'],
    [u'test2/iocage/releases', u'available', u'468744720384', u'-'],
    [
        u'test2/iocage/releases', u'mountpoint', u'/mnt/test2/iocage/releases',
        u'default'
    ], [u'test2/iocage/releases', u'type', u'filesystem', u'-'],
    [u'test2/iocage/templates', u'name', u'test2/iocage/templates', u'-'],
    [u'test2/iocage/templates', u'quota', u'0', u'default'],
    [u'test2/iocage/templates', u'used', u'90112', u'-'],
    [u'test2/iocage/templates', u'available', u'468744720384', u'-'],
    [
        u'test2/iocage/templates', u'mountpoint',
        u'/mnt/test2/iocage/templates', u'default'
    ], [u'test2/iocage/templates', u'type', u'filesystem', u'-'], [u'[df]'],
    [u'freenas-boot/ROOT/default    28942113  773360   28168753     3%    /'],
    [
        u'test2                       457758604      88  457758516     0%    /mnt/test2'
    ],
    [
        u'test2/ISO-File              459771112 2012596  457758516     0%    /mnt/test2/ISO-File'
    ],
    [
        u'test2/Server1               465254332 7495816  457758516     2%    /mnt/test2/Server1'
    ],
    [
        u'test2/iocage                457758620     104  457758516     0%    /mnt/test2/iocage'
    ],
    [
        u'test2/iocage/download       457758604      88  457758516     0%    /mnt/test2/iocage/download'
    ],
    [
        u'test2/iocage/images         457758604      88  457758516     0%    /mnt/test2/iocage/images'
    ],
    [
        u'test2/iocage/jails          457758604      88  457758516     0%    /mnt/test2/iocage/jails'
    ],
    [
        u'test2/iocage/log            457758604      88  457758516     0%    /mnt/test2/iocage/log'
    ],
    [
        u'test2/iocage/releases       457758604      88  457758516     0%    /mnt/test2/iocage/releases'
    ],
    [
        u'test2/iocage/templates      457758604      88  457758516     0%    /mnt/test2/iocage/templates'
    ],
    [
        u'DataStorage                3759613713     176 3759613537     0%    /mnt/DataStorage'
    ],
    [
        u'DataStorage/ ISO-File      3759613713     176 3759613537     0%    /mnt/DataStorage/ ISO-File'
    ],
    [
        u'DataStorage/Server1a       3766994554 7381017 3759613537     0%    /mnt/DataStorage/Server1a'
    ]
]

discovery = {
    '': [
        (u'/', {}), (u'/mnt/DataStorage', {}),
        (u'/mnt/DataStorage/ ISO-File', {}),
        (u'/mnt/DataStorage/Server1a', {}), (u'/mnt/test2', {}),
        (u'/mnt/test2/ISO-File', {}), (u'/mnt/test2/Server1', {}),
        (u'/mnt/test2/iocage', {}), (u'/mnt/test2/iocage/download', {}),
        (u'/mnt/test2/iocage/images', {}), (u'/mnt/test2/iocage/jails', {}),
        (u'/mnt/test2/iocage/log', {}), (u'/mnt/test2/iocage/releases', {}),
        (u'/mnt/test2/iocage/templates', {})
    ]
}

checks = {
    '': [
        (
            u'/', {
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
                    0, '2.67% used (755.23 MB of 27.60 GB)', [
                        (
                            u'/', 755.234375, 22611.02578125,
                            25437.40400390625, 0, 28263.7822265625
                        ),
                        ('fs_size', 28263.7822265625, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/DataStorage', {
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
                    0, '0.2% used (7.04 GB of 3.51 TB)', [
                        (
                            u'/mnt/DataStorage', 7209.889709472656,
                            2942965.987902832, 3310836.736390686, 0,
                            3678707.48487854
                        ),
                        ('fs_size', 3678707.48487854, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/DataStorage/ ISO-File', {
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
                    0, '0.000005% used (175.83 kB of 3.50 TB)', [
                        (
                            u'/mnt/DataStorage/_ISO-File', 0.1717071533203125,
                            2937198.2135009766, 3304347.9901885986, 0,
                            3671497.7668762207
                        ),
                        (
                            'fs_size', 3671497.7668762207, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            u'/mnt/DataStorage/Server1a', {
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
                    0, '0.2% used (7.04 GB of 3.51 TB)', [
                        (
                            u'/mnt/DataStorage/Server1a', 7208.024345397949,
                            2942964.495611572, 3310835.057563019, 0,
                            3678705.6195144653
                        ),
                        (
                            'fs_size', 3678705.6195144653, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2', {
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
                    0, '2.04% used (9.07 of 445.62 GB)', [
                        (
                            u'/mnt/test2', 9290.05859375, 365055.8875,
                            410687.8734375, 0, 456319.859375
                        ), ('fs_size', 456319.859375, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/ISO-File', {
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
                    0, '0.44% used (1.92 of 438.47 GB)', [
                        (
                            u'/mnt/test2/ISO-File', 1965.42578125,
                            359196.18125, 404095.70390625, 0, 448995.2265625
                        ), ('fs_size', 448995.2265625, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/Server1', {
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
                    0, '1.61% used (7.15 of 443.70 GB)', [
                        (
                            u'/mnt/test2/Server1', 7320.1328125, 363479.946875,
                            408914.940234375, 0, 454349.93359375
                        ),
                        ('fs_size', 454349.93359375, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage', {
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
                    0, '0.0001% used (632.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage', 0.6171875, 357624.334375,
                            402327.376171875, 0, 447030.41796875
                        ),
                        ('fs_size', 447030.41796875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/download', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/download', 0.0859375,
                            357623.909375, 402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/images', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/images', 0.0859375,
                            357623.909375, 402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/jails', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/jails', 0.0859375,
                            357623.909375, 402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/log', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/log', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/releases', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/releases', 0.0859375,
                            357623.909375, 402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'/mnt/test2/iocage/templates', {
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
                    0, '0.00002% used (88.00 kB of 436.55 GB)', [
                        (
                            u'/mnt/test2/iocage/templates', 0.0859375,
                            357623.909375, 402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
