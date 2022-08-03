#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore
checkname = 'netapp_api_luns'

info = [
    [
        'lun /vol/iscsi_crm_dblogs/crm_dblogs_lu01', 'read-only false',
        'size 644286182400', 'vserver ISCSI_CRM', 'size-used 538924421120',
        'online true', 'volume iscsi_crm_dblogs'
    ],
    [
        'lun /vol/iscsi_crm_dbprod/crm_dbprod_lu01', 'read-only false',
        'size 2638883681280', 'vserver ISCSI_CRM', 'size-used 2362467872768',
        'online true', 'volume iscsi_crm_dbprod'
    ],
    [
        'lun /vol/iscsi_crm_dbtemp/crm_dbtemp_lu01', 'read-only false',
        'size 697997260800', 'vserver ISCSI_CRM', 'size-used 582014812160',
        'online true', 'volume iscsi_crm_dbtemp'
    ],
    [
        'lun /vol/iscsi_nice_db/nice_db_lun', 'read-only false',
        'size 644286182400', 'vserver ISCSI_NICE_NOVO',
        'size-used 435543142400', 'online true', 'volume iscsi_nice_db'
    ]
]

discovery = {
    '': [
        ('crm_dblogs_lu01', {}), ('crm_dbprod_lu01', {}),
        ('crm_dbtemp_lu01', {}), ('nice_db_lun', {})
    ]
}

checks = {
    '': [
        (
            'crm_dblogs_lu01', {
                'levels': (80.0, 90.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'read_only': False
            }, [
                (
                    1, 'Used: 83.65% - 502 GiB of 600 GiB (warn/crit at 80.00%/90.00% used)', [
                        (
                            'fs_used', 513958.37890625, 491551.34765625,
                            552995.2661132812, 0, None
                        ), ('fs_free', 100480.8056640625, None, None, 0, None),
                        (
                            'fs_used_percent', 83.64674516415641, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 614439.1845703125, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'crm_dbprod_lu01', {
                'levels': (80.0, 90.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'read_only': False
            }, [
                (
                    1, 'Used: 89.53% - 2.15 TiB of 2.40 TiB (warn/crit at 80.00%/90.00% used)', [
                        (
                            'fs_used', 2253024.93359375, 2013308.47265625,
                            2264972.0317382812, 0, None
                        ), ('fs_free', 263610.6572265625, None, None, 0, None),
                        (
                            'fs_used_percent', 89.52527500651625, 80.0, 90.0, 0.0, 100.0
                        ),
                        ('fs_size', 2516635.5908203125, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'crm_dbtemp_lu01', {
                'levels': (80.0, 90.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'read_only': False
            }, [
                (
                    1, 'Used: 83.38% - 542 GiB of 650 GiB (warn/crit at 80.00%/90.00% used)', [
                        (
                            'fs_used', 555052.578125, 532529.6484375,
                            599095.8544921875, 0, None
                        ), ('fs_free', 110609.482421875, None, None, 0, None),
                        (
                            'fs_used_percent', 83.38353813780468, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 665662.060546875, None, None, 0, None)
                    ]
                )
            ]
        ),
        (
            'nice_db_lun', {
                'levels': (80.0, 90.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'read_only': False
            }, [
                (
                    0, 'Used: 67.60% - 406 GiB of 600 GiB', [
                        (
                            'fs_used', 415366.30859375, 491551.34765625,
                            552995.2661132812, 0, None
                        ), ('fs_free', 199072.8759765625, None, None, 0, None),
                        (
                            'fs_used_percent', 67.60088207659193, 80.0, 90.0, 0.0, 100.0
                        ), ('fs_size', 614439.1845703125, None, None, 0, None)
                    ]
                )
            ]
        )
    ]
}
