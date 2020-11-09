#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<aix_diskiod>>>
# hdisk3 0.9 237.0 9.1 1337054478 1628926522
# hdisk5 0.9 237.1 8.8 1333731705 1633897629
# hdisk7 0.9 256.2 10.1 1537047014 1669194644
# hdisk6 0.9 236.6 9.1 1334163361 1626627852
# hdisk2 0.9 237.6 9.1 1334458233 1639383130
# hdisk9 0.8 239.4 9.3 1337740029 1658392394
# hdisk8 0.9 238.3 8.9 1332262996 1649741796
# hdisk4 0.9 237.4 8.8 1332426157 1638419364
# hdisk13 0.5 238.1 8.3 394246756 2585031872
# hdisk11 0.5 238.3 8.3 397601918 2584807275

# Columns means:
# 1. device
# 2. % tm_act
# 3. Kbps
# 4. tps
# 5. Kb_read    -> Kilobytes read since system boot
# 6. Kb_wrtn    -> Kilobytes written since system boot

import time
from typing import Mapping, Optional
from .agent_based_api.v1 import (
    get_value_store,
    get_rate,
    IgnoreResultsError,
    register,
    type_defs,
)
from .utils import diskstat


def parse_aix_diskiod(string_table: type_defs.StringTable) -> Optional[diskstat.Section]:

    section = {}

    for device, _tm_act, _kbps, _tps, kb_read, kb_written in string_table:
        try:
            section[device] = {
                'read_throughput': int(kb_read) * 1024,
                'write_throughput': int(kb_written) * 1024,
            }
        except ValueError:
            continue

    return section if section else None


register.agent_section(
    name="aix_diskiod",
    parse_function=parse_aix_diskiod,
)


def _compute_rates(
    disk: diskstat.Disk,
    value_store,
) -> diskstat.Disk:
    now = time.time()
    disk_with_rates = {}
    ignore_res = False
    for key, value in disk.items():
        try:
            disk_with_rates[key] = get_rate(
                value_store,
                key,
                now,
                value,
                raise_overflow=True,
            )
        except IgnoreResultsError:
            ignore_res = True
    if ignore_res:
        raise IgnoreResultsError('Initializing counters')
    return disk_with_rates


def _check_disk(
    params: type_defs.Parameters,
    disk: diskstat.Disk,
) -> type_defs.CheckResult:
    value_store = get_value_store()
    disk_with_rates = _compute_rates(disk, value_store)
    yield from diskstat.check_diskstat_dict(
        params=params,
        disk=disk_with_rates,
        value_store=value_store,
        this_time=time.time(),
    )


def check_aix_diskiod(
    item: str,
    params: type_defs.Parameters,
    section: diskstat.Section,
) -> type_defs.CheckResult:
    if item == 'SUMMARY':
        disk = diskstat.summarize_disks(section.items())
    else:
        try:
            disk = section[item]
        except KeyError:
            return
    yield from _check_disk(params, disk)


def cluster_check_aix_diskiod(
    item: str,
    params: type_defs.Parameters,
    section: Mapping[str, diskstat.Section],
) -> type_defs.CheckResult:
    if item == 'SUMMARY':
        disk = diskstat.summarize_disks(
            item for node_section in section.values() for item in node_section.items())
    else:
        disk = diskstat.combine_disks(
            node_section[item] for node_section in section.values() if item in node_section)
    yield from _check_disk(params, disk)


register.check_plugin(
    name="aix_diskiod",
    service_name="Disk IO %s",
    discovery_ruleset_type="all",
    discovery_default_parameters={'summary': True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=diskstat.discovery_diskstat_generic,
    check_ruleset_name="diskstat",
    check_default_parameters={},
    check_function=check_aix_diskiod,
    cluster_check_function=cluster_check_aix_diskiod,
)
