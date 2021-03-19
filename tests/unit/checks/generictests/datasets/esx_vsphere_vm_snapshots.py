#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm

checkname = 'esx_vsphere_vm'

parsed = parse_esx_vsphere_vm([[
    'snapshot.rootSnapshotList', '1', '1363596734', 'poweredOff',
    '20130318_105600_snapshot_LinuxI|2', '1413977827', 'poweredOn', 'LinuxI', 'Testsnapshot'
]])

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
    'snapshots': [(None, {}, [
        (0, 'Count: 2', []),
        (0, 'Powered on: LinuxI Testsnapshot', []),
        (0, 'Latest: LinuxI Testsnapshot 2014-10-22 13:37:07', []),
        (0, 'Oldest: 20130318_105600_snapshot_LinuxI 2013-03-18 09:52:14', []),
    ]),]
}
