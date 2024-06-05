#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.veeam_jobs import (
    check_veeam_jobs,
    inventory_veeam_jobs,
    parse_veeam_jobs,
)

STRING_TABLE = [
    ["VMware_Server", "Backup", "Stopped", "Success", "21.01.2019 00:10:22", "21.01.2019 00:29:12"],
    [
        "Lehrer_Rechner",
        "Backup",
        "Stopped",
        "Success",
        "23.07.2018 13:08:37",
        "23.07.2018 13:27:44",
    ],
    [
        "Windows_Admin_PC",
        "Backup",
        "Stopped",
        "Success",
        "20.01.2019 22:00:06",
        "20.01.2019 22:02:42",
    ],
    ["Lehrer Rechner"],
]


def test_discovery_veeam_jobs() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    assert inventory_veeam_jobs(section) == [
        ("VMware_Server", None),
        ("Lehrer_Rechner", None),
        ("Windows_Admin_PC", None),
        ("Lehrer Rechner", None),
    ]


def test_check_veeam_jobs() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    services = inventory_veeam_jobs(section)

    results = [(service[0], check_veeam_jobs(service[0], {}, section)) for service in services]
    assert results == [
        (
            "VMware_Server",
            (
                0,
                "State: Stopped, Result: Success, Creation time: 21.01.2019 00:10:22, End time: 21.01.2019 00:29:12, Type: Backup",
            ),
        ),
        (
            "Lehrer_Rechner",
            (
                0,
                "State: Stopped, Result: Success, Creation time: 23.07.2018 13:08:37, End time: 23.07.2018 13:27:44, Type: Backup",
            ),
        ),
        (
            "Windows_Admin_PC",
            (
                0,
                "State: Stopped, Result: Success, Creation time: 20.01.2019 22:00:06, End time: 20.01.2019 22:02:42, Type: Backup",
            ),
        ),
        ("Lehrer Rechner", None),
    ]
