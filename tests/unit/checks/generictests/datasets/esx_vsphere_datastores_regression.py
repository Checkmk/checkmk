#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'esx_vsphere_datastores'

info = [
    ['[WIN-0108-MCC35-U-L008-SSD-EXC2]'], ['accessible', 'true'],
    ['capacity', '13193871097856'], ['freeSpace', '2879343558656'],
    ['type', 'VMFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/5bacc6e6-1f214d64-5023-901b0e6d02d5'],
    ['[WIN-0100-MCC15-M-L000-SSD]'], ['accessible', 'true'],
    ['capacity', '4397778075648'], ['freeSpace', '3310200291328'],
    ['type', 'VMFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/5bc5b243-c6c57438-bc07-4c52621258cd'],
    ['[VeeamBackup_bvk-srv01]'], ['accessible', 'false'], ['capacity', '0'],
    ['freeSpace', '0'], ['type', 'NFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/2648fab8-4c508495']
]

discovery = {
    '': [
        ('VeeamBackup_bvk-srv01', {}), ('WIN-0100-MCC15-M-L000-SSD', {}),
        ('WIN-0108-MCC35-U-L008-SSD-EXC2', {})
    ]
}

checks = {
    '': [
        (
            'WIN-0100-MCC15-M-L000-SSD', {
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
                    0, '24.73% used (1013 GiB of 4.00 TiB)', [
                        (
                            'fs_used', 1037195.0, 3355238.4, 3774643.2, 0,
                            4194048.0
                        ), ('fs_size', 4194048.0, None, None, None, None),
                        (
                            'fs_used_percent', 24.730165224623086, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 24.73%', []),
                (
                    0, '', [
                        ('overprovisioned', 1037195.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'WIN-0108-MCC35-U-L008-SSD-EXC2', {
                'provisioning_levels': (70.0, 80.0)
            }, [
                (
                    0, '78.18% used (9.38 of 12.0 TiB)', [
                        (
                            'fs_used', 9836700.0, 10066124.8, 11324390.4, 0,
                            12582656.0
                        ), ('fs_size', 12582656.0, None, None, None, None),
                        (
                            'fs_used_percent', 78.17665840979838, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (1, 'Provisioning: 78.18% (warn/crit at 70.00%/80.00%)', []),
                (
                    0, '', [
                        (
                            'overprovisioned', 9836700.0, 8807859.2,
                            10066124.8, None, None
                        )
                    ]
                )
            ]
        ),
        (
            'WIN-0108-MCC35-U-L008-SSD-EXC2', {
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
                    0, '78.18% used (9.38 of 12.0 TiB)', [
                        (
                            'fs_used', 9836700.0, 10066124.8, 11324390.4, 0,
                            12582656.0
                        ), ('fs_size', 12582656.0, None, None, None, None),
                        (
                            'fs_used_percent', 78.17665840979838, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 78.18%', []),
                (
                    0, '', [
                        ('overprovisioned', 9836700.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'VeeamBackup_bvk-srv01', {
                'levels': (80.0, 90.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'onlow',
                'show_reserved': False
            }, [(2, 'inaccessible', [])]
        )
    ]
}
