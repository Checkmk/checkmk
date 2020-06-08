#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = "netapp_api_volumes"

info = [
    ['volume 99efd228-e2d3-4d31-980e-470e19389806', 'size-total 3068834836480', 'node euedcnas1011',
     'files-total 31876696', 'vserver_name euedcnas1011', 'name vol_1011_root', 'state online',
     'size-available 2996744216576', 'files-used 63106', 'fcp_write_data 0', 'fcp_read_latency 0',
     'iscsi_write_latency 0', 'read_latency 641571331962', 'nfs_write_ops 0', 'fcp_read_ops 0',
     'fcp_read_data 0', 'cifs_write_ops 0', 'iscsi_read_latency 0', 'nfs_write_latency 0',
     'iscsi_read_ops 0', 'read_ops 1023923957', 'cifs_read_latency 0', 'nfs_read_latency 0',
     'iscsi_read_data 0', 'instance_name vol_1011_root', 'san_read_ops 0', 'san_read_data 0',
     'san_read_latency 0', 'write_data 1733658177396', 'cifs_write_data 0', 'iscsi_write_data 0',
     'san_write_latency 0', 'san_write_data 0', 'iscsi_write_ops 0', 'san_write_ops 0',
     'fcp_write_latency 0', 'fcp_write_ops 0', 'nfs_read_ops 0', 'read_data 6745251997344',
     'cifs_read_ops 0', 'write_latency 103955282923', 'cifs_read_data 0', 'nfs_read_data 0',
     'write_ops 539245772', 'nfs_write_data 0', 'cifs_write_latency 0'],
    ['volume 0bec3d74-a3ca-4269-be10-5bb890c5bfe2', 'size-total 3068834836480', 'node euedcnas1012',
     'files-total 31876696', 'vserver_name euedcnas1012', 'name vol_1012_root', 'state online',
     'size-available 3034830319616', 'files-used 62894', 'fcp_write_data 0', 'fcp_read_latency 0',
     'iscsi_write_latency 0', 'read_latency 492694300156', 'nfs_write_ops 0', 'fcp_read_ops 0',
     'fcp_read_data 0', 'cifs_write_ops 0', 'iscsi_read_latency 0', 'nfs_write_latency 0',
     'iscsi_read_ops 0', 'read_ops 339222081', 'cifs_read_latency 0', 'nfs_read_latency 0',
     'iscsi_read_data 0', 'instance_name vol_1012_root', 'san_read_ops 0', 'san_read_data 0',
     'san_read_latency 0', 'write_data 1512773163403', 'cifs_write_data 0', 'iscsi_write_data 0',
     'san_write_latency 0', 'san_write_data 0', 'iscsi_write_ops 0', 'san_write_ops 0',
     'fcp_write_latency 0', 'fcp_write_ops 0', 'nfs_read_ops 0', 'read_data 2064285089001',
     'cifs_read_ops 0', 'write_latency 36447123810', 'cifs_read_data 0', 'nfs_read_data 0',
     'write_ops 391736081', 'nfs_write_data 0', 'cifs_write_latency 0'],
    ['volume e585741f-5e66-4bb9-9d21-3966a28174af', 'size-total 161061273600', 'node euedcnas1012',
     'files-total 4669444', 'vserver_name euedcnas1710', 'name v_1710_a2mac1', 'msid 2155257036',
     'state broken', 'size-available 34452643840', 'files-used 329535', 'fcp_write_data 0',
     'fcp_read_latency 0', 'iscsi_write_latency 0', 'read_latency 5690194839', 'nfs_write_ops 0',
     'fcp_read_ops 0', 'fcp_read_data 0', 'cifs_write_ops 269223', 'iscsi_read_latency 0',
     'nfs_write_latency 0', 'iscsi_read_ops 0', 'read_ops 1046981', 'cifs_read_latency 5651491277',
     'nfs_read_latency 0', 'iscsi_read_data 0', 'instance_name v_1710_a2mac1', 'san_read_ops 0',
     'san_read_data 0', 'san_read_latency 0', 'write_data 21266276975',
     'cifs_write_data 20676268249', 'iscsi_write_data 0', 'san_write_latency 0', 'san_write_data 0',
     'iscsi_write_ops 0', 'san_write_ops 0', 'fcp_write_latency 0', 'fcp_write_ops 0',
     'nfs_read_ops 0', 'read_data 45020886427', 'cifs_read_ops 856082', 'write_latency 63998626',
     'cifs_read_data 44361557879', 'nfs_read_data 0', 'write_ops 291850', 'nfs_write_data 0',
     'cifs_write_latency 60204543'],
    ['volume 004379ad-59c3-443f-bc01-9dab2f12e54f', 'size-total 322122547200', 'node euedcnas1012',
     'files-total 9338875', 'vserver_name euedcnas1710', 'name v_1710_aspera', 'msid 2155257034',
     'state online', 'size-available 128706699264', 'files-used 3414', 'fcp_write_data 0',
     'fcp_read_latency 0', 'iscsi_write_latency 0', 'read_latency 8121797', 'nfs_write_ops 0',
     'fcp_read_ops 0', 'fcp_read_data 0', 'cifs_write_ops 0', 'iscsi_read_latency 0',
     'nfs_write_latency 0', 'iscsi_read_ops 0', 'read_ops 135861', 'cifs_read_latency 0',
     'nfs_read_latency 0', 'iscsi_read_data 0', 'instance_name v_1710_aspera', 'san_read_ops 0',
     'san_read_data 0', 'san_read_latency 0', 'write_data 640774', 'cifs_write_data 0',
     'iscsi_write_data 0', 'san_write_latency 0', 'san_write_data 0', 'iscsi_write_ops 0',
     'san_write_ops 0', 'fcp_write_latency 0', 'fcp_write_ops 0', 'nfs_read_ops 0',
     'read_data 70677732', 'cifs_read_ops 0', 'write_latency 342316', 'cifs_read_data 0',
     'nfs_read_data 0', 'write_ops 1954', 'nfs_write_data 0', 'cifs_write_latency 0'],
    ['volume 619e3283-7151-4f15-ad32-81e241613ecd', 'size-total 1099511627776', 'node euedcnas1012',
     'files-total 31876696', 'vserver_name euedcnas1710', 'name v_1710_data', 'msid 2155256942',
     'state online', 'size-available 1098808291328', 'files-used 315', 'fcp_write_data 0',
     'fcp_read_latency 0', 'iscsi_write_latency 0', 'read_latency 22911925', 'nfs_write_ops 0',
     'fcp_read_ops 0', 'fcp_read_data 0', 'cifs_write_ops 0', 'iscsi_read_latency 0',
     'nfs_write_latency 0', 'iscsi_read_ops 0', 'read_ops 137695', 'cifs_read_latency 13502252',
     'nfs_read_latency 0', 'iscsi_read_data 0', 'instance_name v_1710_data', 'san_read_ops 0',
     'san_read_data 0', 'san_read_latency 0', 'write_data 1363374', 'cifs_write_data 0',
     'iscsi_write_data 0', 'san_write_latency 0', 'san_write_data 0', 'iscsi_write_ops 0',
     'san_write_ops 0', 'fcp_write_latency 0', 'fcp_write_ops 0', 'nfs_read_ops 0',
     'read_data 808349225', 'cifs_read_ops 1642', 'write_latency 1096990',
     'cifs_read_data 736920818', 'nfs_read_data 0', 'write_ops 3864', 'nfs_write_data 0',
     'cifs_write_latency 0'],
]

