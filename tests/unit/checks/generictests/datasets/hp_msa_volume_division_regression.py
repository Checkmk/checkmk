#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'hp_msa_volume'

info = [
    ['volumes', '1', 'durable-id', 'V0'],
    ['volumes', '1', 'virtual-disk-name', 'IMSAKO2B1_U1_B01-04'],
    ['volumes', '1', 'storage-pool-name', 'IMSAKO2B1_U1_B01-04'],
    ['volumes', '1', 'volume-name', 'IMSAKO2B1_U1_B01-04_v0001'],
    ['volumes', '1', 'size', '1198.9GB'],
    ['volumes', '1', 'size-numeric', '2341789696'],
    ['volumes', '1', 'total-size', '1198.9GB'],
    ['volumes', '1', 'total-size-numeric', '2341789696'],
    ['volumes', '1', 'allocated-size', '1198.9GB'],
    ['volumes', '1', 'allocated-size-numeric', '2341789696'],
    ['volumes', '1', 'storage-type', 'Linear'],
    ['volumes', '1', 'storage-type-numeric', '0'],
    ['volumes', '1', 'preferred-owner', 'A'],
    ['volumes', '1', 'preferred-owner-numeric', '1'],
    ['volumes', '1', 'owner', 'A'], ['volumes', '1', 'owner-numeric', '1'],
    ['volumes', '1', 'serial-number', '00c0ff1ec44a00008425415501000000'],
    ['volumes', '1', 'write-policy', 'write-back'],
    ['volumes', '1', 'write-policy-numeric', '1'],
    ['volumes', '1', 'cache-optimization', 'standard'],
    ['volumes', '1', 'cache-optimization-numeric', '0'],
    ['volumes', '1', 'read-ahead-size', 'Adaptive'],
    ['volumes', '1', 'read-ahead-size-numeric', '-1'],
    ['volumes', '1', 'volume-type', 'standard'],
    ['volumes', '1', 'volume-type-numeric', '0'],
    ['volumes', '1', 'volume-class', 'standard'],
    ['volumes', '1', 'volume-class-numeric', '0'],
    ['volumes', '1', 'profile-preference', 'Standard'],
    ['volumes', '1', 'profile-preference-numeric', '0'],
    ['volumes', '1', 'snapshot', 'No'],
    ['volumes', '1', 'volume-qualifier', 'N/A'],
    ['volumes', '1', 'volume-qualifier-numeric', '0'],
    ['volumes', '1', 'blocks', '2341789696'],
    ['volumes', '1', 'capabilities', 'dmscer'],
    ['volumes', '1', 'volume-parent'], ['volumes', '1', 'snap-pool'],
    ['volumes', '1', 'replication-set'], ['volumes', '1', 'attributes'],
    [
        'volumes', '1', 'virtual-disk-serial',
        '00c0ff1ec44a00001e23415500000000'
    ], ['volumes', '1', 'volume-description'],
    ['volumes', '1', 'wwn', '600C0FF0001EC44A8425415501000000'],
    ['volumes', '1', 'progress', '0%'],
    ['volumes', '1', 'progress-numeric', '0'],
    ['volumes', '1', 'container-name', 'IMSAKO2B1_U1_B01-04'],
    ['volumes', '1', 'container-serial', '00c0ff1ec44a00001e23415500000000'],
    ['volumes', '1', 'allowed-storage-tiers', 'N/A'],
    ['volumes', '1', 'allowed-storage-tiers-numeric', '0'],
    ['volumes', '1', 'threshold-percent-of-pool', '0'],
    ['volumes', '1', 'reserved-size-in-pages', '0'],
    ['volumes', '1', 'allocate-reserved-pages-first', 'Disabled'],
    ['volumes', '1', 'allocate-reserved-pages-first-numeric', '0'],
    ['volumes', '1', 'zero-init-page-on-allocation', 'Disabled'],
    ['volumes', '1', 'zero-init-page-on-allocation-numeric', '0'],
    ['volumes', '1', 'raidtype', 'RAID10'],
    ['volumes', '1', 'raidtype-numeric', '10'],
    ['volumes', '1', 'pi-format', 'T0'],
    ['volumes', '1', 'pi-format-numeric', '0'],
    ['volumes', '1', 'health', 'Warning'],
    ['volumes', '1', 'health-numeric', '0'],
    ['volumes', '1', 'health-reason', 'There', 'is', 'a', 'warning'],
    ['volumes', '1', 'health-recommendation'],
    ['volumes', '1', 'volume-group', 'UNGROUPEDVOLUMES'],
    ['volumes', '1', 'group-key', 'VGU'],
    ['volumes', '1', 'serial-number', '00c0ff1ec44a00008425415501000000'],
    ['volumes', '2', 'durable-id', 'V3'],
    ['volumes', '2', 'virtual-disk-name', 'IMSAKO2B1_U1_B05-08'],
    ['volumes', '2', 'storage-pool-name', 'IMSAKO2B1_U1_B05-08'],
    ['volumes', '2', 'volume-name', 'IMSAKO2B1_U1_B05-08_v0001'],
    ['volumes', '2', 'size', '1198.9GB'],
    ['volumes', '2', 'size-numeric', '2341789696'],
    ['volumes', '2', 'total-size', '1198.9GB'],
    ['volumes', '2', 'total-size-numeric', '2341789696'],
    ['volumes', '2', 'allocated-size', '1198.9GB'],
    ['volumes', '2', 'allocated-size-numeric', '2341789696'],
    ['volumes', '2', 'storage-type', 'Linear'],
    ['volumes', '2', 'storage-type-numeric', '0'],
    ['volumes', '2', 'preferred-owner', 'B'],
    ['volumes', '2', 'preferred-owner-numeric', '0'],
    ['volumes', '2', 'owner', 'B'], ['volumes', '2', 'owner-numeric', '0'],
    ['volumes', '2', 'serial-number', '00c0ff1ec10b00009925415501000000'],
    ['volumes', '2', 'write-policy', 'write-back'],
    ['volumes', '2', 'write-policy-numeric', '1'],
    ['volumes', '2', 'cache-optimization', 'standard'],
    ['volumes', '2', 'cache-optimization-numeric', '0'],
    ['volumes', '2', 'read-ahead-size', 'Adaptive'],
    ['volumes', '2', 'read-ahead-size-numeric', '-1'],
    ['volumes', '2', 'volume-type', 'standard'],
    ['volumes', '2', 'volume-type-numeric', '0'],
    ['volumes', '2', 'volume-class', 'standard'],
    ['volumes', '2', 'volume-class-numeric', '0'],
    ['volumes', '2', 'profile-preference', 'Standard'],
    ['volumes', '2', 'profile-preference-numeric', '0'],
    ['volumes', '2', 'snapshot', 'No'],
    ['volumes', '2', 'volume-qualifier', 'N/A'],
    ['volumes', '2', 'volume-qualifier-numeric', '0'],
    ['volumes', '2', 'blocks', '2341789696'],
    ['volumes', '2', 'capabilities', 'dmscer'],
    ['volumes', '2', 'volume-parent'], ['volumes', '2', 'snap-pool'],
    ['volumes', '2', 'replication-set'], ['volumes', '2', 'attributes'],
    [
        'volumes', '2', 'virtual-disk-serial',
        '00c0ff1ec10b0000e423415500000000'
    ], ['volumes', '2', 'volume-description'],
    ['volumes', '2', 'wwn', '600C0FF0001EC10B9925415501000000'],
    ['volumes', '2', 'progress', '0%'],
    ['volumes', '2', 'progress-numeric', '0'],
    ['volumes', '2', 'container-name', 'IMSAKO2B1_U1_B05-08'],
    ['volumes', '2', 'container-serial', '00c0ff1ec10b0000e423415500000000'],
    ['volumes', '2', 'allowed-storage-tiers', 'N/A'],
    ['volumes', '2', 'allowed-storage-tiers-numeric', '0'],
    ['volumes', '2', 'threshold-percent-of-pool', '0'],
    ['volumes', '2', 'reserved-size-in-pages', '0'],
    ['volumes', '2', 'allocate-reserved-pages-first', 'Disabled'],
    ['volumes', '2', 'allocate-reserved-pages-first-numeric', '0'],
    ['volumes', '2', 'zero-init-page-on-allocation', 'Disabled'],
    ['volumes', '2', 'zero-init-page-on-allocation-numeric', '0'],
    ['volumes', '2', 'raidtype', 'RAID10'],
    ['volumes', '2', 'raidtype-numeric', '10'],
    ['volumes', '2', 'pi-format', 'T0'],
    ['volumes', '2', 'pi-format-numeric',
     '0'], ['volumes', '2', 'health', 'OK'],
    ['volumes', '2', 'health-numeric', '0'], ['volumes', '2', 'health-reason'],
    ['volumes', '2', 'health-recommendation'],
    ['volumes', '2', 'volume-group', 'UNGROUPEDVOLUMES'],
    ['volumes', '2', 'group-key', 'VGU'],
    ['volume-statistics', '1', 'bytes-per-second', '2724.3KB'],
    ['volume-statistics', '1', 'bytes-per-second-numeric', '2724352'],
    ['volume-statistics', '1', 'iops', '66'],
    ['volume-statistics', '1', 'number-of-reads', '11965055'],
    ['volume-statistics', '1', 'number-of-writes', '80032996'],
    ['volume-statistics', '1', 'data-read', '1241.3GB'],
    ['volume-statistics', '1', 'data-read-numeric', '1241361379840'],
    ['volume-statistics', '1', 'data-written', '6462.6GB'],
    ['volume-statistics', '1', 'data-written-numeric', '6462660316672'],
    ['volume-statistics', '1', 'allocated-pages', '0'],
    ['volume-statistics', '1', 'percent-tier-ssd', '0'],
    ['volume-statistics', '1', 'percent-tier-sas', '0'],
    ['volume-statistics', '1', 'percent-tier-sata', '0'],
    ['volume-statistics', '1', 'percent-allocated-rfc', '0'],
    ['volume-statistics', '1', 'pages-alloc-per-minute', '0'],
    ['volume-statistics', '1', 'pages-dealloc-per-minute', '0'],
    ['volume-statistics', '1', 'shared-pages', '0'],
    ['volume-statistics', '1', 'write-cache-hits', '93581599'],
    ['volume-statistics', '1', 'write-cache-misses', '345571865'],
    ['volume-statistics', '1', 'read-cache-hits', '29276023'],
    ['volume-statistics', '1', 'read-cache-misses', '54728207'],
    ['volume-statistics', '1', 'small-destages', '36593447'],
    ['volume-statistics', '1', 'full-stripe-write-destages', '4663277'],
    ['volume-statistics', '1', 'read-ahead-operations', '4804068203594569116'],
    ['volume-statistics', '1', 'write-cache-space', '74'],
    ['volume-statistics', '1', 'write-cache-percent', '8'],
    ['volume-statistics', '1', 'reset-time', '2015-05-22', '13:54:36'],
    ['volume-statistics', '1', 'reset-time-numeric', '1432302876'],
    ['volume-statistics', '1', 'start-sample-time', '2015-08-21', '11:51:17'],
    ['volume-statistics', '1', 'start-sample-time-numeric', '1440157877'],
    ['volume-statistics', '1', 'stop-sample-time', '2015-08-21', '11:51:48'],
    ['volume-statistics', '1', 'stop-sample-time-numeric', '1440157908'],
    ['volume-statistics', '2', 'volume-name', 'IMSAKO2B1_U1_B05-08_v0001'],
    [
        'volume-statistics', '2', 'serial-number',
        '00c0ff1ec10b00009925415501000000'
    ], ['volume-statistics', '2', 'bytes-per-second', '1064.9KB'],
    ['volume-statistics', '2', 'bytes-per-second-numeric', '1064960'],
    ['volume-statistics', '2', 'iops', '45'],
    ['volume-statistics', '2', 'number-of-reads', '9892573'],
    ['volume-statistics', '2', 'number-of-writes', '76500553'],
    ['volume-statistics', '2', 'data-read', '1242.5GB'],
    ['volume-statistics', '2', 'data-read-numeric', '1242509234176'],
    ['volume-statistics', '2', 'data-written', '6572.7GB'],
    ['volume-statistics', '2', 'data-written-numeric', '6572795755008'],
    ['volume-statistics', '2', 'allocated-pages', '0'],
    ['volume-statistics', '2', 'percent-tier-ssd', '0'],
    ['volume-statistics', '2', 'percent-tier-sas', '0'],
    ['volume-statistics', '2', 'percent-tier-sata', '0'],
    ['volume-statistics', '2', 'percent-allocated-rfc', '0'],
    ['volume-statistics', '2', 'pages-alloc-per-minute', '0'],
    ['volume-statistics', '2', 'pages-dealloc-per-minute', '0'],
    ['volume-statistics', '2', 'shared-pages', '0'],
    ['volume-statistics', '2', 'write-cache-hits', '83182170'],
    ['volume-statistics', '2', 'write-cache-misses', '359922110'],
    ['volume-statistics', '2', 'read-cache-hits', '28226639'],
    ['volume-statistics', '2', 'read-cache-misses', '54120346'],
    ['volume-statistics', '2', 'small-destages', '32838729'],
    ['volume-statistics', '2', 'full-stripe-write-destages', '4893881'],
    ['volume-statistics', '2', 'read-ahead-operations', '4804068203594574099'],
    ['volume-statistics', '2', 'write-cache-space', '73'],
    ['volume-statistics', '2', 'write-cache-percent', '8'],
    ['volume-statistics', '2', 'reset-time', '2015-04-29', '11:47:48'],
    ['volume-statistics', '2', 'reset-time-numeric', '1430308068'],
    ['volume-statistics', '2', 'start-sample-time', '2015-08-21', '11:51:17'],
    ['volume-statistics', '2', 'start-sample-time-numeric', '1440157877'],
    ['volume-statistics', '2', 'stop-sample-time', '2015-08-21', '11:51:47'],
    ['volume-statistics', '2', 'stop-sample-time-numeric', '1440157907']
]

