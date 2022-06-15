#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'emcvnx_storage_pools'

parsed = {
    u'backup': {
        u'Disk Type': u'Mixed',
        u'Relocation Type': u'Scheduled',
        u'Performance_User Capacity (GBs)': u'4400.83',
        u"Deduplicated LUNs' Tiering Policy": u'Auto Tier',
        u'Compression Savings (GBs)': u'N/A',
        u'Raw Capacity (GBs)': u'20177.924',
        u'Capacity_Consumed Capacity (GBs)': u'9096.98',
        u'Efficiency Savings (Blocks)': u'N/A',
        u'Deduplication Status': u'OK(0x0)',
        u'Current Operation State': u'N/A',
        u'Deduplication Remaining Size (GBs)': u'N/A',
        u'Deduplication Percent Completed': u'-42',
        u'Performance_Data Targeted for Higher Tier (GBs)': u'0.00',
        u'Consumed Capacity (GBs)': u'13058.455',
        u'Current Operation Percent Completed': u'0',
        'tier_names': [u'Performance', u'Capacity'],
        u'Rebalance Percent Complete': u'N/A',
        u"Deduplicated LUNs' Initial Tier": u'Highest Available',
        u'Deduplication Remaining Size (Blocks)': u'N/A',
        u'Snapshot Subscribed Capacity (GBs)': u'0.000',
        u'FAST Cache': u'Disabled',
        u'Percent Full': u'84.763',
        u'User Capacity (GBs)': u'15405.781',
        u'Performance_Data Targeted Within Tier (GBs)': u'0.00',
        u'Deduplication Shared Capacity (Blocks)': u'N/A',
        u'Deduplication State': u'Idle (No Deduplicated LUNs)',
        u'Percent Full Threshold': u'80',
        u'Metadata Subscribed Capacity (GBs)': u'433.954',
        u'Raw Capacity (Blocks)': u'42316172978',
        u'Capacity_Data Targeted for Lower Tier (GBs)': u'0.00',
        u'Schedule Duration Remaining': u'None',
        u'Total Subscribed Capacity (Blocks)': u'27384514560',
        u'Data to Move Within Tiers (GBs)': u'0.00',
        u'State': u'Ready',
        u'Efficiency Savings (GBs)': u'N/A',
        u'LUN Allocation (GBs)': u'12624.000',
        u'Capacity_Raid Drive Count': u'8',
        u'Available Capacity (GBs)': u'2347.326',
        u'Data to Move Up (GBs)': u'17.03',
        u'Available Capacity (Blocks)': u'4922698752',
        u'Deduplication Shared Capacity (GBs)': u'N/A',
        u'Auto-Delete Pool Full High Watermark': u'95.00',
        u'Auto-Tiering': u'Scheduled',
        u'Auto-Delete Pool Full State': u'Idle',
        u'Auto-Delete Snapshot Space Used State': u'Idle',
        u'Compression Savings (Blocks)': u'N/A',
        u'LUN Allocation (Blocks)': u'26474446848',
        u'LUN Subscribed Capacity (GBs)': u'12624.000',
        u'LUNs':
        u'395, 328, 164, 70, 356, 80, 360, 330, 273, 62, 347, 267, 299, 263, 209, 264, 206, 89, 307, 364, 64, 371, 135, 323, 268, 315, 69, 332, 326, 376, 77, 394, 57, 261, 122, 271, 170, 266, 246, 272, 73, 167, 366, 179, 156, 381, 310, 344, 270, 86, 317, 75, 336, 117, 52, 107, 378, 240, 374, 112, 312, 291, 59, 253, 321, 68, 55, 274, 162, 385, 265, 95, 369, 359, 334, 386, 142, 358, 380, 128, 338, 319, 269, 66, 383, 32, 257, 275, 96, 27, 149, 102, 50',
        u'Metadata Subscribed Capacity (Blocks)': u'910067712',
        u'Capacity_Percent Subscribed': u'82.66%',
        u'Performance_Data Targeted for Lower Tier (GBs)': u'17.03',
        u'Performance_Raid Type': u'r_5',
        u'Oversubscribed by (GBs)': u'0.000',
        u'Deduplication Rate': u'Medium',
        u'Auto-Delete Pool Full Threshold Enabled': u'On',
        u'Snapshot Allocation (GBs)': u'0.000',
        u'Performance_Percent Subscribed': u'90.01%',
        u'Estimated Time to Complete': u'4 minutes',
        u'Capacity_Data Targeted for Higher Tier (GBs)': u'17.03',
        u'Total Subscribed Capacity (GBs)': u'13057.954',
        u'User Capacity (Blocks)': u'32308263936',
        u'Auto-Delete Snapshot Space Used Low Watermark': u'20.00',
        u'Status': u'OK(0x0)',
        u'Oversubscribed by (Blocks)': u'0',
        u'Pool ID': u'2',
        u'Relocation Rate': u'Medium',
        u'Auto-Delete Pool Full Low Watermark': u'85.00',
        u'Capacity_Data Targeted Within Tier (GBs)': u'0.00',
        u'Current Operation Status': u'N/A',
        u'Relocation Status': u'Inactive',
        u'Disks': u'',
        u'Performance_Raid Drive Count': u'5',
        u'Metadata Allocation (GBs)': u'434.455',
        u'Metadata Allocation (Blocks)': u'911118336',
        u'Data to Move Down (GBs)': u'17.03',
        u'Optimal Deduplicated LUN SP Owner': u'N/A',
        u'Snapshot Subscribed Capacity (Blocks)': u'0',
        u'LUN Subscribed Capacity (Blocks)': u'26474446848',
        u'Current Operation': u'None',
        u'Description': u'',
        u'Capacity_Raid Type': u'r_6',
        u'Performance_Consumed Capacity (GBs)': u'3960.97',
        u'Snapshot Allocation (Blocks)': u'0',
        u'Storage Pool ID': u'2',
        u'Performance_Available Capacity (GBs)': u'439.86',
        u'Raid Type': u'Mixed',
        u'Capacity_Available Capacity (GBs)': u'1907.97',
        u'Consumed Capacity (Blocks)': u'27385565184',
        u'Capacity_User Capacity (GBs)': u'11004.95',
        u'Data Movement Completed (GBs)': u'102.70',
        u'Auto-Delete Snapshot Space Used Threshold Enabled': u'Off',
        u'Auto-Delete Snapshot Space Used High Watermark': u'25.00',
        u'Percent Subscribed': u'84.760'
    }
}

