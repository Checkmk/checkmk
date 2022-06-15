#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
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
                    1, '83.65% used (502 of 600 GiB)', [
                        (
                            'fs_used', 513958.37890625, 491551.34765625,
                            552995.2661132812, 0, 614439.1845703125
                        ),
                        ('fs_size', 614439.1845703125, None, None, None, None),
                        (
                            'fs_used_percent', 83.64674516415641, None, None,
                            None, None
                        )
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
                    1, '89.53% used (2.15 of 2.40 TiB)', [
                        (
                            'fs_used', 2253024.93359375, 2013308.47265625,
                            2264972.0317382812, 0, 2516635.5908203125
                        ),
                        (
                            'fs_size', 2516635.5908203125, None, None, None,
                            None
                        ),
                        (
                            'fs_used_percent', 89.52527500651625, None, None,
                            None, None
                        )
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
                    1, '83.38% used (542 of 650 GiB)', [
                        (
                            'fs_used', 555052.578125, 532529.6484375,
                            599095.8544921875, 0, 665662.060546875
                        ),
                        ('fs_size', 665662.060546875, None, None, None, None),
                        (
                            'fs_used_percent', 83.38353813780468, None, None,
                            None, None
                        )
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
                    0, '67.60% used (406 of 600 GiB)', [
                        (
                            'fs_used', 415366.30859375, 491551.34765625,
                            552995.2661132812, 0, 614439.1845703125
                        ),
                        ('fs_size', 614439.1845703125, None, None, None, None),
                        (
                            'fs_used_percent', 67.60088207659193, None, None,
                            None, None
                        )
                    ]
                )
            ]
        )
    ]
}
