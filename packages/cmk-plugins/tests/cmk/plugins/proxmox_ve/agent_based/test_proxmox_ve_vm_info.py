#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import json
from collections.abc import MutableMapping
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_info import (
    _check_proxmox_ve_vm_info_testable,
    Params,
    parse_proxmox_ve_vm_info,
)
from cmk.plugins.proxmox_ve.lib.vm_info import LockState, SectionVMInfo

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
    lock=LockState.BACKUP,
)


@pytest.mark.parametrize("info_section_model", [VM_DATA, VM_DATA_WITH_LOCK])
def test_check_proxmox_ve_vm_info_parse_function(info_section_model: SectionVMInfo) -> None:
    assert (
        parse_proxmox_ve_vm_info([[json.dumps(info_section_model.model_dump(mode="json"))]])
        == info_section_model
    )


@pytest.mark.parametrize(
    "params,section,value_store,expected_results",
    [
        (
            {
                "lock_duration": ("no_levels", None),
            },
            VM_DATA,
            {},
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
            {
                "required_vm_status": "",
                "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
            },
            VM_DATA,
            {},
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
            {
                "required_vm_status": None,
                "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
            },
            VM_DATA_WITH_LOCK,
            {
                "proxmox_ve_vm_info.lock_duration.133": (
                    1738678610.0,
                    LockState.BACKUP,
                )
            },
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, summary="Config lock: backup"),
                Result(
                    state=State.CRIT,
                    summary="Config lock duration: 1 hour 0 minutes (warn/crit at 15 minutes 0 seconds/30 minutes 0 seconds)",
                ),
            ),
        ),
        (
            {
                "required_vm_status": None,
                "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
            },
            VM_DATA_WITH_LOCK,
            {
                "proxmox_ve_vm_info.lock_duration.133": (
                    1738678610.0,
                    LockState.SUSPENDED,
                )
            },
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, summary="Config lock: backup"),
            ),
        ),
        (
            {
                "required_vm_status": "idle",
                "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
            },
            VM_DATA,
            {},
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
    params: Params,
    section: SectionVMInfo,
    value_store: MutableMapping[str, object],
    expected_results: CheckResult,
) -> None:
    with time_machine.travel(datetime.datetime(2025, 2, 4, 16, 16, 50, tzinfo=ZoneInfo("CET"))):
        results = tuple(
            _check_proxmox_ve_vm_info_testable(
                params,
                section,
                value_store,
            )
        )
        assert results == expected_results
