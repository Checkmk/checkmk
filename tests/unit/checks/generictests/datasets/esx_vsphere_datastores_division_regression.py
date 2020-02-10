# -*- encoding: utf-8
# yapf: disable
checkname = 'esx_vsphere_datastores'

info = [
    [u'[backup_day_esx_blade_nfs_nfs32]'], [u'accessible', u'true'],
    [u'capacity', u'19923665018880'], [u'freeSpace', u'15224133410816'],
    [u'type', u'NFS'], [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/e430852e-b5e7cbe9'], [u'[storage_iso]'],
    [u'accessible', u'true'], [u'capacity', u'7869711945728'],
    [u'freeSpace', u'1835223412736'], [u'type', u'NFS'],
    [u'uncommitted', u'0'], [u'url', u'/vmfs/volumes/04cc2737-7d460e93'],
    [u'[vmware_files]'], [u'accessible', u'true'],
    [u'capacity', u'7869711945728'], [u'freeSpace', u'1835223412736'],
    [u'type', u'NFS'], [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/393e2076-21c41536'], [u'[datastore01]'],
    [u'accessible', u'true'], [u'capacity', u'4500588855296'],
    [u'freeSpace', u'1684666318848'], [u'type',
                                       u'VMFS'], [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/563b3611-f9333855-cfa1-00215e221152'],
    [u'[system01_20100701]'], [u'accessible', u'true'],
    [u'capacity', u'492042190848'], [u'freeSpace', u'491020877824'],
    [u'type', u'VMFS'], [u'uncommitted', u'0'],
    [u'url', u'/vmfs/volumes/56822303-d64ea045-c8cc-001a645a8f28']
]

discovery = {
    '': [
        (u'backup_day_esx_blade_nfs_nfs32', {}), (u'datastore01', {}),
        (u'storage_iso', {}), (u'system01_20100701', {}),
        (u'vmware_files', {})
    ]
}

checks = {
    '': [
        (
            u'backup_day_esx_blade_nfs_nfs32', {
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
                    0, '23.59% used (4.27 of 18.12 TB)', [
                        (
                            u'backup_day_esx_blade_nfs_nfs32', 4481822.59375,
                            15200550.09375, 17100618.85546875, 0,
                            19000687.6171875
                        ),
                        ('fs_size', 19000687.6171875, None, None, None, None)
                    ]
                ),
                (
                    0, 'Uncommitted: 0.00 B', [
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
            u'datastore01', {
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
                    0, '62.57% used (2.56 of 4.09 TB)', [
                        (
                            u'datastore01', 2685473.0, 3433676.8, 3862886.4, 0,
                            4292096.0
                        ), ('fs_size', 4292096.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Uncommitted: 0.00 B', [
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
            u'storage_iso', {
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
                    0, '76.68% used (5.49 of 7.16 TB)', [
                        (
                            u'storage_iso', 5754936.7265625, 6004113.728125,
                            6754627.944140625, 0, 7505142.16015625
                        ),
                        ('fs_size', 7505142.16015625, None, None, None, None)
                    ]
                ),
                (
                    0, 'Uncommitted: 0.00 B', [
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
            u'system01_20100701', {
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
                    0, '0.21% used (974.00 MB of 458.25 GB)', [
                        (
                            u'system01_20100701', 974.0, 375398.4, 422323.2, 0,
                            469248.0
                        ), ('fs_size', 469248.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Uncommitted: 0.00 B', [
                        ('uncommitted', 0.0, None, None, None, None)
                    ]
                ), (0, 'Provisioning: 0.21%', []),
                (0, '', [('overprovisioned', 974.0, None, None, None, None)])
            ]
        ),
        (
            u'vmware_files', {
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
                    0, '76.68% used (5.49 of 7.16 TB)', [
                        (
                            u'vmware_files', 5754936.7265625, 6004113.728125,
                            6754627.944140625, 0, 7505142.16015625
                        ),
                        ('fs_size', 7505142.16015625, None, None, None, None)
                    ]
                ),
                (
                    0, 'Uncommitted: 0.00 B', [
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
