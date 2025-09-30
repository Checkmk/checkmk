#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from collections.abc import Mapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_info as pvvi
from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.proxmox_ve.lib.vm_info import SectionVMInfo

VM_DATA = SectionVMInfo(
    vmid="133",
    node="pve-dc4-001",
    status="running",
    type="qemu",
    name="aq-test.lan.mathias-kettner.de",
    uptime=12345,
)

VM_DATA_WITH_LOCK = SectionVMInfo(
    vmid="133",
    node="pve-dc4-001",
    status="running",
    type="qemu",
    name="aq-test.lan.mathias-kettner.de",
    uptime=12345,
    lock="backup",
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
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, notice="Config lock: none"),
            ),
        ),
        (
            {"required_vm_status": ""},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, notice="Config lock: none"),
            ),
        ),
        (
            {"required_vm_status": None},
            VM_DATA_WITH_LOCK,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.CRIT, notice="Config lock: backup"),
            ),
        ),
        (
            {"required_vm_status": "idle"},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.WARN, summary="Status: running (required: idle)"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, notice="Config lock: none"),
            ),
        ),
    ],
)
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object], section: SectionVMInfo, expected_results: CheckResult
) -> None:
    with time_machine.travel(datetime.datetime(2025, 2, 4, 16, 16, 50, tzinfo=ZoneInfo("CET"))):
        results = tuple(pvvi.check_proxmox_ve_vm_info(params, section))
        assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvvi.__file__])
    pytest.main(["-vvsx", __file__])
