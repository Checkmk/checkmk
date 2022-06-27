#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'emcvnx_storage_pools'

info = [
    [u'[[[storage_pools]]]'], [u'Pool Name',
                               u'  Pool 0'], [u'Pool ID', u'  0'],
    [u'Raid Type', u'  r_5'], [u'Percent Full Threshold', u'  70'],
    [u'Description', u'  '], [u'Disk Type', u'  SAS'], [u'State', u'  Ready'],
    [u'Status', u'  OK(0x0)'], [u'Current Operation', u'  None'],
    [u'Current Operation State', u'  N/A'],
    [u'Current Operation Status', u'  N/A'],
    [u'Current Operation Percent Completed', u'  0'],
    [u'Raw Capacity (Blocks)', u'  40527668736'],
    [u'Raw Capacity (GBs)', u'  19325.098'],
    [u'User Capacity (Blocks)', u'  35990175744'],
    [u'User Capacity (GBs)', u'  17161.453'],
    [u'Consumed Capacity (Blocks)', u'  20201398272'],
    [u'Consumed Capacity (GBs)', u'  9632.777'],
    [u'Available Capacity (Blocks)', u'  15788777472'],
    [u'Available Capacity (GBs)', u'  7528.676'],
    [u'Percent Full', u'  56.130'],
    [u'LUN Allocation (Blocks)', u'  19501416448'],
    [u'LUN Allocation (GBs)', u'  9299.000'],
    [u'Snapshot Allocation (Blocks)', u'  0'],
    [u'Snapshot Allocation (GBs)', u'  0.000'],
    [u'Metadata Allocation (Blocks)', u'  699981824'],
    [u'Metadata Allocation (GBs)', u'  333.777'],
    [u'Total Subscribed Capacity (Blocks)', u'  20201398272'],
    [u'Total Subscribed Capacity (GBs)', u'  9632.777'],
    [u'Percent Subscribed', u'  56.130'],
    [u'Oversubscribed by (Blocks)', u'  0'],
    [u'Oversubscribed by (GBs)', u'  0.000'],
    [u'LUN Subscribed Capacity (Blocks)', u'  19501416448'],
    [u'LUN Subscribed Capacity (GBs)', u'  9299.000'],
    [u'Snapshot Subscribed Capacity (Blocks)', u'  0'],
    [u'Snapshot Subscribed Capacity (GBs)', u'  0.000'],
    [u'Metadata Subscribed Capacity (Blocks)', u'  699981824'],
    [u'Metadata Subscribed Capacity (GBs)', u'  333.777'],
    [u'Compression Savings (Blocks)', u'  N/A'],
    [u'Compression Savings (GBs)', u'  N/A'], [u''],
    [u'Tier Name', u'  Performance'], [u'Raid Type', u'  r_5'],
    [u'Raid Drive Count', u'  9'], [u'User Capacity (GBs)', u'  17161.45'],
    [u'Consumed Capacity (GBs)', u'  9632.78'],
    [u'Available Capacity (GBs)', u'  7528.68'],
    [u'Percent Subscribed', u'  56.13%'], [u'Disks (Type)', u''],
    [u'Bus 1 Enclosure 0 Disk 1 (SAS)'], [u'Bus 1 Enclosure 0 Disk 8 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 13 (SAS)'], [u'Bus 0 Enclosure 1 Disk 10 (SAS)'],
    [u'Bus 0 Enclosure 0 Disk 7 (SAS)'], [u'Bus 0 Enclosure 0 Disk 9 (SAS)'],
    [u'Bus 0 Enclosure 0 Disk 10 (SAS)'], [u'Bus 0 Enclosure 0 Disk 12 (SAS)'],
    [u'Bus 0 Enclosure 0 Disk 14 (SAS)'], [u'Bus 0 Enclosure 1 Disk 1 (SAS)'],
    [u'Bus 0 Enclosure 1 Disk 3 (SAS)'], [u'Bus 0 Enclosure 1 Disk 5 (SAS)'],
    [u'Bus 0 Enclosure 1 Disk 7 (SAS)'], [u'Bus 0 Enclosure 1 Disk 9 (SAS)'],
    [u'Bus 0 Enclosure 1 Disk 0 (SAS)'], [u'Bus 1 Enclosure 0 Disk 10 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 7 (SAS)'], [u'Bus 1 Enclosure 0 Disk 9 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 12 (SAS)'], [u'Bus 1 Enclosure 0 Disk 3 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 5 (SAS)'], [u'Bus 0 Enclosure 0 Disk 6 (SAS)'],
    [u'Bus 0 Enclosure 0 Disk 8 (SAS)'], [u'Bus 0 Enclosure 1 Disk 2 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 0 (SAS)'], [u'Bus 1 Enclosure 0 Disk 11 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 14 (Unknown)'],
    [u'Bus 1 Enclosure 0 Disk 6 (SAS)'], [u'Bus 1 Enclosure 0 Disk 2 (SAS)'],
    [u'Bus 1 Enclosure 0 Disk 4 (SAS)'], [u'Bus 0 Enclosure 0 Disk 11 (SAS)'],
    [u'Bus 0 Enclosure 0 Disk 13 (SAS)'], [u'Bus 0 Enclosure 1 Disk 4 (SAS)'],
    [u'Bus 0 Enclosure 1 Disk 6 (SAS)'], [u'Bus 0 Enclosure 1 Disk 8 (SAS)'],
    [u'Bus 0 Enclosure 1 Disk 11 (SAS)'], [u''],
    [u'Rebalance Percent Complete', u'  N/A'], [u'Disks', u''],
    [u'Bus 1 Enclosure 0 Disk 1'], [u'Bus 1 Enclosure 0 Disk 13'],
    [u'Bus 1 Enclosure 0 Disk 8'], [u'Bus 0 Enclosure 1 Disk 10'],
    [u'Bus 0 Enclosure 0 Disk 14'], [u'Bus 0 Enclosure 0 Disk 12'],
    [u'Bus 0 Enclosure 0 Disk 10'], [u'Bus 0 Enclosure 0 Disk 9'],
    [u'Bus 0 Enclosure 0 Disk 7'], [u'Bus 0 Enclosure 1 Disk 9'],
    [u'Bus 0 Enclosure 1 Disk 7'], [u'Bus 0 Enclosure 1 Disk 5'],
    [u'Bus 0 Enclosure 1 Disk 3'], [u'Bus 0 Enclosure 1 Disk 1'],
    [u'Bus 0 Enclosure 1 Disk 0'], [u'Bus 1 Enclosure 0 Disk 10'],
    [u'Bus 1 Enclosure 0 Disk 12'], [u'Bus 1 Enclosure 0 Disk 9'],
    [u'Bus 1 Enclosure 0 Disk 7'], [u'Bus 1 Enclosure 0 Disk 5'],
    [u'Bus 1 Enclosure 0 Disk 3'], [u'Bus 0 Enclosure 0 Disk 8'],
    [u'Bus 0 Enclosure 0 Disk 6'], [u'Bus 0 Enclosure 1 Disk 2'],
    [u'Bus 1 Enclosure 0 Disk 0'], [u'Bus 1 Enclosure 0 Disk 11'],
    [u'Bus 1 Enclosure 0 Disk 14'], [u'Bus 1 Enclosure 0 Disk 6'],
    [u'Bus 1 Enclosure 0 Disk 4'], [u'Bus 1 Enclosure 0 Disk 2'],
    [u'Bus 0 Enclosure 0 Disk 13'], [u'Bus 0 Enclosure 0 Disk 11'],
    [u'Bus 0 Enclosure 1 Disk 11'], [u'Bus 0 Enclosure 1 Disk 8'],
    [u'Bus 0 Enclosure 1 Disk 6'], [u'Bus 0 Enclosure 1 Disk 4'],
    [
        u'LUNs',
        u'  136, 120, 111, 127, 131, 130, 121, 133, 102, 132, 103, 107, 126, 138, 137, 134, 105, 101, 109, 128, 122, 106, 129, 110, 123, 124, 135, 104, 100, 108, 125'
    ], [u'FAST Cache', u'  N/A'],
    [u'Auto-Delete Pool Full Threshold Enabled', u'  Off'],
    [u'Auto-Delete Pool Full High Watermark', u'  95.00'],
    [u'Auto-Delete Pool Full Low Watermark', u'  85.00'],
    [u'Auto-Delete Pool Full State', u'  Idle'],
    [u'Auto-Delete Snapshot Space Used Threshold Enabled', u'  Off'],
    [u'Auto-Delete Snapshot Space Used High Watermark', u'  25.00'],
    [u'Auto-Delete Snapshot Space Used Low Watermark', u'  20.00'],
    [u'Auto-Delete Snapshot Space Used State',
     u'  Idle'], [u''], [u'[[[auto_tiering]]]'],
    [u'Auto-tiering is not supported on this system.'],
    [u'Unrecognized option', u' (-info).']
]

