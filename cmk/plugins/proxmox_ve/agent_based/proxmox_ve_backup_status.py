#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from datetime import datetime, UTC
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class BackupData(TypedDict, total=False):
    """Define names and types for all _potential_ details of backups.
    These details are redundant and only partially available. The magic will be done in the check"""

    started_time: datetime
    total_duration: float
    bytes_written_size: int
    bytes_written_bandwidth: float
    transfer_size: int
    transfer_time: float
    archive_name: str
    archive_size: int
    upload_amount: int
    upload_total: int
    upload_time: float
    backup_amount: int
    backup_total: int
    backup_time: float
    error: str


Section = Mapping[str, BackupData]


def parse_proxmox_ve_vm_backup_status(
    string_table: StringTable,
) -> Section:
    result = BackupData()
    backup_data = json.loads(string_table[0][0])["last_backup"] or {}
    if "started_time" in backup_data:
        # the datetime object has timezone information
        result["started_time"] = datetime.strptime(
            backup_data["started_time"], "%Y-%m-%d %H:%M:%S%z"
        )
    if "total_duration" in backup_data:
        result["total_duration"] = int(backup_data["total_duration"])
    if "bytes_written_size" in backup_data:
        result["bytes_written_size"] = int(backup_data["bytes_written_size"])
    if "bytes_written_bandwidth" in backup_data:
        result["bytes_written_bandwidth"] = float(backup_data["bytes_written_bandwidth"])
    if "transfer_size" in backup_data:
        result["transfer_size"] = int(backup_data["transfer_size"])
    if "transfer_time" in backup_data:
        result["transfer_time"] = float(backup_data["transfer_time"])
    if "archive_name" in backup_data:
        result["archive_name"] = str(backup_data["archive_name"])
    if "archive_size" in backup_data:
        result["archive_size"] = int(backup_data["archive_size"])
    if "upload_amount" in backup_data:
        result["upload_amount"] = int(backup_data["upload_amount"])
    if "upload_total" in backup_data:
        result["upload_total"] = int(backup_data["upload_total"])
    if "upload_time" in backup_data:
        result["upload_time"] = float(backup_data["upload_time"])
    if "backup_amount" in backup_data:
        result["backup_amount"] = int(backup_data["backup_amount"])
    if "backup_total" in backup_data:
        result["backup_total"] = int(backup_data["backup_total"])
    if "backup_time" in backup_data:
        result["backup_time"] = float(backup_data["backup_time"])
    if "error" in backup_data:
        result["error"] = str(backup_data["error"])
    return {"last_backup": result}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_vm_backup_status(
    now: datetime,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    last_backup = section.get("last_backup")
    if not last_backup:
        yield (
            Result(state=State.CRIT, summary="No backup found")
            if params["age_levels_upper"][0] == "fixed"
            else Result(state=State.OK, summary="No backup found and none needed")  #
        )
        return
    if "error" in last_backup:
        yield Result(
            state=State.CRIT,
            summary=f"Last backup failed with message {last_backup['error']!r}",
        )
        return

    # Proxmox VE backup logs only provide time stamps without time zone so the special agent
    # explicitly converted them to utc
    started_time = last_backup.get("started_time")
    if started_time:
        yield from check_levels(
            value=(now - started_time.astimezone(UTC)).total_seconds(),
            levels_upper=params["age_levels_upper"],
            metric_name="age",
            render_func=render.timespan,
            label="Age",
            boundaries=(0, None),
        )
    yield Result(
        state=State.OK,
        summary=f"Server local start time: {started_time}",
    )

    yield from check_levels(
        value=last_backup["total_duration"],
        levels_upper=params["duration_levels_upper"],
        metric_name="backup_duration",
        render_func=render.timespan,
        label="Duration",
        boundaries=(0, None),
    )

    if "archive_name" in last_backup:
        yield Result(state=State.OK, summary=f"Name: {last_backup['archive_name']}")
    if "archive_size" in last_backup:
        yield Result(state=State.OK, summary=f"Size: {render.bytes(last_backup['archive_size'])}")

    if all(k in last_backup for k in ("bytes_written_size", "bytes_written_bandwidth")):
        bandwidth = last_backup["bytes_written_bandwidth"]
    elif all(k in last_backup for k in ("transfer_size", "transfer_time")):
        if last_backup["transfer_time"] == 0:
            return
        bandwidth = last_backup["transfer_size"] / last_backup["transfer_time"]
    elif all(k in last_backup for k in ("upload_amount", "upload_total", "upload_time")):
        if last_backup["upload_amount"] > 0:
            dedup_rate = last_backup["upload_total"] / last_backup["upload_amount"]
            yield Result(state=State.OK, summary=f"Dedup rate: {dedup_rate:.2f}")
        if last_backup["upload_time"] == 0:
            return
        bandwidth = last_backup["upload_amount"] / last_backup["upload_time"]
    elif all(k in last_backup for k in ("backup_amount", "backup_total", "backup_time")):
        if last_backup["backup_amount"] > 0:
            dedup_rate = last_backup["backup_total"] / last_backup["backup_amount"]
            yield Result(state=State.OK, summary=f"Dedup rate: {dedup_rate:.2f}")
        if last_backup["backup_time"] == 0:
            return
        bandwidth = last_backup["backup_amount"] / last_backup["backup_time"]
    else:
        return

    yield from check_levels(
        value=bandwidth,
        levels_lower=params["bandwidth_levels_lower"],
        metric_name="backup_avgspeed",
        render_func=render.iobandwidth,
        label="Bandwidth",
        boundaries=(0, None),
    )


agent_section_proxmox_ve_vm_backup_status = AgentSection(
    name="proxmox_ve_vm_backup_status",
    parse_function=parse_proxmox_ve_vm_backup_status,
)


def check_proxmox_ve_vm_backup_status_unpure(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """Because of datetime.now() this function is not testable.
    Test check_proxmox_ve_vm_backup_status() instead."""
    # the datetime object is always utc
    yield from check_proxmox_ve_vm_backup_status(datetime.now(tz=UTC), params, section)


check_plugin_proxmox_ve_vm_backup_status = CheckPlugin(
    name="proxmox_ve_vm_backup_status",
    service_name="Proxmox VE VM Backup Status",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_backup_status_unpure,
    check_ruleset_name="proxmox_ve_vm_backup_status",
    check_default_parameters={
        "age_levels_upper": (
            "fixed",
            (
                60 * 60 * 26,
                60 * 60 * 50,
            ),
        ),
        "duration_levels_upper": ("no_levels", None),
        "bandwidth_levels_lower": ("no_levels", None),
    },
)
