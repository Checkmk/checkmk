#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from enum import IntEnum, unique
from typing import Any, Final, Mapping, MutableMapping, Optional, Sequence, Union

from .agent_based_api.v1 import get_rate, get_value_store, IgnoreResultsError, register, type_defs
from .utils import diskstat

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

DiskType = dict[str, Union[int, float]]
SectionsType = dict[str, DiskType]


@unique
class TableRows(IntEnum):
    HEADER = 0
    INSTANCES = 1
    DATA = 2


@unique
class DataRowIndex(IntEnum):
    METRIC = 0
    METRIC_TYPE = -1


@unique
class HeaderRowIndex(IntEnum):
    TIMESTAMP = 0
    FREQUENCY = 2


# index row
@unique
class InstancesRowIndex(IntEnum):
    ID = 1
    FIRST_DISK = 2


def parse_winperf_phydisk(string_table: type_defs.StringTable) -> Optional[diskstat.Section]:
    if _is_data_absent(string_table):
        return None
    instances = string_table[TableRows.INSTANCES]
    if instances[InstancesRowIndex.ID] != "instances:":
        return {}

    disk_template: Final = _create_disk_template(string_table[TableRows.HEADER])
    sections: Final = _create_sections(instances, disk_template)
    for data_row in string_table[TableRows.DATA :]:
        _update_sections(sections, data_row)
    return sections


def _is_data_absent(data_table: type_defs.StringTable) -> bool:
    # In case disk performance counters are not enabled, the agent sends
    # an almost empty section, where the second line is missing completely
    return len(data_table) <= 1


def _create_disk_template(header_row: Sequence[str]) -> DiskType:
    timestamp, frequency = _parse_header(header_row)
    disk_template = {"timestamp": timestamp}
    if frequency is not None:
        disk_template["frequency"] = frequency
    return disk_template


def _parse_header(header_row: Sequence[str]) -> tuple[float, Optional[int]]:
    timestamp = float(header_row[HeaderRowIndex.TIMESTAMP])
    try:
        return timestamp, int(header_row[HeaderRowIndex.FREQUENCY])
    except IndexError:
        return timestamp, None


def _create_sections(instances: Sequence[str], disk_template: DiskType) -> SectionsType:
    sections: SectionsType = {}
    # Example of instances
    # From Agent we get:  "3 instances: 0_C: 1_F: _Total\n"
    # Parser does this:  ['3','instances:','0_C','1_F','_Total']
    disk_labels = [disk_str.split("_") for disk_str in instances[InstancesRowIndex.FIRST_DISK : -1]]
    for disk_num, disk_name in disk_labels:
        new_disk = disk_template.copy()
        if disk_name in sections:
            # Disk exists(strange!): write full disk id but reversed: not "C", but "C_1" or "C_0"
            sections[f"{disk_num}_{disk_name}"] = new_disk  # TODO(jh): Reversed? Explain, pls
        else:
            sections[disk_name] = new_disk
    return sections


def _update_sections(sections: SectionsType, row: Sequence[str]) -> None:
    metric_name = _get_metric_name(row)
    if metric_name is None:
        return

    # TABLE format:
    # metric disk1 ... diskN total type            <-- from header(approximately)
    # 1170   14    ... 11    334   type(550500)    <-- row 1
    # ...
    # -26    334   ... 999   1001  average_timer   <-- row N
    # -26    3     ... 9     14    average_base    <-- row N
    # ...
    # The data are located in row[1:-2] on per-disk base
    for disk, value in zip(
        iter(sections.values()),
        iter(map(int, row[1:-2])),
    ):
        disk[metric_name] = value


def _get_metric_name(data_row: Sequence[str]) -> Optional[str]:
    if metric_name := _LINE_TO_METRIC.get(data_row[DataRowIndex.METRIC]):
        if (
            metric_name.startswith("average")
            and data_row[DataRowIndex.METRIC_TYPE] == "average_base"
        ):
            metric_name += "_base"
        return metric_name

    return None


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
    disks_merged: dict[str, diskstat.Disk] = {}
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