discovery = {
    '': [(u'Pool 0', {})],
    'tiering': [(u'Pool 0', {})],
    'tieringtypes': [(u'Pool 0 Performance', {})],
    'deduplication': [(u'Pool 0', {})]
}

checks = {
    '': [
        (
            u'Pool 0', {
                'percent_full': (70.0, 90.0)
            }, [
                (
                    0,
                    u'State: Ready, Status: OK(0x0), [Phys. capacity] User capacity: 16.8 TiB, Consumed capacity: 9.41 TiB, Available capacity: 7.35 TiB',
                    []
                ), (0, 'Percent full: 56.13%', []),
                (
                    0,
                    '[Virt. capacity] Percent subscribed: 56.13%, Oversubscribed by: 0 B, Total subscribed capacity: 9.41 TiB',
                    [
                        (
                            'emcvnx_consumed_capacity', 10343115546165.248,
                            None, None, None, None
                        ),
                        (
                            'emcvnx_avail_capacity', 8083854300545.024, None,
                            None, None, None
                        ), ('emcvnx_perc_full', 56.13, None, None, None, None),
                        (
                            'emcvnx_perc_subscribed', 56.13, None, None, None,
                            None
                        ),
                        (
                            'emcvnx_over_subscribed', 0.0, None, None, None,
                            None
                        ),
                        (
                            'emcvnx_total_subscribed_capacity',
                            10343115546165.248, None, None, None, None
                        )
                    ]
                )
            ]
        )
    ],
    'tiering': [
        (
            u'Pool 0', {
                'time_to_complete': (1814400, 2419200)
            }, [(0, u'Fast cache: N/A', [])]
        )
    ],
    'tieringtypes': [
        (
            u'Pool 0 Performance', {}, [
                (0, 'User capacity: 16.8 TiB', []),
                (
                    0, 'Consumed capacity: 9.41 TiB', [
                        (
                            'emcvnx_consumed_capacity', 10343118767390.72,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, 'Available capacity: 7.35 TiB', [
                        (
                            'emcvnx_avail_capacity', 8083858595512.32, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Percent subscribed: 56.13%', [
                        (
                            'emcvnx_perc_subscribed', 56.13, None, None, None,
                            None
                        )
                    ]
                )
            ]
        )
    ],
    'deduplication': [
        (
            u'Pool 0', {}, [
                (0, 'State: unknown', []), (0, 'Status: unknown', []),
                (0, 'Rate: unknown', []),
                (0, 'Efficiency savings: unknown', []),
                (0, 'Percent completed: unknown', []),
                (0, 'Remaining size: unknown', []),
                (0, 'Shared capacity: unknown', [])
            ]
        )
    ]
}
