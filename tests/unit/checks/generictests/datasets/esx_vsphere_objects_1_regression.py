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
    ["virtualmachine", "WindowsXP", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "win2003", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "Server", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "virt1-1.4.2", "10.1.1.112", "poweredOff"],
    ["virtualmachine", "XEN-SRV01", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "NetAppCluster_2", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "Windows", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "NetAppCluster_1", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "jiratest", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "jiratest-backupclone", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "Windows", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "bi-srv01", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "ORA-SRV01", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "virt1-1.3.20", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "ORA-SRV02", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "win2016rechner", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "NetApp-SIM-A", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "Debian", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "VMware", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "Lehrerrechner", "10.1.1.111", "poweredOff"],
    ["virtualmachine", "Windows10", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "aq-test", "10.1.1.111", "poweredOn"],
    ["virtualmachine", "virt1-", "10.1.1.112", "poweredOn"],
    ["virtualmachine", "Schulungs_ESXi", "10.1.1.112", "poweredOff"],
    ["virtualmachine", "virt1-", "10.1.1.112", "poweredOn"],
]

discovery = {
    "": [
        ("HostSystem 10.1.1.111", {}),
        ("HostSystem 10.1.1.112", {}),
        ("VM Debian", {}),
        ("VM Grafana", {}),
        ("VM Lehrerrechner", {}),
        ("VM NetApp-SIM-A", {}),
        ("VM NetAppCluster_1", {}),
        ("VM NetAppCluster_2", {}),
        ("VM ORA-SRV01", {}),
        ("VM ORA-SRV02", {}),
        ("VM Schulungs_ESXi", {}),
        ("VM Server", {}),
        ("VM VMware", {}),
        ("VM Windows", {}),
        ("VM Windows10", {}),
        ("VM WindowsXP", {}),
        ("VM XEN-SRV01", {}),
        ("VM aq-test", {}),
        ("VM bi-srv01", {}),
        ("VM jiratest", {}),
        ("VM jiratest-backupclone", {}),
        ("VM virt1-", {}),
        ("VM virt1-1.3.20", {}),
        ("VM virt1-1.4.2", {}),
        ("VM win2003", {}),
        ("VM win2016rechner", {}),
    ],
    "count": [(None, {})],
}

checks = {
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
            "VM Debian",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM Grafana",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM Lehrerrechner",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM NetApp-SIM-A",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM NetAppCluster_1",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM NetAppCluster_2",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM ORA-SRV01",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM ORA-SRV02",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
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
            "VM Server",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM VMware",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM Windows",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM Windows",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM Windows10",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM WindowsXP",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM XEN-SRV01",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM aq-test",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM bi-srv01",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM jiratest",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM jiratest-backupclone",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM virt1-",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.112]", [])],
        ),
        (
            "VM virt1-",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.112]", [])],
        ),
        (
            "VM virt1-1.3.20",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.111]", [])],
        ),
        (
            "VM virt1-1.4.2",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(1, "power state: poweredOff", []), (0, "defined on [10.1.1.112]", [])],
        ),
        (
            "VM win2003",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
        (
            "VM win2016rechner",
            {"states": {"unknown": 3, "poweredOn": 0, "poweredOff": 1, "suspended": 1}},
            [(0, "power state: poweredOn", []), (0, "running on [10.1.1.111]", [])],
        ),
    ],
    "count": [
        (
            None,
            {},
            [
                (0, "Virtualmachines: 24", [("vms", 24, None, None, None, None)]),
                (0, "Hostsystems: 2", [("hosts", 2, None, None, None, None)]),
            ],
        )
    ],
}
