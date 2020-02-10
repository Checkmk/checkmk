# -*- encoding: utf-8
# yapf: disable
checkname = 'ceph_df'

info = [
    [u'RAW', u'STORAGE:'],
    [u'CLASS', u'SIZE', u'AVAIL', u'USED', u'RAW', u'USED', u'%RAW', u'USED'],
    [
        u'ssd', u'84', u'TiB', u'81', u'TiB', u'2.9', u'TiB', u'3.0', u'TiB',
        u'3.52'
    ],
    [
        u'TOTAL', u'84', u'TiB', u'81', u'TiB', u'2.9', u'TiB', u'3.0', u'TiB',
        u'3.52'
    ], [u'POOLS:'],
    [
        u'POOL', u'ID', u'STORED', u'OBJECTS', u'USED', u'%USED', u'MAX',
        u'AVAIL', u'QUOTA', u'OBJECTS', u'QUOTA', u'BYTES', u'DIRTY', u'USED',
        u'COMPR', u'UNDER', u'COMPR'
    ],
    [
        u'glance-images', u'1', u'25', u'GiB', u'5.88k', u'75', u'GiB',
        u'0.10', u'25', u'TiB', u'N/A', u'N/A', u'5.88k', u'0', u'B', u'0',
        u'B'
    ],
    [
        u'cinder-volumes', u'2', u'616', u'GiB', u'158.31k', u'1.8', u'TiB',
        u'2.32', u'25', u'TiB', u'N/A', u'N/A', u'158.31k', u'0', u'B', u'0',
        u'B'
    ],
    [
        u'nova-vms', u'3', u'349', u'GiB', u'91.08k', u'1.0', u'TiB', u'1.32',
        u'25', u'TiB', u'N/A', u'N/A', u'91.08k', u'0', u'B', u'0', u'B'
    ],
    [
        u'cephfs_data', u'4', u'0', u'B', u'0', u'0', u'B', u'0', u'25',
        u'TiB', u'N/A', u'N/A', u'0', u'0', u'B', u'0', u'B'
    ],
    [
        u'cephfs_metadata', u'5', u'15', u'KiB', u'60', u'969', u'KiB', u'0',
        u'25', u'TiB', u'N/A', u'N/A', u'60', u'0', u'B', u'0', u'B'
    ],
    [
        u'.rgw.root', u'6', u'2.6', u'KiB', u'6', u'288', u'KiB', u'0', u'25',
        u'TiB', u'N/A', u'N/A', u'6', u'0', u'B', u'0', u'B'
    ],
    [
        u'default.rgw.control', u'7', u'0', u'B', u'8', u'0', u'B', u'0',
        u'25', u'TiB', u'N/A', u'N/A', u'8', u'0', u'B', u'0', u'B'
    ],
    [
        u'default.rgw.meta', u'8', u'0', u'B', u'0', u'0', u'B', u'0', u'25',
        u'TiB', u'N/A', u'N/A', u'0', u'0', u'B', u'0', u'B'
    ],
    [
        u'default.rgw.log', u'9', u'0', u'B', u'207', u'0', u'B', u'0', u'25',
        u'TiB', u'N/A', u'N/A', u'207', u'0', u'B', u'0', u'B'
    ]
]

discovery = {
    '': [
        ('SUMMARY', {}), (u'.rgw.root', {}), (u'cephfs_data', {}),
        (u'cephfs_metadata', {}), (u'cinder-volumes', {}),
        (u'default.rgw.control', {}), (u'default.rgw.log', {}),
        (u'default.rgw.meta', {}), (u'glance-images', {}), (u'nova-vms', {})
    ]
}

checks = {
    '': [
        (
            'SUMMARY', {
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
                    0, '3.57% used (3.00 of 84.00 TB)', [
                        (
                            'SUMMARY', 3145728.0, 70464307.2, 79272345.6, 0,
                            88080384.0
                        ), ('fs_size', 88080384.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'.rgw.root', {
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
                    0, '0.000001% used (288.00 kB of 25.00 TB)', [
                        (
                            u'.rgw.root', 0.28125, 20971520.225,
                            23592960.253125, 0, 26214400.28125
                        ), ('fs_size', 26214400.28125, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'cephfs_data', {
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            u'cephfs_data', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'cephfs_metadata', {
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
                    0, '0.000004% used (969.00 kB of 25.00 TB)', [
                        (
                            u'cephfs_metadata', 0.9462890625,
                            20971520.75703125, 23592960.851660155, 0,
                            26214400.946289062
                        ),
                        (
                            'fs_size', 26214400.946289062, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            u'cinder-volumes', {
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
                    0, '6.72% used (1.80 of 26.80 TB)', [
                        (
                            u'cinder-volumes', 1887436.8000000007, 22481469.44,
                            25291653.12, 0, 28101836.8
                        ), ('fs_size', 28101836.8, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'default.rgw.control', {
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            u'default.rgw.control', 0.0, 20971520.0,
                            23592960.0, 0, 26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'default.rgw.log', {
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            u'default.rgw.log', 0.0, 20971520.0, 23592960.0, 0,
                            26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'default.rgw.meta', {
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
                    0, '0% used (0.00 B of 25.00 TB)', [
                        (
                            u'default.rgw.meta', 0.0, 20971520.0, 23592960.0,
                            0, 26214400.0
                        ), ('fs_size', 26214400.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'glance-images', {
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
                    0, '0.29% used (75.00 GB of 25.07 TB)', [
                        (
                            u'glance-images', 76800.0, 21032960.0, 23662080.0,
                            0, 26291200.0
                        ), ('fs_size', 26291200.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'nova-vms', {
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
                    0, '3.85% used (1.00 of 26.00 TB)', [
                        (
                            u'nova-vms', 1048576.0, 21810380.8, 24536678.4, 0,
                            27262976.0
                        ), ('fs_size', 27262976.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
