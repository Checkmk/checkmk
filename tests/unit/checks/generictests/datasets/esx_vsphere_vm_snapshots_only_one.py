#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm

checkname = 'esx_vsphere_vm'

freeze_time = "2019-06-22 14:37"

parsed = parse_esx_vsphere_vm([
    ['snapshot.rootSnapshotList', '154', '1560322675', 'poweredOn', 'VM-Snapshot', '12.06.2019',
     '10:56', 'UTC+02:00'],
])

discovery = {
    'cpu': [],
    'datastores': [],
    'guest_tools': [],
    'heartbeat': [],
    'mem_usage': [],
    'mounted_devices': [],
    'name': [],
    'running_on': [],
    'snapshots': [(None, {})],
    'snapshots_summary': [(None, {})],
}

checks = {
    'snapshots': [
        (None, {'age_oldest': (30, 3600)}, [
            (0, 'Count: 1', []),
            (0, 'Powered on: VM-Snapshot 12.06.2019 10:56 UTC+02:00'),
            (0, 'Latest: VM-Snapshot 12.06.2019 10:56 UTC+02:00 2019-06-12 08:57:55', []),
            (2, 'Age of oldest: 10 d (warn/crit at 30.0 s/60 m)', [
                ('age_oldest', 891545.0, 30, 3600, None, None),
            ]),
        ]),
    ],
}
