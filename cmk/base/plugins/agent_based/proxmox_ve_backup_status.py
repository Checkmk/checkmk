#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, TypedDict
from datetime import datetime
import json

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    Result,
    Service,
    State,
    check_levels,
    render,
)

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    Parameters,
    CheckResult,
    DiscoveryResult,
    StringTable,
)


class BackupData(TypedDict, total=False):
    archive_name: str
    archive_size: int
    transfer_size: int
    started_time: datetime
    transfer_time: float
    error: str


Section = Mapping[str, BackupData]


def parse_proxmox_ve_vm_backup_status(string_table: StringTable) -> Section:
    result = BackupData()
    backup_data = json.loads(string_table[0][0])['last_backup']
    if 'archive_name' in backup_data:
        result['archive_name'] = str(backup_data['archive_name'])
    if 'archive_size' in backup_data:
        result['archive_size'] = int(backup_data['archive_size'])
    if 'transfer_size' in backup_data:
        result['transfer_size'] = int(backup_data['transfer_size'])
    if 'started_time' in backup_data:
        result['started_time'] = datetime.strptime(backup_data['started_time'], "%Y-%m-%d %H:%M:%S")
    if 'transfer_time' in backup_data:
        result['transfer_time'] = int(backup_data['transfer_time'])
    if 'error' in backup_data:
        result['error'] = str(backup_data['error'])
    return {'last_backup': result}


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_vm_backup_status(
    now: datetime,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """If conditions provided calculate and compare age of last backup agains provided
    levels and define result status accordingly
    >>> for result in check_proxmox_ve_vm_backup_status(
    ...     datetime.strptime("2020-12-07 21:28:02", '%Y-%m-%d %H:%M:%S'),
    ...     {'age_levels_upper': (93600, 180000)},
    ...     parse_proxmox_ve_vm_backup_status([[
    ...       '{"last_backup": {'
    ...       '  "archive_name": "/some/where/vzdump-qemu-109-2020_12_06-21_28_02.vma.zst",'
    ...       '  "archive_size": 1099511627776,'
    ...       '  "started_time": "2020-12-06 21:28:02",'
    ...       '  "transfer_time": 100}}']])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Age: 1 day 0 hours')
    Metric('age', 86400.0, levels=(93600.0, 180000.0))
    Result(state=<State.OK: 0>, summary='Time: 2020-12-06 21:28:02')
    Result(state=<State.OK: 0>, summary='Size: 1.00 TiB')
    Result(state=<State.OK: 0>, summary='Bandwidth: 11.0 GB/s')
    """
    age_levels_upper = params.get("age_levels_upper")
    last_backup = section.get("last_backup")
    if not last_backup:
        yield (Result(state=State.CRIT, summary="No backup found") if age_levels_upper else  #
               Result(state=State.OK, summary="No backup found and none needed"))
        return
    if "error" in last_backup:
        yield Result(
            state=State.CRIT,
            summary=f"Last backup failed with message {last_backup['error']!r}",
        )
        return

    # Proxmox VE logs only provide time stamps w/o time zone so we have to hope the Proxmox VE node
    # is located close to us
    started_time = last_backup.get("started_time")
    if started_time:
        yield from check_levels(
            value=(now - started_time).total_seconds(),
            levels_upper=age_levels_upper,
            metric_name="age",
            render_func=render.timespan,
            label="Age",
        )
    yield Result(state=State.OK, summary=f"Time: {last_backup.get('started_time')}")
    yield Result(state=State.OK, summary=f"Size: {render.bytes(last_backup['archive_size'])}")

    transfer_size = last_backup.get("transfer_size", last_backup.get("archive_size", 0))
    yield Result(
        state=State.OK,
        summary=f"Bandwidth: {render.iobandwidth(transfer_size / last_backup['transfer_time'])}",
    )


register.agent_section(
    name="proxmox_ve_vm_backup_status",
    parse_function=parse_proxmox_ve_vm_backup_status,
)


def check_proxmox_ve_vm_backup_status_unpure(params: Parameters, section: Section) -> CheckResult:
    """Because of datetime.now() this function is not testable.
    Test check_proxmox_ve_vm_backup_status() instead."""
    yield from check_proxmox_ve_vm_backup_status(datetime.now(), params, section)


register.check_plugin(
    name="proxmox_ve_vm_backup_status",
    service_name="Proxmox VE VM Backup Status",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_backup_status_unpure,
    check_ruleset_name="proxmox_ve_vm_backup_status",
    check_default_parameters={"age_levels_upper": (
        60 * 60 * 26,
        60 * 60 * 50,
    )},
)