discovery = {
    '':
    [('IMSAKO2B1_U1_B01-04_v0001', None), ('IMSAKO2B1_U1_B05-08_v0001', None)],
    'df':
    [('IMSAKO2B1_U1_B01-04_v0001', {}), ('IMSAKO2B1_U1_B05-08_v0001', {})],
    'io': [('SUMMARY', 'diskstat_default_levels')]
}

checks = {
    '': [
        (
            'IMSAKO2B1_U1_B01-04_v0001', {}, [
                (
                    1,
                    'Status: warning (There is a warning), container name: IMSAKO2B1_U1_B01-04 (RAID10)',
                    []
                )
            ]
        ),
        (
            'IMSAKO2B1_U1_B05-08_v0001', {}, [
                (
                    0,
                    'Status: OK, container name: IMSAKO2B1_U1_B05-08 (RAID10)',
                    []
                )
            ]
        )
    ],
    'df': [
        (
            'IMSAKO2B1_U1_B01-04_v0001', {
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
                (0, 'IMSAKO2B1_U1_B01-04 (RAID10)', []),
                (
                    2,
                    '100% used (1.09 of 1.09 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        ('fs_used', 1143452, 914761.6, 1029106.8, 0, 1143452),
                        ('fs_size', 1143452, None, None, None, None),
                        ('fs_used_percent', 100.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'IMSAKO2B1_U1_B05-08_v0001', {
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
                (0, 'IMSAKO2B1_U1_B05-08 (RAID10)', []),
                (
                    2,
                    '100% used (1.09 of 1.09 TiB, warn/crit at 80.00%/90.00%)',
                    [
                        ('fs_used', 1143452, 914761.6, 1029106.8, 0, 1143452),
                        ('fs_size', 1143452, None, None, None, None),
                        ('fs_used_percent', 100.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'io': [
        (
            'SUMMARY', {}, [
                (
                    0, 'Read: 0.00 B/s', [
                        ('disk_read_throughput', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write: 0.00 B/s', [
                        ('disk_write_throughput', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
