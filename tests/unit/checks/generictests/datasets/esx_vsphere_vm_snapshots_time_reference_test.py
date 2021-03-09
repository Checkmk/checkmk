#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

checkname = 'esx_vsphere_vm'

info = [
    [u'snapshot.rootSnapshotList', u'732', u'1594041788', u'poweredOn', u'FransTeil2'],
    [u'time_reference', u'1594096464'],
]

discovery = {
    u'cpu': [],
    u'datastores': [],
    u'guest_tools': [],
    u'heartbeat': [],
    u'mem_usage': [],
    u'mounted_devices': [],
    u'name': [],
    u'running_on': [],
    u'snapshots': [(None, {})]
}

checks = {
    'snapshots': [(
        None,
        {
            'age': (86400, 172800),
            'age_oldest': (86400, 172800)
        },
        [
            (0, u'Count: 1', []),
            (0, u'Powered on: FransTeil2', []),
            (0, u'Latest: FransTeil2 2020-07-06 15:23:08', []),
            (0, u'', [(u'age', 54676, 86400.0, 172800.0, None, None)]),
            (0, u'', [(u'age_oldest', 54676, 86400.0, 172800.0, None, None)]),
        ],
    )],
}
