#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'netapp_api_qtree_quota'

info = [
    [
        'quota fd-content-db', 'quota-type tree', 'disk-limit 52428800',
        'volume vol_bronze1_cifs', 'disk-used 24430212'
    ],
    [
        'quota fd-interface-BPROD', 'quota-type tree', 'disk-limit 15728640',
        'volume vol_bronze1_cifs', 'disk-used 5241944'
    ],
    [
        'quota fd-interface-LEGACY', 'quota-type tree', 'disk-limit 10485760',
        'volume vol_bronze1_cifs', 'disk-used 4720520'
    ],
    [
        'quota fd-interface-BTEST', 'quota-type tree', 'disk-limit 10485760',
        'volume vol_bronze1_cifs', 'disk-used 4752'
    ],
    [
        'quota fd-interface-TCLONE', 'quota-type tree', 'disk-limit 10485760',
        'volume vol_bronze1_cifs', 'disk-used 6487460'
    ],
    [
        'quota fd-interface-BCLONE', 'quota-type tree', 'disk-limit 5242880',
        'volume vol_bronze1_cifs', 'disk-used 43884'
    ],
    [
        'quota fd-interface-BOFA', 'quota-type tree', 'disk-limit 5242880',
        'volume vol_bronze1_cifs', 'disk-used 963468'
    ],
    [
        'quota fd-interface-BRM', 'quota-type tree', 'disk-limit 1048576',
        'volume vol_bronze1_cifs', 'disk-used 96'
    ],
    [
        'quota jiraarchiv', 'quota-type tree', 'disk-limit 52428800',
        'volume vol_bronze1_cifs', 'disk-used 583932'
    ],
    [
        'quota CP-SOC_Malware', 'quota-type tree', 'disk-limit 10485760',
        'volume vol_bronze1_cifs', 'disk-used 148096'
    ],
    [
        'quota CP-SOC_Dokumente', 'quota-type tree', 'disk-limit 10485760',
        'volume vol_bronze1_cifs', 'disk-used 2013628'
    ],
    [
        'quota FD-MIS-Drop$', 'quota-type tree', 'disk-limit 31457280',
        'volume vol_bronze1_cifs', 'disk-used 1580324'
    ]
]

discovery = {
    '': [
        ('CP-SOC_Dokumente', {}), ('CP-SOC_Malware', {}), ('FD-MIS-Drop$', {}),
        ('fd-content-db', {}), ('fd-interface-BCLONE', {}),
        ('fd-interface-BOFA', {}), ('fd-interface-BPROD', {}),
        ('fd-interface-BRM', {}), ('fd-interface-BTEST', {}),
        ('fd-interface-LEGACY', {}), ('fd-interface-TCLONE', {}),
        ('jiraarchiv', {})
    ]
}

checks = {
    '': [
        (
            'CP-SOC_Dokumente', {
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
                    0, '19.2% used (1.92 of 10.00 GB)', [
                        ('fs_used', 1966.43359375, 8192.0, 9216.0, 0, 10240.0),
                        ('fs_size', 10240.0, None, None, None, None),
                        (
                            'fs_used_percent', 19.203453063964844, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'CP-SOC_Malware', {
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
                    0, '1.41% used (144.62 MB of 10.00 GB)', [
                        ('fs_used', 144.625, 8192.0, 9216.0, 0, 10240.0),
                        ('fs_size', 10240.0, None, None, None, None),
                        (
                            'fs_used_percent', 1.412353515625, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'FD-MIS-Drop$', {
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
                    0, '5.02% used (1.51 of 30.00 GB)', [
                        (
                            'fs_used', 1543.28515625, 24576.0, 27648.0, 0,
                            30720.0
                        ), ('fs_size', 30720.0, None, None, None, None),
                        (
                            'fs_used_percent', 5.023714701334636, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-content-db', {
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
                    0, '46.6% used (23.30 of 50.00 GB)', [
                        (
                            'fs_used', 23857.62890625, 40960.0, 46080.0, 0,
                            51200.0
                        ), ('fs_size', 51200.0, None, None, None, None),
                        (
                            'fs_used_percent', 46.59693145751953, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-BCLONE', {
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
                    0, '0.84% used (42.86 MB of 5.00 GB)', [
                        ('fs_used', 42.85546875, 4096.0, 4608.0, 0, 5120.0),
                        ('fs_size', 5120.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.8370208740234375, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-BOFA', {
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
                    0, '18.38% used (940.89 MB of 5.00 GB)', [
                        ('fs_used', 940.88671875, 4096.0, 4608.0, 0, 5120.0),
                        ('fs_size', 5120.0, None, None, None, None),
                        (
                            'fs_used_percent', 18.376693725585938, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-BPROD', {
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
                    0, '33.33% used (5.00 of 15.00 GB)', [
                        (
                            'fs_used', 5119.0859375, 12288.0, 13824.0, 0,
                            15360.0
                        ), ('fs_size', 15360.0, None, None, None, None),
                        (
                            'fs_used_percent', 33.32738240559896, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-BRM', {
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
                    0, '0.009% used (96.00 kB of 1.00 GB)', [
                        ('fs_used', 0.09375, 819.2, 921.6, 0, 1024.0),
                        ('fs_size', 1024.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.0091552734375, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-BTEST', {
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
                    0, '0.05% used (4.64 MB of 10.00 GB)', [
                        ('fs_used', 4.640625, 8192.0, 9216.0, 0, 10240.0),
                        ('fs_size', 10240.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.045318603515625, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-LEGACY', {
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
                    0, '45.02% used (4.50 of 10.00 GB)', [
                        ('fs_used', 4609.8828125, 8192.0, 9216.0, 0, 10240.0),
                        ('fs_size', 10240.0, None, None, None, None),
                        (
                            'fs_used_percent', 45.01838684082031, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'fd-interface-TCLONE', {
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
                    0, '61.87% used (6.19 of 10.00 GB)', [
                        ('fs_used', 6335.41015625, 8192.0, 9216.0, 0, 10240.0),
                        ('fs_size', 10240.0, None, None, None, None),
                        (
                            'fs_used_percent', 61.869239807128906, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'jiraarchiv', {
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
                    0, '1.11% used (570.25 MB of 50.00 GB)', [
                        (
                            'fs_used', 570.24609375, 40960.0, 46080.0, 0,
                            51200.0
                        ), ('fs_size', 51200.0, None, None, None, None),
                        (
                            'fs_used_percent', 1.1137619018554688, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
