#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'esx_vsphere_datastores'

info = [
    ['[backup_day_esx_blade_nfs_nfs32]'], ['accessible', 'true'],
    ['capacity', '19923665018880'], ['freeSpace', '15224133410816'],
    ['type', 'NFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/e430852e-b5e7cbe9'], ['[storage_iso]'],
    ['accessible', 'true'], ['capacity', '7869711945728'],
    ['freeSpace', '1835223412736'], ['type', 'NFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/04cc2737-7d460e93'], ['[vmware_files]'],
    ['accessible', 'true'], ['capacity', '7869711945728'],
    ['freeSpace', '1835223412736'], ['type', 'NFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/393e2076-21c41536'], ['[datastore01]'],
    ['accessible', 'true'], ['capacity', '4500588855296'],
    ['freeSpace', '1684666318848'], ['type', 'VMFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/563b3611-f9333855-cfa1-00215e221152'],
    ['[system01_20100701]'], ['accessible', 'true'],
    ['capacity', '492042190848'], ['freeSpace', '491020877824'],
    ['type', 'VMFS'], ['uncommitted', '0'],
    ['url', '/vmfs/volumes/56822303-d64ea045-c8cc-001a645a8f28']
]

discovery = {
    '': [
        ('backup_day_esx_blade_nfs_nfs32', {}), ('datastore01', {}),
        ('storage_iso', {}), ('system01_20100701', {}), ('vmware_files', {})
    ]
}

checks = {
    '': [
        (
            'backup_day_esx_blade_nfs_nfs32', {
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
                    0, '23.59% used (4.27 of 18.1 TiB)', [
                        (
                            'fs_used', 4481822.59375, 15200550.09375,
                            17100618.85546875, 0, 19000687.6171875
                        ),
                        ('fs_size', 19000687.6171875, None, None, None, None),
                        (
                            'fs_used_percent', 23.587686319814377, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 23.59%', []),
                (
                    0, '', [
                        (
                            'overprovisioned', 4481822.59375, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'datastore01', {
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
                    0, '62.57% used (2.56 of 4.09 TiB)', [
                        (
                            'fs_used', 2685473.0, 3433676.8, 3862886.4, 0,
                            4292096.0
                        ), ('fs_size', 4292096.0, None, None, None, None),
                        (
                            'fs_used_percent', 62.56786893862579, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 62.57%', []),
                (
                    0, '', [
                        ('overprovisioned', 2685473.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'storage_iso', {
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
                    0, '76.68% used (5.49 of 7.16 TiB)', [
                        (
                            'fs_used', 5754936.7265625, 6004113.728125,
                            6754627.944140625, 0, 7505142.16015625
                        ),
                        ('fs_size', 7505142.16015625, None, None, None, None),
                        (
                            'fs_used_percent', 76.67991629944939, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 76.68%', []),
                (
                    0, '', [
                        (
                            'overprovisioned', 5754936.7265625, None, None,
                            None, None
                        )
                    ]
                )
            ]
        ),
        (
            'system01_20100701', {
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
                    0, '0.21% used (974 MiB of 458 GiB)', [
                        ('fs_used', 974.0, 375398.4, 422323.2, 0, 469248.0),
                        ('fs_size', 469248.0, None, None, None, None),
                        (
                            'fs_used_percent', 0.2075661483906165, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 0.21%', []),
                (0, '', [('overprovisioned', 974.0, None, None, None, None)])
            ]
        ),
        (
            'vmware_files', {
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
                    0, '76.68% used (5.49 of 7.16 TiB)', [
                        (
                            'fs_used', 5754936.7265625, 6004113.728125,
                            6754627.944140625, 0, 7505142.16015625
                        ),
                        ('fs_size', 7505142.16015625, None, None, None, None),
                        (
                            'fs_used_percent', 76.67991629944939, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Uncommitted: 0 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 76.68%', []),
                (
                    0, '', [
                        (
                            'overprovisioned', 5754936.7265625, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
