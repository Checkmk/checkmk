#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime
from typing import Any, Mapping, TypedDict

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
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


def parse_proxmox_ve_vm_backup_status(string_table: StringTable) -> Section:
    result = BackupData()
    backup_data = json.loads(string_table[0][0])["last_backup"] or {}
    if "started_time" in backup_data:
        result["started_time"] = datetime.strptime(backup_data["started_time"], "%Y-%m-%d %H:%M:%S")
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
    """If conditions provided calculate and compare age of last backup agains provided
    levels and define result status accordingly
    >>> for result in check_proxmox_ve_vm_backup_status(
    ...     datetime.strptime("2020-12-07 21:28:02", '%Y-%m-%d %H:%M:%S'),
    ...     {'age_levels_upper': (93600, 180000)},
    ...     parse_proxmox_ve_vm_backup_status([[
    ...     '  {"last_backup": {'
    ...     '     "started_time": "2020-12-06 21:28:02",'
    ...     '     "total_duration": 140,'
    ...     '     "archive_name": "/tmp/vzdump-qemu-109-2020_12_06-21_28_02.vma.zst",'
    ...     '     "upload_amount": 10995116277,'
    ...     '     "upload_total": 1099511627776,'
    ...     '     "upload_time": 120'
    ...     '  }}'
    ...     ]])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Age: 1 day 0 hours')
    Metric('age', 86400.0, levels=(93600.0, 180000.0), boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Time: 2020-12-06 21:28:02')
    Result(state=<State.OK: 0>, summary='Duration: 2 minutes 20 seconds')
    Result(state=<State.OK: 0>, summary='Name: /tmp/vzdump-qemu-109-2020_12_06-21_28_02.vma.zst')
    Result(state=<State.OK: 0>, summary='Dedup rate: 100.00')
    Result(state=<State.OK: 0>, summary='Bandwidth: 91.6 MB/s')
    """
    age_levels_upper = params.get("age_levels_upper")
    last_backup = section.get("last_backup")
    if not last_backup:
        yield (
            Result(state=State.CRIT, summary="No backup found")
            if age_levels_upper
            else Result(state=State.OK, summary="No backup found and none needed")  #
        )
        return
    if "error" in last_backup:
        yield Result(
            state=State.CRIT,
            summary=f"Last backup failed with message {last_backup['error']!r}",
        )
        return

    # Proxmox VE backup logs only provide time stamps without time zone so we have to hope
    # the Proxmox VE node is located close to us
    started_time = last_backup.get("started_time")
    if started_time:
        yield from check_levels(
            value=(now - started_time).total_seconds(),
            levels_upper=age_levels_upper,
            metric_name="age",
            render_func=render.timespan,
            label="Age",
            boundaries=(0, None),
        )
    yield Result(
        state=State.OK,
        summary=f"Time: {started_time}",
    )
    yield Result(
        state=State.OK,
        summary=f"Duration: {render.timespan(last_backup['total_duration'])}",
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

    yield Result(state=State.OK, summary=f"Bandwidth: {render.iobandwidth(bandwidth)}")


register.agent_section(
    name="proxmox_ve_vm_backup_status",
    parse_function=parse_proxmox_ve_vm_backup_status,
)


def check_proxmox_ve_vm_backup_status_unpure(
    params: Mapping[str, Any], section: Section
) -> CheckResult:
    """Because of datetime.now() this function is not testable.
    Test check_proxmox_ve_vm_backup_status() instead."""
    yield from check_proxmox_ve_vm_backup_status(datetime.now(), params, section)


register.check_plugin(
    name="proxmox_ve_vm_backup_status",
    service_name="Proxmox VE VM Backup Status",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_backup_status_unpure,
    check_ruleset_name="proxmox_ve_vm_backup_status",
    check_default_parameters={
        "age_levels_upper": (
            60 * 60 * 26,
            60 * 60 * 50,
        )
    },
)
