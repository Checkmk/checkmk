#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ad_replication'

freeze_time = '2015-07-12 00:00:00'

info = [
    [
        u'showrepl_COLUMNS,Destination', u'DSA', u'Site,Destination', u'DSA,Naming',
        u'Context,Source', u'DSA', u'Site,Source', u'DSA,Transport', u'Type,Number', u'of',
        u'Failures,Last', u'Failure', u'Time,Last', u'Success', u'Time,Last', u'Failure', u'Status'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        u'09:15:37,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        u'09:18:37,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        u'09:18:37,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        u'09:18:38,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        u'08:48:03,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        u'08:48:03,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        u'08:48:03,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"CN=Schema,CN=Configuration,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        u'08:48:03,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS008,RPC,0,0,2015-07-07',
        u'09:18:52,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS055,RPC,0,0,2015-07-07',
        u'09:18:55,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS003,RPC,0,0,2015-07-07',
        u'09:19:00,0'
    ],
    [
        u'showrepl_INFO,HAM,HSHPI220,"DC=network,DC=internal",HAM,SADS015,RPC,0,0,2015-07-07',
        u'09:19:01,0'
    ], [u'showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS003,RPC,0,0,2015-07-07', u'08:48:03,0'],
    [u'showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS055,RPC,0,0,2015-07-07', u'08:48:03,0'],
    [u'showrepl_INFO,HAM,HSHPI220,DC=internal,HAM,SADS008,RPC,0,0,2015-07-07', u'08:48:03,0']
]

discovery = {
    '': [(u'HAM/SADS003', 'ad_replication_default_params'),
         (u'HAM/SADS008', 'ad_replication_default_params'),
         (u'HAM/SADS015', 'ad_replication_default_params'),
         (u'HAM/SADS055', 'ad_replication_default_params')]
}

checks = {
    '': [
        (u'HAM/SADS003', (15, 20), [(0, 'All replications are OK.', [])]),
        (u'HAM/SADS008', (15, 20), [(0, 'All replications are OK.', [])]),
        (u'HAM/SADS015', (-1, 2),
         [(1, 'Replications with failures: 3, Total failures: 0', []),
          (0,
           u'\nHAM/SADS015 replication of context "CN=Configuration;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 16 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)\nHAM/SADS015 replication of context "CN=Schema;CN=Configuration;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 17 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)\nHAM/SADS015 replication of context "DC=network;DC=internal" reached  the threshold of maximum failures (-1) (Last success: 4 days 16 hours ago, Last failure: unknown, Num failures: 0, Status: 0)(!)',
           [])]), (u'HAM/SADS055', (15, 20), [(0, 'All replications are OK.', [])]),
        (u'HAM/SADS015', (15, 20), [(0, 'All replications are OK.', [])])
    ]
}
