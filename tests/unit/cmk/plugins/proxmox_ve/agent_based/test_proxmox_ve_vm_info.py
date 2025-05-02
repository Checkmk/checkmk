#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from collections.abc import Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_info as pvvi
from cmk.agent_based.v2 import CheckResult, Result, State

VM_DATA = pvvi.parse_proxmox_ve_vm_info(
    [
        [
            json.dumps(
                {
                    "name": "aq-test.lan.mathias-kettner.de",
                    "node": "pve-dc4-001",
                    "status": "running",
                    "type": "qemu",
                    "vmid": "133",
                    "uptime": 12345,
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        (
            {},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 0 days 3 hours"),
            ),
        ),
        (
            {"required_vm_status": ""},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 0 days 3 hours"),
            ),
        ),
        (
            {"required_vm_status": None},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 0 days 3 hours"),
            ),
        ),
        (
            {"required_vm_status": "idle"},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.WARN, summary="Status: running (required: idle)"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 0 days 3 hours"),
            ),
        ),
    ],
)
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object], section: pvvi.Section, expected_results: CheckResult
) -> None:
    with time_machine.travel(datetime.datetime(2025, 2, 4, 16, 16, 50, tzinfo=ZoneInfo("CET"))):
        results = tuple(pvvi.check_proxmox_ve_vm_info(params, section))
        assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvvi.__file__])
    pytest.main(["-vvsx", __file__])
