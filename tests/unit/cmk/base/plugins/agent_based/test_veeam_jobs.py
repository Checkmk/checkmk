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
    [  # based on customer agent output, this is the most common state
        "VMware_Server",
        "Backup",
        "Stopped",
        "Success",
        "21.01.2019 00:10:22",
        "21.01.2019 00:29:12",
    ],
    [  # based on customer agent output
        "warning_backup",
        "Backup",
        "Stopped",
        "Warning",
        "03.09.2020 15:45:50",
        "03.09.2020 16:44:39",
    ],
    [  # based on customer agent output
        "backup_sync_job",
        "BackupSync",
        "Working",
        "None",
        "20.07.2017 08:25:09",
        "20.07.2017 08:25:29",
    ],
    [  # based on customer agent output, happens if creation time/end time are empty
        "backup_stopped",
        "Backup",
        "Stopped",
        "None",
    ],
    [  # based on customer agent output
        "stopped_and_failed",
        "Backup",
        "Stopped",
        "Failed",
        "26.10.2013 23:13:13",
        "27.10.2013 00:51:17",
    ],
    [  # based on customer agent output
        "starting_and_failed",
        "Backup",
        "Starting",
        "Failed",
        "26.10.2013 23:13:13",
        "27.10.2013 00:51:17",
    ],
    ["Lehrer Rechner"],
    [  # made up to get 100% coverage of check,
        "backup_sync_idle",
        "BackupSync",
        "Idle",
        "None",
        "20.07.2017 08:25:09",
        "20.07.2017 08:25:29",
    ],
]


def test_discovery_veeam_jobs() -> None:
    section = parse_veeam_jobs(STRING_TABLE)
    assert inventory_veeam_jobs(section) == [
        ("VMware_Server", None),
        ("warning_backup", None),
        ("backup_sync_job", None),
        ("backup_stopped", None),
        ("stopped_and_failed", None),
        ("starting_and_failed", None),
        ("Lehrer Rechner", None),
        ("backup_sync_idle", None),
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
            "warning_backup",
            (
                1,
                "State: Stopped, Result: Warning, Creation time: 03.09.2020 15:45:50, End time: 03.09.2020 16:44:39, Type: Backup",
            ),
        ),
        ("backup_sync_job", (0, "Running since 20.07.2017 08:25:09 (current state is: Working)")),
        ("backup_stopped", None),
        (
            "stopped_and_failed",
            (
                2,
                "State: Stopped, Result: Failed, Creation time: 26.10.2013 23:13:13, End time: 27.10.2013 00:51:17, Type: Backup",
            ),
        ),
        (
            "starting_and_failed",
            (
                0,
                "Running since 26.10.2013 23:13:13 (current state is: Starting)",
            ),
        ),
        ("Lehrer Rechner", None),
        (
            "backup_sync_idle",
            (
                0,
                "State: Idle, Result: None, Creation time: 20.07.2017 08:25:09, End time: 20.07.2017 08:25:29, Type: BackupSync",
            ),
        ),
    ]
