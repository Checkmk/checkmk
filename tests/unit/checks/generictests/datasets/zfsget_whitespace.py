#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'zfsget'

info = [
    ['DataStorage', 'name', 'DataStorage', '-'],
    ['DataStorage', 'quota', '0', 'default'],
    ['DataStorage', 'used', '7560117312', '-'],
    ['DataStorage', 'available', '3849844262352', '-'],
    ['DataStorage', 'mountpoint', '/mnt/DataStorage', 'default'],
    ['DataStorage', 'type', 'filesystem', '-'],
    ['DataStorage/ ISO-File ', 'name', 'DataStorage/ ISO-File ', '-'],
    ['DataStorage/ ISO-File ', 'quota', '0', 'default'],
    ['DataStorage/ ISO-File ', 'used', '180048', '-'],
    ['DataStorage/ ISO-File ', 'available', '3849844262352', '-'],
    [
        'DataStorage/ ISO-File ', 'mountpoint', '/mnt/DataStorage/ ISO-File ',
        'default'
    ], ['DataStorage/ ISO-File ', 'type', 'filesystem', '-'],
    ['DataStorage/Server1a', 'name', 'DataStorage/Server1a', '-'],
    ['DataStorage/Server1a', 'quota', '0', 'default'],
    ['DataStorage/Server1a', 'used', '7558161336', '-'],
    ['DataStorage/Server1a', 'available', '3849844262352', '-'],
    [
        'DataStorage/Server1a', 'mountpoint', '/mnt/DataStorage/Server1a',
        'default'
    ], ['DataStorage/Server1a', 'type', 'filesystem', '-'],
    ['freenas-boot', 'name', 'freenas-boot', '-'],
    ['freenas-boot', 'quota', '0', 'default'],
    ['freenas-boot', 'used', '800454656', '-'],
    ['freenas-boot', 'available', '28844803072', '-'],
    ['freenas-boot', 'mountpoint', 'none', 'local'],
    ['freenas-boot', 'type', 'filesystem', '-'],
    ['freenas-boot/ROOT', 'name', 'freenas-boot/ROOT', '-'],
    ['freenas-boot/ROOT', 'quota', '0', 'default'],
    ['freenas-boot/ROOT', 'used', '799748608', '-'],
    ['freenas-boot/ROOT', 'available', '28844803072', '-'],
    ['freenas-boot/ROOT', 'mountpoint', 'none', 'inherited from freenas-boot'],
    ['freenas-boot/ROOT', 'type', 'filesystem', '-'],
    [
        'freenas-boot/ROOT/Initial-Install', 'name',
        'freenas-boot/ROOT/Initial-Install', '-'
    ], ['freenas-boot/ROOT/Initial-Install', 'quota', '0', 'default'],
    ['freenas-boot/ROOT/Initial-Install', 'used', '1024', '-'],
    ['freenas-boot/ROOT/Initial-Install', 'available', '28844803072', '-'],
    ['freenas-boot/ROOT/Initial-Install', 'mountpoint', 'legacy', 'local'],
    ['freenas-boot/ROOT/Initial-Install', 'type', 'filesystem', '-'],
    ['freenas-boot/ROOT/default', 'name', 'freenas-boot/ROOT/default', '-'],
    ['freenas-boot/ROOT/default', 'quota', '0', 'default'],
    ['freenas-boot/ROOT/default', 'used', '799717888', '-'],
    ['freenas-boot/ROOT/default', 'available', '28844803072', '-'],
    ['freenas-boot/ROOT/default', 'mountpoint', 'legacy', 'local'],
    ['freenas-boot/ROOT/default', 'type', 'filesystem', '-'],
    ['test2', 'name', 'test2', '-'], ['test2', 'quota', '0', 'default'],
    ['test2', 'used', '9741332480', '-'],
    ['test2', 'available', '468744720384', '-'],
    ['test2', 'mountpoint', '/mnt/test2', 'default'],
    ['test2', 'type', 'filesystem', '-'],
    ['test2/ISO-File', 'name', 'test2/ISO-File', '-'],
    ['test2/ISO-File', 'quota', '0', 'default'],
    ['test2/ISO-File', 'used', '2060898304', '-'],
    ['test2/ISO-File', 'available', '468744720384', '-'],
    ['test2/ISO-File', 'mountpoint', '/mnt/test2/ISO-File', 'default'],
    ['test2/ISO-File', 'type', 'filesystem', '-'],
    ['test2/Server1', 'name', 'test2/Server1', '-'],
    ['test2/Server1', 'quota', '0', 'default'],
    ['test2/Server1', 'used', '7675715584', '-'],
    ['test2/Server1', 'available', '468744720384', '-'],
    ['test2/Server1', 'mountpoint', '/mnt/test2/Server1', 'default'],
    ['test2/Server1', 'type', 'filesystem', '-'],
    ['test2/iocage', 'name', 'test2/iocage', '-'],
    ['test2/iocage', 'quota', '0', 'default'],
    ['test2/iocage', 'used', '647168', '-'],
    ['test2/iocage', 'available', '468744720384', '-'],
    ['test2/iocage', 'mountpoint', '/mnt/test2/iocage', 'default'],
    ['test2/iocage', 'type', 'filesystem', '-'],
    ['test2/iocage/download', 'name', 'test2/iocage/download', '-'],
    ['test2/iocage/download', 'quota', '0', 'default'],
    ['test2/iocage/download', 'used', '90112', '-'],
    ['test2/iocage/download', 'available', '468744720384', '-'],
    [
        'test2/iocage/download', 'mountpoint', '/mnt/test2/iocage/download',
        'default'
    ], ['test2/iocage/download', 'type', 'filesystem', '-'],
    ['test2/iocage/images', 'name', 'test2/iocage/images', '-'],
    ['test2/iocage/images', 'quota', '0', 'default'],
    ['test2/iocage/images', 'used', '90112', '-'],
    ['test2/iocage/images', 'available', '468744720384', '-'],
    [
        'test2/iocage/images', 'mountpoint', '/mnt/test2/iocage/images',
        'default'
    ], ['test2/iocage/images', 'type', 'filesystem', '-'],
    ['test2/iocage/jails', 'name', 'test2/iocage/jails', '-'],
    ['test2/iocage/jails', 'quota', '0', 'default'],
    ['test2/iocage/jails', 'used', '90112', '-'],
    ['test2/iocage/jails', 'available', '468744720384', '-'],
    ['test2/iocage/jails', 'mountpoint', '/mnt/test2/iocage/jails', 'default'],
    ['test2/iocage/jails', 'type', 'filesystem', '-'],
    ['test2/iocage/log', 'name', 'test2/iocage/log', '-'],
    ['test2/iocage/log', 'quota', '0', 'default'],
    ['test2/iocage/log', 'used', '90112', '-'],
    ['test2/iocage/log', 'available', '468744720384', '-'],
    ['test2/iocage/log', 'mountpoint', '/mnt/test2/iocage/log', 'default'],
    ['test2/iocage/log', 'type', 'filesystem', '-'],
    ['test2/iocage/releases', 'name', 'test2/iocage/releases', '-'],
    ['test2/iocage/releases', 'quota', '0', 'default'],
    ['test2/iocage/releases', 'used', '90112', '-'],
    ['test2/iocage/releases', 'available', '468744720384', '-'],
    [
        'test2/iocage/releases', 'mountpoint', '/mnt/test2/iocage/releases',
        'default'
    ], ['test2/iocage/releases', 'type', 'filesystem', '-'],
    ['test2/iocage/templates', 'name', 'test2/iocage/templates', '-'],
    ['test2/iocage/templates', 'quota', '0', 'default'],
    ['test2/iocage/templates', 'used', '90112', '-'],
    ['test2/iocage/templates', 'available', '468744720384', '-'],
    [
        'test2/iocage/templates', 'mountpoint', '/mnt/test2/iocage/templates',
        'default'
    ], ['test2/iocage/templates', 'type', 'filesystem', '-'], ['[df]'],
    ['freenas-boot/ROOT/default    28942113  773360   28168753     3%    /'],
    [
        'test2                       457758604      88  457758516     0%    /mnt/test2'
    ],
    [
        'test2/ISO-File              459771112 2012596  457758516     0%    /mnt/test2/ISO-File'
    ],
    [
        'test2/Server1               465254332 7495816  457758516     2%    /mnt/test2/Server1'
    ],
    [
        'test2/iocage                457758620     104  457758516     0%    /mnt/test2/iocage'
    ],
    [
        'test2/iocage/download       457758604      88  457758516     0%    /mnt/test2/iocage/download'
    ],
    [
        'test2/iocage/images         457758604      88  457758516     0%    /mnt/test2/iocage/images'
    ],
    [
        'test2/iocage/jails          457758604      88  457758516     0%    /mnt/test2/iocage/jails'
    ],
    [
        'test2/iocage/log            457758604      88  457758516     0%    /mnt/test2/iocage/log'
    ],
    [
        'test2/iocage/releases       457758604      88  457758516     0%    /mnt/test2/iocage/releases'
    ],
    [
        'test2/iocage/templates      457758604      88  457758516     0%    /mnt/test2/iocage/templates'
    ],
    [
        'DataStorage                3759613713     176 3759613537     0%    /mnt/DataStorage'
    ],
    [
        'DataStorage/ ISO-File      3759613713     176 3759613537     0%    /mnt/DataStorage/ ISO-File'
    ],
    [
        'DataStorage/Server1a       3766994554 7381017 3759613537     0%    /mnt/DataStorage/Server1a'
    ]
]

