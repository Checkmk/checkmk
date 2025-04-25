#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "esx_vsphere_objects"

info = [
    ["hostsystem", "10.1.1.112", "", "poweredOn"],
    ["hostsystem", "10.1.1.111", "", "poweredOn"],
    ["virtualmachine", "Grafana", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "Server", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "virt1-1.4.2", "10.1.1.112", "poweredOff"],
    ["virtualmachine", "Schulungs_ESXi", "10.1.1.112", "poweredOff"],
    ["template", "Dummy-Template", "1.2.3.4", "poweredOff"]
]

discovery = {
    "": [
        ("HostSystem 10.1.1.111", {}),
        ("HostSystem 10.1.1.112", {}),
        ("VM Grafana", {}),
        ("VM Schulungs_ESXi", {}),
        ("VM Server", {}),
        ("VM virt1-1.4.2", {}),
        ("Template Dummy-Template", {}),
    ],
    "count": [(None, {})],
}

checks = {
    "count": [
        (
            None,
            {"distribution": [{"hosts_count": 2, "state": 2, "vm_names": ["Grafana", "Server"]}]},
            [
                (0, "Templates: 1", [("templates", 1, None, None, None, None)]),
                (0, "Virtualmachines: 4", [("vms", 4, None, None, None, None)]),
                (0, "Hostsystems: 2", [("hosts", 2, None, None, None, None)]),
                (2, "VMs Grafana, Server are running on 1 host: 10.1.1.111", []),
            ],
        ),
        (
            None,
            {
                "distribution": [
                    {"hosts_count": 2, "state": 2, "vm_names": ["Grafana", "Schulungs_ESXi"]}
                ]
            },
            [
                (0, "Templates: 1", [("templates", 1, None, None, None, None)]),
                (0, "Virtualmachines: 4", [("vms", 4, None, None, None, None)]),
                (0, "Hostsystems: 2", [("hosts", 2, None, None, None, None)]),
            ],
        ),
        (
            None,
            {},
            [
                (0, "Templates: 1", [("templates", 1, None, None, None, None)]),
                (0, "Virtualmachines: 4", [("vms", 4, None, None, None, None)]),
                (0, "Hostsystems: 2", [("hosts", 2, None, None, None, None)]),
            ],
        ),
    ],
    "": [
        (
            "HostSystem 10.1.1.111",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", [])],
        ),
        (
            "HostSystem 10.1.1.112",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", [])],
        ),
        (
            "VM Grafana",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM Schulungs_ESXi",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.112]", [])],
        ),
        (
            "VM Server",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM virt1-1.4.2",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.112]", [])],
        ),
    ],
}
