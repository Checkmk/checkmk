#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import MutableMapping
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_value_store,
    HostLabel,
    HostLabelGenerator,
    IgnoreResultsError,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.uptime import check as check_uptime_seconds
from cmk.plugins.lib.uptime import Section as UptimeSection
from cmk.plugins.proxmox_ve.lib.vm_info import LockState, SectionVMInfo


class Params(TypedDict):
    required_vm_status: str
    lock_duration: NoLevelsT | FixedLevelsT[float]


class GetLockDurationError(IgnoreResultsError):
    """The exception raised by :func:`._get_lock_duration`.
    If unhandled, this exception will make the service go stale.
    """


def parse_proxmox_ve_vm_info(string_table: StringTable) -> SectionVMInfo:
    return SectionVMInfo.model_validate_json(string_table[0][0])


def host_label_function(section: SectionVMInfo) -> HostLabelGenerator:
    """
    Generate Proxmox VE VM host labels.
    Labels:
        cmk/pve/entity:<entity_type>:
            Shows that the object type is VM. It can be VM (qemu) or LXC (lxc).
    """
    yield HostLabel("cmk/pve/entity", "vm" if section.type == "qemu" else "LXC")
    if section.cluster:
        yield HostLabel("cmk/pve/cluster", section.cluster)


def discover_single(section: SectionVMInfo) -> DiscoveryResult:
    yield Service()


def _get_lock_duration(
    value_store: MutableMapping[str, Any],
    key: str,
    time: float,
    value: LockState,
) -> float | None:
    last_state = value_store.get(key)
    match last_state:
        case (
            float() | int() as last_time,
            LockState() as last_value,
        ):
            pass
        case _other:
            return None

    if time <= last_time:
        raise GetLockDurationError("No duration available (time anomaly detected)")

    if value is last_value:
        return time - last_time

    value_store[key] = (time, value)
    return None


def _check_lock_state_and_duration(
    value_store: MutableMapping[str, Any],
    lock_value: LockState,
    key: str,
    now: float,
    lock_duration_params: NoLevelsT | FixedLevelsT[float],
) -> CheckResult:
    lock_duration = _get_lock_duration(
        value_store=value_store,
        key=key,
        time=now,
        value=lock_value,
    )

    yield Result(
        state=State.OK,
        summary=f"Config lock: {lock_value.value}",
    )

    if lock_duration is None or lock_duration_params[0] == "no_levels":
        return

    yield from check_levels(
        value=lock_duration,
        levels_upper=lock_duration_params,
        render_func=render.timespan,
        label="Config lock duration",
        notice_only=True,
    )


def _check_proxmox_ve_vm_info_testable(
    params: Params, section: SectionVMInfo, value_store: MutableMapping[str, Any]
) -> CheckResult:
    yield Result(state=State.OK, summary=f"VM ID: {section.vmid}")

    vm_status = section.status.lower() if section.status else "n/a"
    req_vm_status = (params.get("required_vm_status") or "").lower()
    yield Result(
        state=State.OK if not req_vm_status or vm_status == req_vm_status else State.WARN,
        summary=f"Status: {vm_status}%s" % (req_vm_status and f" (required: {req_vm_status})"),
    )

    yield Result(state=State.OK, summary=f"Type: {section.type}, Host: {section.node}")

    yield from check_uptime_seconds(
        params={},
        section=UptimeSection(uptime_sec=section.uptime, message=None),
    )

    if not section.lock:
        yield Result(
            state=State.OK,
            notice="Config lock: none",
        )
        return

    yield from _check_lock_state_and_duration(
        value_store=value_store,
        lock_value=section.lock,
        key=f"proxmox_ve_vm_info.lock_duration.{section.vmid}",
        now=time.time(),
        lock_duration_params=params["lock_duration"],
    )


def check_proxmox_ve_vm_info(
    params: Params,
    section: SectionVMInfo,
) -> CheckResult:
    yield from _check_proxmox_ve_vm_info_testable(
        params=params,
        section=section,
        value_store=get_value_store(),
    )


agent_section_proxmox_ve_vm_info = AgentSection(
    name="proxmox_ve_vm_info",
    parse_function=parse_proxmox_ve_vm_info,
    host_label_function=host_label_function,
)

check_plugin_proxmox_ve_vm_info = CheckPlugin(
    name="proxmox_ve_vm_info",
    service_name="Proxmox VE VM Info",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_info,
    check_ruleset_name="proxmox_ve_vm_info",
    check_default_parameters={
        "required_vm_status": "",
        "lock_duration": ("fixed", (15 * 60.0, 30 * 60.0)),
    },
)