discovery = {
    '': [
        ('/', {}),
        ('/mnt/DataStorage', {}), ('/mnt/DataStorage/ ISO-File', {}),
        ('/mnt/DataStorage/Server1a', {}), ('/mnt/test2', {}),
        ('/mnt/test2/ISO-File', {}), ('/mnt/test2/Server1', {}),
        ('/mnt/test2/iocage', {}), ('/mnt/test2/iocage/download', {}),
        ('/mnt/test2/iocage/images', {}), ('/mnt/test2/iocage/jails', {}),
        ('/mnt/test2/iocage/log', {}), ('/mnt/test2/iocage/releases', {}),
        ('/mnt/test2/iocage/templates', {})
    ]
}

checks = {
    '': [
        (
            '/', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '2.67% used (755 MiB of 27.6 GiB)', [
                        (
                            'fs_used', 755.234375, 22611.02578125,
                            25437.40400390625, 0, 28263.7822265625
                        ),
                        ('fs_size', 28263.7822265625, None, None, None, None),
                        (
                            'fs_used_percent', 2.672092393530493, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/DataStorage', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.2% used (7.04 GiB of 3.51 TiB)', [
                        (
                            'fs_used', 7209.889709472656, 2942965.987902832,
                            3310836.736390686, 0, 3678707.48487854
                        ),
                        ('fs_size', 3678707.48487854, None, None, None, None),
                        (
                            'fs_used_percent', 0.1959897528985158, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/DataStorage/ ISO-File', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.000005% used (176 KiB of 3.50 TiB)', [
                        (
                            'fs_used', 0.1717071533203125, 2937198.2135009766,
                            3304347.9901885986, 0, 3671497.7668762207
                        ),
                        (
                            'fs_size', 3671497.7668762207, None, None, None,
                            None
                        ),
                        (
                            'fs_used_percent', 4.676760391070704e-06, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/DataStorage/Server1a', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.2% used (7.04 GiB of 3.51 TiB)', [
                        (
                            'fs_used', 7208.024345397949, 2942964.495611572,
                            3310835.057563019, 0, 3678705.6195144653
                        ),
                        (
                            'fs_size', 3678705.6195144653, None, None, None,
                            None
                        ),
                        (
                            'fs_used_percent', 0.1959391452026352, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '2.04% used (9.07 of 446 GiB)', [
                        (
                            'fs_used', 9290.05859375, 365055.8875,
                            410687.8734375, 0, 456319.859375
                        ), ('fs_size', 456319.859375, None, None, None, None),
                        (
                            'fs_used_percent', 2.035865501552827, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/ISO-File', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.44% used (1.92 of 438 GiB)', [
                        (
                            'fs_used', 1965.42578125, 359196.18125,
                            404095.70390625, 0, 448995.2265625
                        ), ('fs_size', 448995.2265625, None, None, None, None),
                        (
                            'fs_used_percent', 0.43773868071989697, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/Server1', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '1.61% used (7.15 of 444 GiB)', [
                        (
                            'fs_used', 7320.1328125, 363479.946875,
                            408914.940234375, 0, 454349.93359375
                        ),
                        ('fs_size', 454349.93359375, None, None, None, None),
                        (
                            'fs_used_percent', 1.6111222366866644, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.0001% used (632 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.6171875, 357624.334375,
                            402327.376171875, 0, 447030.41796875
                        ),
                        ('fs_size', 447030.41796875, None, None, None, None),
                        (
                            'fs_used_percent', 0.00013806387109056747, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/download', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/images', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/jails', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/log', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/releases', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        ),
        (
            '/mnt/test2/iocage/templates', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [
                (
                    0, '0.00002% used (88.0 KiB of 437 GiB)', [
                        (
                            'fs_used', 0.0859375, 357623.909375,
                            402326.898046875, 0, 447029.88671875
                        ),
                        ('fs_size', 447029.88671875, None, None, None, None),
                        (
                            'fs_used_percent', 1.9224106162295095e-05, None,
                            None, None, None
                        )
                    ]
                )
            ]
        )
    ]
}
