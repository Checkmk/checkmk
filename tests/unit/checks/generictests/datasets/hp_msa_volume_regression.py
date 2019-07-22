# yapf: disable
checkname = 'hp_msa_volume'

info = [[u'volumes', u'1', u'durable-id', u'V3'], [u'volumes', u'1', u'virtual-disk-name', u'A'],
        [u'volumes', u'1', u'total-size-numeric', u'4296482816'],
        [u'volumes', u'1', u'allocated-size-numeric', u'2484011008'],
        [u'volumes', u'1', u'container-name', u'A'], [u'volumes', u'1', u'raidtype', u'RAID0'],
        [u'volumes', u'1', u'health', u'OK'], [u'volumes', u'2', u'durable-id', u'V4'],
        [u'volumes', u'2', u'virtual-disk-name', u'A'],
        [u'volumes', u'2', u'total-size-numeric', u'4296286208'],
        [u'volumes', u'2', u'allocated-size-numeric', u'3925712896'],
        [u'volumes', u'2', u'container-name', u'A'], [u'volumes', u'2', u'raidtype', u'RAID0'],
        [u'volumes', u'2', u'health', u'OK'], [u'volumes', u'3', u'durable-id', u'V2'],
        [u'volumes', u'3', u'virtual-disk-name', u'A'],
        [u'volumes', u'3', u'total-size-numeric', u'195305472'],
        [u'volumes', u'3', u'allocated-size-numeric', u'48365568'],
        [u'volumes', u'3', u'container-name', u'A'], [u'volumes', u'3', u'raidtype', u'RAID0'],
        [u'volumes', u'3', u'health', u'OK'], [u'volumes', u'4', u'durable-id', u'V5'],
        [u'volumes', u'4', u'virtual-disk-name', u'A'],
        [u'volumes', u'4', u'total-size-numeric', u'859250688'],
        [u'volumes', u'4', u'allocated-size-numeric', u'676921344'],
        [u'volumes', u'4', u'container-name', u'A'], [u'volumes', u'4', u'raidtype', u'RAID0'],
        [u'volumes', u'4', u'health', u'OK'],
        [u'volume-statistics', u'1', u'volume-name', u'VMFS_01'],
        [u'volume-statistics', u'1', u'data-read-numeric', u'23719999539712'],
        [u'volume-statistics', u'1', u'data-written-numeric', u'18093374647808'],
        [u'volume-statistics', u'2', u'volume-name', u'VMFS_02'],
        [u'volume-statistics', u'2', u'data-read-numeric', u'49943891507200'],
        [u'volume-statistics', u'2', u'data-written-numeric', u'7384656100352'],
        [u'volume-statistics', u'3', u'volume-name', u'VMFS_ISO'],
        [u'volume-statistics', u'3', u'data-read-numeric', u'570950961152'],
        [u'volume-statistics', u'3', u'data-written-numeric', u'391124122624'],
        [u'volume-statistics', u'4', u'volume-name', u'VMFS_VDI_01'],
        [u'volume-statistics', u'4', u'data-read-numeric', u'5726598572544'],
        [u'volume-statistics', u'4', u'data-written-numeric', u'1305666958848']]

discovery = {
    '': [(u'VMFS_ISO', None), (u'VMFS_01', None), (u'VMFS_02', None), (u'VMFS_VDI_01', None)],
    'df': [(u'VMFS_ISO', {}), (u'VMFS_01', {}), (u'VMFS_02', {}), (u'VMFS_VDI_01', {})],
    'io': [('SUMMARY', 'diskstat_default_levels')]
}

checks = {
    '': [(u'VMFS_ISO', {}, [(0, u'Status: OK, container name: A (RAID0)', [])]),
         (u'VMFS_01', {}, [(0, u'Status: OK, container name: A (RAID0)', [])]),
         (u'VMFS_02', {}, [(0, u'Status: OK, container name: A (RAID0)', [])]),
         (u'VMFS_VDI_01', {}, [(0, u'Status: OK, container name: A (RAID0)', [])])],
    'df': [
        (u'VMFS_ISO', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, u'A (RAID0)', []),
            (0, '24.76% used (23.06 of 93.13 GB), trend: 0.00 B / 24 hours',
             [(u'VMFS_ISO', 23616, 76291.2, 85827.6, 0, 95364),
              ('fs_size', 95364, None, None, None, None), ('growth', 0.0, None, None, None, None),
              ('trend', 0, None, None, 0, 3973)])]),
        (u'VMFS_01', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, u'A (RAID0)', []),
            (0, '57.81% used (1.16 of 2.00 TB), trend: 0.00 B / 24 hours',
             [(u'VMFS_01', 1212896, 1678313.6, 1888102.8, 0, 2097892),
              ('fs_size', 2097892, None, None, None, None), ('growth', 0.0, None, None, None, None),
              ('trend', 0, None, None, 0, 87412)])]),
        (u'VMFS_02', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        },
         [(0, u'A (RAID0)', []),
          (2, '91.37% used (1.83 of 2.00 TB), (warn/crit at 80.0%/90.0%), trend: 0.00 B / 24 hours',
           [(u'VMFS_02', 1916852, 1678236.8, 1888016.4, 0, 2097796),
            ('fs_size', 2097796, None, None, None, None), ('growth', 0.0, None, None, None, None),
            ('trend', 0, None, None, 0, 87408)])]),
        (u'VMFS_VDI_01', {
            'trend_range': 24,
            'show_levels': 'onmagic',
            'inodes_levels': (10.0, 5.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'levels': (80.0, 90.0),
            'show_reserved': False,
            'levels_low': (50.0, 60.0),
            'trend_perfdata': True
        }, [(0, u'A (RAID0)', []),
            (0, '78.78% used (322.78 of 409.72 GB), trend: 0.00 B / 24 hours',
             [(u'VMFS_VDI_01', 330528, 335644.8, 377600.4, 0, 419556),
              ('fs_size', 419556, None, None, None, None), ('growth', 0.0, None, None, None, None),
              ('trend', 0, None, None, 0, 17481)])])
    ],
    'io': [('SUMMARY', {}, [
        (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0, None, None, None, None)]),
        (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0, None, None, None, None)]),
    ])]
}
