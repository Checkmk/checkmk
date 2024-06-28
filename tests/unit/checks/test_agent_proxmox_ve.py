#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import SpecialAgent

from cmk.special_agents.agent_proxmox_ve import BackupTask


@pytest.mark.parametrize(
    ["params", "expected_result"],
    [
        pytest.param(
            {
                "username": "user",
                "password": ("password", "passwd"),
                "port": "443",
                "no-cert-check": True,
                "timeout": "30",
                "log-cutoff-weeks": "4",
            },
            [
                "-u",
                "user",
                "-p",
                "passwd",
                "--port",
                "443",
                "--no-cert-check",
                "--timeout",
                "30",
                "--log-cutoff-weeks",
                "4",
                "testhost",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "username": "user",
                "password": ("store", "passwd"),
                "timeout": "40",
            },
            [
                "-u",
                "user",
                "-p",
                ("store", "passwd", "%s"),
                "--timeout",
                "40",
                "testhost",
            ],
            id="password_from_store",
        ),
    ],
)
def test_agent_proxmox_ve_arguments(
    params: Mapping[str, Any],
    expected_result: Sequence[Any],
) -> None:
    assert (
        SpecialAgent("agent_proxmox_ve").argument_func(
            params,
            "testhost",
            "1.2.3.4",
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "log, expected_backup_amount, expected_backup_total, expected_backup_time",
    [
        pytest.param(
            "INFO: root.pxar: had to backup 962.93 MiB of 5.444 GiB (compressed 200.638 MiB) in 37.10s",
            1009705288,
            5845450490,
            37.1,
            id="old log format",
        ),
        pytest.param(
            "INFO: root.pxar: had to backup 1004.756 MiB of 5.434 GiB (compressed 221.297 MiB) in 58.86 s (average 17.07 MiB/s)",
            1053563027,
            5834713072,
            58.86,
            id="new log format",
        ),
    ],
)
def test_parsing_backuped_logs(
    log: str, expected_backup_amount: int, expected_backup_total: int, expected_backup_time: int
) -> None:
    backup_task = BackupTask(
        {},
        [
            {"n": 1, "t": "INFO: Starting Backup of VM 1"},
            {"n": 2, "t": "INFO: Backup started at 2024-07-02 01:00:00"},
            {"n": 3, "t": log},
            {"n": 4, "t": "INFO: Finished Backup of VM 1 (01:05:00)"},
        ],
        strict=True,
        dump_erroneous_logs=False,
    )

    assert backup_task.backup_data["1"]["backup_amount"] == expected_backup_amount
    assert backup_task.backup_data["1"]["backup_total"] == expected_backup_total
    assert backup_task.backup_data["1"]["backup_time"] == expected_backup_time