discovery = {
    '': [(u'backup', {})],
    'tieringtypes': [(u'backup Capacity', {}), (u'backup Performance', {})],
    'tiering': [(u'backup', {})],
    'deduplication': [(u'backup', {})]
}

checks = {
    '': [
        (
            u'backup', {
                'percent_full': (70.0, 90.0)
            }, [
                (
                    0,
                    u'State: Ready, Status: OK(0x0), [Phys. capacity] User capacity: 15.0 TiB, Consumed capacity: 12.8 TiB, Available capacity: 2.29 TiB',
                    []
                ),
                (1, 'Percent full: 84.76% (warn/crit at 70 B/90 B)', []),
                (
                    0,
                    '[Virt. capacity] Percent subscribed: 84.76%, Oversubscribed by: 0 B, Total subscribed capacity: 12.8 TiB',
                    [
                        (
                            'emcvnx_consumed_capacity', 14021409290321.92,
                            None, None, None, None
                        ),
                        (
                            'emcvnx_avail_capacity', 2520422100762.624, None,
                            None, None, None
                        ),
                        ('emcvnx_perc_full', 84.763, None, None, None, None),
                        (
                            'emcvnx_perc_subscribed', 84.76, None, None, None,
                            None
                        ),
                        (
                            'emcvnx_over_subscribed', 0.0, None, None, None,
                            None
                        ),
                        (
                            'emcvnx_total_subscribed_capacity',
                            14020871345668.096, None, None, None, None
                        )
                    ]
                )
            ]
        )
    ],
    'tieringtypes': [
        (
            u'backup Capacity', {}, [
                (0, 'User capacity: 10.7 TiB', []),
                (
                    0, 'Consumed capacity: 8.88 TiB', [
                        (
                            'emcvnx_consumed_capacity', 9767807898091.52, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Available capacity: 1.86 TiB', [
                        (
                            'emcvnx_avail_capacity', 2048667187937.28, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Percent subscribed: 82.66%', [
                        (
                            'emcvnx_perc_subscribed', 82.66, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Move higher: 17.0 GiB', [
                        (
                            'emcvnx_targeted_higher', 18285823262.72, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Move lower: 0 B', [
                        ('emcvnx_targeted_lower', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Move within: 0 B',
                    [('emcvnx_targeted_within', 0.0, None, None, None, None)]
                )
            ]
        ),
        (
            u'backup Performance', {}, [
                (0, 'User capacity: 4.30 TiB', []),
                (
                    0, 'Consumed capacity: 3.87 TiB', [
                        (
                            'emcvnx_consumed_capacity', 4253059152609.28, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Available capacity: 440 GiB', [
                        (
                            'emcvnx_avail_capacity', 472296078704.64, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Percent subscribed: 90.01%', [
                        (
                            'emcvnx_perc_subscribed', 90.01, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Move higher: 0 B',
                    [('emcvnx_targeted_higher', 0.0, None, None, None, None)]
                ),
                (
                    0, 'Move lower: 17.0 GiB', [
                        (
                            'emcvnx_targeted_lower', 18285823262.72, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Move within: 0 B',
                    [('emcvnx_targeted_within', 0.0, None, None, None, None)]
                )
            ]
        )
    ],
    'tiering': [
        (
            u'backup', {
                'time_to_complete': (1814400, 2419200)
            }, [
                (0, u'Fast cache: Disabled', []),
                (0, u'Relocation status: Inactive', []),
                (0, u'Relocation rate: Medium', []),
                (
                    0, 'Move up: 17.0 GiB', [
                        (
                            'emcvnx_move_up', 18285823262.72, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Move down: 17.0 GiB', [
                        (
                            'emcvnx_move_down', 18285823262.72, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Move within: 0 B', [
                        ('emcvnx_move_within', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Movement completed: 103 GiB', [
                        (
                            'emcvnx_move_completed', 110273285324.8, None,
                            None, None, None
                        )
                    ]
                ), (0, u'Estimated time to complete: 4 minutes', []),
                (
                    0, 'Age: 4 minutes 0 seconds', [
                        (
                            'emcvnx_time_to_complete', 240, 1814400.0,
                            2419200.0, None, None
                        )
                    ]
                )
            ]
        )
    ],
    'deduplication': [
        (
            u'backup', {}, [
                (0, u'State: Idle (No Deduplicated LUNs)', []),
                (0, u'Status: OK', []), (0, u'Rate: Medium', []),
                (0, 'Efficiency savings: N/A', []),
                (
                    0, 'Percent completed: -42.00%', [
                        (
                            'emcvnx_dedupl_perc_completed', -42.0, None, None,
                            None, None
                        )
                    ]
                ), (0, 'Remaining size: N/A', []),
                (0, 'Shared capacity: N/A', [])
            ]
        )
    ]
}
