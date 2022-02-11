#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent
# <<<winperf_phydisk>>>
# 1352457622.31 234
# 2 instances: 0_C: _Total
# -36 0 0 rawcount
# -34 235822560 235822560 type(20570500)
# -34 2664021277 2664021277 type(40030500)
# 1166 235822560 235822560 type(550500)        ----> Average Disk Queue Length
# -32 109877176 109877176 type(20570500)
# -32 2664021277 2664021277 type(40030500)
# 1168 109877176 109877176 type(550500)        ----> Average Disk Read Queue Length
# -30 125945384 125945384 type(20570500)
# -30 2664021277 2664021277 type(40030500)
# 1170 125945384 125945384 type(550500)        ----> Average Disk Write Queue Length
# -28 3526915777 3526915777 average_timer
# -28 36283 36283 average_base
# -26 1888588843 1888588843 average_timer     ----> Average Disk Seconds/Read
# -26 17835 17835 average_base
# -24 1638326933 1638326933 average_timer
# -24 18448 18448 average_base                ----> Average Disk Seconds/Write
# -22 36283 36283 counter
# -20 17835 17835 counter                     ----> Disk Reads/sec
# -18 18448 18448 counter                     ----> Disk Writes/sec
# -16 1315437056 1315437056 bulk_count
# -14 672711680 672711680 bulk_count          ----> Disk Read Bytes/sec
# -12 642725376 642725376 bulk_count          ----> Disk Write Bytes/sec
# -10 1315437056 1315437056 average_bulk
# -10 36283 36283 average_base
# -8 672711680 672711680 average_bulk
# -8 17835 17835 average_base
# -6 642725376 642725376 average_bulk
# -6 18448 18448 average_base
# 1248 769129229 769129229 type(20570500)
# 1248 2664021277 2664021277 type(40030500)
# 1250 1330 1330 counter

import time
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence

from .agent_based_api.v1 import get_rate, get_value_store, IgnoreResultsError, register, type_defs
from .utils import diskstat

_LINE_TO_METRIC = {
    "-14": "read_throughput",
    "-12": "write_throughput",
    "-20": "read_ios",
    "-18": "write_ios",
    "1168": "read_ql",
    "1170": "write_ql",
    "-24": "average_read_wait",
    "-26": "average_write_wait",
}


def parse_winperf_phydisk(string_table: type_defs.StringTable) -> Optional[diskstat.Section]:

    section: Dict[str, Dict[str, float]] = {}

    # In case disk performance counters are not enabled, the agent sends
    # an almost empty section, where the second line is missing completely
    if len(string_table) == 1:
        return None

    first_line = string_table[0]
    disk_template = {
        "timestamp": float(first_line[0]),
    }
    try:
        disk_template["frequency"] = int(first_line[2])
    except IndexError:
        pass

    instances_line = string_table[1]
    if instances_line[1] == "instances:":
        for disk_id_str in instances_line[2:-1]:
            disk_id = disk_id_str.split("_")
            new_disk = disk_template.copy()
            if disk_id[-1] in section:
                section["%s_%s" % (disk_id[-1], disk_id[0])] = new_disk
            else:
                section[disk_id[-1]] = new_disk
    else:
        return section

    for line in string_table[2:]:

        metric = _LINE_TO_METRIC.get(line[0])
        if not metric:
            continue

        if metric.startswith("average") and line[-1] == "average_base":
            metric += "_base"

        for disk, val in zip(
            iter(section.values()),
            iter(map(int, line[1:-2])),
        ):
            disk[metric] = val

    return section


register.agent_section(
    name="winperf_phydisk",
    parse_function=parse_winperf_phydisk,
)


def discover_winperf_phydisk(
    params: Sequence[Mapping[str, Any]],
    section: diskstat.Section,
) -> type_defs.DiscoveryResult:
    yield from diskstat.discovery_diskstat_generic(
        params,
        section,
    )


def _compute_rates_single_disk(
    disk: diskstat.Disk,
    value_store: MutableMapping[str, Any],
    value_store_suffix: str = "",
) -> diskstat.Disk:

    disk_with_rates = {}
    timestamp = disk["timestamp"]
    frequency = disk.get("frequency")
    raised_ignore_res_excpt = False

    for metric, value in disk.items():

        if metric in ("timestamp", "frequency") or metric.endswith("base"):
            continue

        # Queue Lengths (currently only Windows). Windows uses counters here.
        # I have not understood, why..
        if metric.endswith("ql"):
            denom = 10000000.0

        elif metric.endswith("wait"):
            key_base = metric + "_base"
            base = disk.get(key_base)
            if base is None or frequency is None:
                continue

            # using 1 for the base if the counter didn't increase. This makes little to no sense
            try:
                base = (
                    get_rate(
                        value_store,
                        key_base + value_store_suffix,
                        timestamp,
                        base,
                        raise_overflow=True,
                    )
                    or 1
                )
            except IgnoreResultsError:
                raised_ignore_res_excpt = True

            denom = base * frequency

        else:
            denom = 1.0

        try:
            disk_with_rates[metric] = (
                get_rate(
                    value_store,
                    metric + value_store_suffix,
                    timestamp,
                    value,
                    raise_overflow=True,
                )
                / denom
            )

        except IgnoreResultsError:
            raised_ignore_res_excpt = True

    if raised_ignore_res_excpt:
        raise IgnoreResultsError("Initializing counters")

    return disk_with_rates


def _averaging_to_seconds(params: Mapping[str, Any]) -> Mapping[str, Any]:
    key_avg = "average"
    if key_avg in params:
        params = {
            **params,
            key_avg: params[key_avg] * 60,
        }
    return params


def check_winperf_phydisk(
    item: str,
    params: Mapping[str, Any],
    section: diskstat.Section,
) -> type_defs.CheckResult:
    # Unfortunately, summarizing the disks does not commute with computing the rates for this check.
    # Therefore, we have to compute the rates first.

    value_store = get_value_store()

    if item == "SUMMARY":
        names_and_disks_with_rates = diskstat.compute_rates_multiple_disks(
            section,
            value_store,
            _compute_rates_single_disk,
        )
        disk_with_rates = diskstat.summarize_disks(iter(names_and_disks_with_rates.items()))

    else:
        try:
            disk_with_rates = _compute_rates_single_disk(
                section[item],
                value_store,
            )
        except KeyError:
            return

    yield from diskstat.check_diskstat_dict(
        params=_averaging_to_seconds(params),
        disk=disk_with_rates,
        value_store=value_store,
        this_time=time.time(),
    )


def cluster_check_winperf_phydisk(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[diskstat.Section]],
) -> type_defs.CheckResult:
    # We potentially overwrite a disk from an earlier section with a disk with the same name from a
    # later section
    disks_merged: Dict[str, diskstat.Disk] = {}
    for node_section in section.values():
        disks_merged.update(node_section or {})

    yield from check_winperf_phydisk(
        item,
        params,
        disks_merged,
    )


register.check_plugin(
    name="winperf_phydisk",
    service_name="Disk IO %s",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={"summary": True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=discover_winperf_phydisk,
    check_ruleset_name="disk_io",
    check_default_parameters={},
    check_function=check_winperf_phydisk,
    cluster_check_function=cluster_check_winperf_phydisk,
)