discovery = {
    "": [
        ("euedcnas1011.vol_1011_root", {}),
        ("euedcnas1012.vol_1012_root", {}),
        ("euedcnas1710.v_1710_a2mac1", {}),
        ("euedcnas1710.v_1710_aspera", {}),
        ("euedcnas1710.v_1710_data", {}),
    ]
}

freeze_time = '2020-06-10 13:50:21'


def mock_util(*args):
    item_state = {}

    for item in ["euedcnas1011.vol_1011_root", "euedcnas1012.vol_1012_root",
                 "euedcnas1710.v_1710_a2mac1", "euedcnas1710.v_1710_aspera",
                 "euedcnas1710.v_1710_data"]:

        item_state['df.%s.delta' % item, None] = (1591789747, 0)
        item_state['df.%s.trend' % item, (1591797021.0, None)] = (1591789747, 0)

        for protocol in ["", "nfs", "cifs", "san", "fcp", "iscsi"]:
            for mode in ["read", "write", "other"]:
                for field in ["data", "ops", "latency"]:
                    key = "netapp_api_volumes.%s.%s" % (item, "_".join([protocol, mode, field]))
                    item_state[key, None] = (1591789747, 0)

    return item_state[args]


mock_item_state = {'': mock_util}

checks = {
    "": [
        (
            "euedcnas1011.vol_1011_root",
            {},
            [
                (
                    0,
                    '2.35% used (67.14 GB of 2.79 TB), trend: +45.21 GB / 24 hours, ',
                    [('fs_used', 68750.97265625, 2341335.171875, 2634002.068359375, 0,
                      2926668.96484375), ('fs_size', 2926668.96484375),
                     ('fs_used_percent', 2.349120227880658), ('growth', 816618.6468930437),
                     ('trend', 46290.73742521239, None, None, 0, 121944.54020182292),
                     ('inodes_used', 63106, None, None, 0.0, 31876696.0)],
                ),
            ],
        ),
        (
            "euedcnas1012.vol_1012_root",
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "trend_range": 24,
                "trend_perfdata": True,
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
            },
            [
                (
                    0,
                    '1.11% used (31.67 GB of 2.79 TB), trend: +21.32 GB / 24 hours, ',
                    [('fs_used', 32429.234375, 2341335.171875, 2634002.068359375, 0,
                      2926668.96484375), ('fs_size', 2926668.96484375),
                     ('fs_used_percent', 1.1080595299486269), ('growth', 385191.89579323615),
                     ('trend', 21834.93724313627, None, None, 0, 121944.54020182292),
                     ('inodes_used', 62894, 28689026.400000002, 30282861.2, 0.0, 31876696.0)],
                ),
            ],
        ),
        (
            "euedcnas1710.v_1710_a2mac1",
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "trend_range": 24,
                "trend_perfdata": True,
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
            },
            [
                (
                    1,
                    'Volume is broken',
                ),
            ],
        ),
        (
            "euedcnas1710.v_1710_aspera",
            {
                'levels': (10.0, 20.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'always',
                'show_reserved': False,
                'perfdata': ['', 'nfs', 'cifs', 'san', 'fcp', 'iscsi'],
                'magic': 0.8, 'trend_mb': (100, 200),
                'trend_perc': (5.0, 10.0),
                'trend_timeleft': (12, 6),
                'trend_showtimeleft': True
            },
            [
                (
                    2,
                    '60.04% used (180.13 of 300.00 GB), (warn/crit at 50.0%/60.0%), trend: +121.29 '
                    'GB / 24 hours - growing too fast (warn/crit at 100.00 MB/200.00 MB per 24.0 h)'
                    '(!!), growing too fast (warn/crit at 5.000%/10.000% per 24.0 h)(!!), time '
                    'left until disk full: 23 hours, Inodes Used: 0.04%, inodes available: 9.34 '
                    'M/99.96%, ',
                    [('fs_used', 184455.7265625, 153600.0, 184320.0, 0, 307200.0),
                     ('fs_size', 307200.0), ('fs_used_percent', 60.04418182373047),
                     ('growth', 2190950.615204839),
                     ('trend', 124195.93898073, 100.0, 200.0, 0, 12800.0),
                     ('trend_hoursleft', 23.719475746763944),
                     ('inodes_used', 3414, 8404987.5, 8871931.25, 0.0, 9338875.0),
                     ('nfs_read_data', 0.0), ('nfs_read_ops', 0.0), ('nfs_read_latency', 0.0),
                     ('nfs_write_data', 0.0), ('nfs_write_ops', 0.0), ('nfs_write_latency', 0.0),
                     ('cifs_read_data', 0.0), ('cifs_read_ops', 0.0), ('cifs_read_latency', 0.0),
                     ('cifs_write_data', 0.0), ('cifs_write_ops', 0.0), ('cifs_write_latency', 0.0),
                     ('san_read_data', 0.0), ('san_read_ops', 0.0), ('san_read_latency', 0.0),
                     ('san_write_data', 0.0), ('san_write_ops', 0.0), ('san_write_latency', 0.0),
                     ('fcp_read_data', 0.0), ('fcp_read_ops', 0.0), ('fcp_read_latency', 0.0),
                     ('fcp_write_data', 0.0), ('fcp_write_ops', 0.0), ('fcp_write_latency', 0.0),
                     ('iscsi_read_data', 0.0), ('iscsi_read_ops', 0.0), ('iscsi_read_latency', 0.0),
                     ('iscsi_write_data', 0.0), ('iscsi_write_ops', 0.0),
                     ('iscsi_write_latency', 0.0)],
                ),
            ],
        ),
        (
            "euedcnas1710.v_1710_data",
            {
                'levels': (10.0, 20.0),
                'magic_normsize': 20,
                'levels_low': (50.0, 60.0),
                'trend_range': 24,
                'trend_perfdata': True,
                'show_levels': 'onmagic',
                'inodes_levels': (10.0, 5.0),
                'show_inodes': 'always',
                'show_reserved': False,
                'perfdata': ['', 'nfs', 'cifs', 'san', 'fcp', 'iscsi'],
                'magic': 0.8, 'trend_mb': (100, 200),
                'trend_perc': (5.0, 10.0),
                'trend_timeleft': (12, 6),
                'trend_showtimeleft': True
            },
            [
                (
                    2,
                    '0.06% used (670.75 MB of 1.00 TB), (warn/crit at 59.04%/63.59%), trend: '
                    '+451.63 MB / 24 hours - growing too fast (warn/crit at 100.00 MB/200.00 MB '
                    'per 24.0 h)(!!), time left until disk full: more than a year, Inodes Used: '
                    '0.001%, inodes available: 31.88 M/100%, ',
                    [('fs_used', 670.75390625, 619051.0158057379, 666776.0140495448, 0, 1048576.0),
                     ('fs_size', 1048576.0), ('fs_used_percent', 0.06396807730197906),
                     ('growth', 7967.162152873247),
                     ('trend', 451.6255079968184, 100.0, 200.0, 0, 43690.666666666664),
                     ('trend_hoursleft', 55687.124533336086),
                     ('inodes_used', 315, 28689026.400000002, 30282861.2, 0.0, 31876696.0),
                     ('nfs_read_data', 0.0), ('nfs_read_ops', 0.0), ('nfs_read_latency', 0.0),
                     ('nfs_write_data', 0.0), ('nfs_write_ops', 0.0), ('nfs_write_latency', 0.0),
                     ('cifs_read_data', 101308.88342040143), ('cifs_read_ops', 0.22573549628814957),
                     ('cifs_read_latency', 8.223052375152253), ('cifs_write_data', 0.0),
                     ('cifs_write_ops', 0.0), ('cifs_write_latency', 0.0), ('san_read_data', 0.0),
                     ('san_read_ops', 0.0), ('san_read_latency', 0.0), ('san_write_data', 0.0),
                     ('san_write_ops', 0.0), ('san_write_latency', 0.0), ('fcp_read_data', 0.0),
                     ('fcp_read_ops', 0.0), ('fcp_read_latency', 0.0), ('fcp_write_data', 0.0),
                     ('fcp_write_ops', 0.0), ('fcp_write_latency', 0.0), ('iscsi_read_data', 0.0),
                     ('iscsi_read_ops', 0.0), ('iscsi_read_latency', 0.0),
                     ('iscsi_write_data', 0.0), ('iscsi_write_ops', 0.0),
                     ('iscsi_write_latency', 0.0)],
                ),
            ],
        ),
    ],
}
