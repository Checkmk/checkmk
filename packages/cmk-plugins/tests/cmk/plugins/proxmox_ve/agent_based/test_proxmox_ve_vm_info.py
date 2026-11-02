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

from cmk.agent_based.v2 import CheckResult, HostLabel, Metric, Result, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_info import (
    _check_proxmox_ve_vm_info_testable,
    host_label_function,
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

VM_DATA_WITH_UNKNOWN_LOCK = VM_DATA.model_copy(update={"lock": "some-future-lock"})


@pytest.mark.parametrize(
    "tags,expected_tag_labels",
    [
        ((), []),
        (
            ("prod", "web"),
            [HostLabel("cmk/pve/tag/prod", "yes"), HostLabel("cmk/pve/tag/web", "yes")],
        ),
    ],
)
def test_host_label_function_tags(
    tags: tuple[str, ...], expected_tag_labels: list[HostLabel]
) -> None:
    section = VM_DATA.model_copy(update={"tags": tags, "cluster": "cluster1"})
    labels = list(host_label_function(section))
    assert labels == [
        HostLabel("cmk/pve/entity", "vm"),
        HostLabel("cmk/pve/cluster", "cluster1"),
        *expected_tag_labels,
    ]


@pytest.mark.parametrize(
    "info_section_model", [VM_DATA, VM_DATA_WITH_LOCK, VM_DATA_WITH_UNKNOWN_LOCK]
)
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
                    "backup",
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
                    "suspended",
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
                "required_vm_status": None,
                "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
            },
            VM_DATA_WITH_UNKNOWN_LOCK,
            {
                "proxmox_ve_vm_info.lock_duration.133": (
                    1738678610.0,
                    "some-future-lock",
                )
            },
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu, Host: pve-dc4-001"),
                Result(state=State.OK, summary="Up since 2025-02-04 12:51:05"),
                Result(state=State.OK, summary="Uptime: 3 hours 25 minutes"),
                Metric("uptime", 12345.0),
                Result(state=State.OK, summary="Config lock: some-future-lock"),
                Result(
                    state=State.CRIT,
                    summary="Config lock duration: 1 hour 0 minutes (warn/crit at 15 minutes 0 seconds/30 minutes 0 seconds)",
                ),
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


@pytest.mark.parametrize(
    "section,value_store,expected_lock",
    [
        pytest.param(VM_DATA_WITH_LOCK, {}, "backup", id="first_sight"),
        pytest.param(
            VM_DATA_WITH_UNKNOWN_LOCK,
            {"proxmox_ve_vm_info.lock_duration.133": (1738678610.0, "backup")},
            "some-future-lock",
            id="lock_changed",
        ),
    ],
)
def test_check_proxmox_ve_vm_info_starts_tracking_lock(
    section: SectionVMInfo,
    value_store: MutableMapping[str, object],
    expected_lock: str,
) -> None:
    now = datetime.datetime(2025, 2, 4, 16, 16, 50, tzinfo=ZoneInfo("CET"))
    with time_machine.travel(now, tick=False):
        tuple(
            _check_proxmox_ve_vm_info_testable(
                {"required_vm_status": "", "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0))},
                section,
                value_store,
            )
        )
    assert value_store == {"proxmox_ve_vm_info.lock_duration.133": (now.timestamp(), expected_lock)}


def test_check_proxmox_ve_vm_info_restarts_tracking_after_lock_cleared() -> None:
    params: Params = {"required_vm_status": "", "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0))}
    value_store: MutableMapping[str, object] = {}
    first_lock = datetime.datetime(2025, 2, 4, 1, 0, 0, tzinfo=ZoneInfo("CET"))
    next_lock = first_lock + datetime.timedelta(days=1)
    for when, section in (
        (first_lock, VM_DATA_WITH_LOCK),
        (first_lock + datetime.timedelta(minutes=5), VM_DATA),
        (next_lock, VM_DATA_WITH_LOCK),
    ):
        with time_machine.travel(when, tick=False):
            tuple(_check_proxmox_ve_vm_info_testable(params, section, value_store))
    assert value_store == {
        "proxmox_ve_vm_info.lock_duration.133": (next_lock.timestamp(), "backup")
    }
