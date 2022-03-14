#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm

checkname = "esx_vsphere_vm"

parsed = parse_esx_vsphere_vm(
    [
        ["snapshot.rootSnapshotList", "732", "1594041788", "poweredOn", "FransTeil2"],
    ]
)

discovery = {
    "cpu": [],
    "datastores": [],
    "guest_tools": [],
    "heartbeat": [],
    "mem_usage": [],
    "mounted_devices": [],
    "name": [],
    "running_on": [],
    "snapshots": [(None, {})],
    "snapshots_summary": [(None, {})],
}

checks = {
    "snapshots": [
        (
            None,
            {"age": (86400, 172800), "age_oldest": (86400, 172800)},
            [
                (0, "Count: 1", []),
                (0, "Powered on: FransTeil2", []),
                (0, "Latest: FransTeil2 2020-07-06 15:23:08", []),
                (0, "", [("age", 54676, 86400.0, 172800.0, None, None)]),
                (0, "", [("age_oldest", 54676, 86400.0, 172800.0, None, None)]),
            ],
        )
    ],
}
