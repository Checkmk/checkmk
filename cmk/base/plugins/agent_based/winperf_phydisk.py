#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique
from typing import Any, Final, Mapping, MutableMapping, Optional, Sequence, Union

from .agent_based_api.v1 import (
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
    register,
    type_defs,
)
from .utils import diskstat

# Example output from agent
# <<<winperf_phydisk>>>
# 1352457622.31 234
# 2 instances: 0_C: _Total
# -36 0 0 rawcount                              ----> Current Disk Queue Length as in Windows 10
# -34 235822560 235822560 type(20570500)        ----> % Disk Time
# -34 2664021277 2664021277 type(40030500)      ----
# 1166 235822560 235822560 type(550500)         ----> Average Disk Queue Length
# -32 109877176 109877176 type(20570500)        ----> % Disk Read Time
# -32 2664021277 2664021277 type(40030500)      ----
# 1168 109877176 109877176 type(550500)         ----> Average Disk Read Queue Length
# -30 125945384 125945384 type(20570500)        ----> % Disk Write Time
# -30 2664021277 2664021277 type(40030500)      ----
# 1170 125945384 125945384 type(550500)         ----> Average Disk Write Queue Length
# -28 3526915777 3526915777 average_timer       ----> Avg. Disk sec/Transfer
# -28 36283 36283 average_base                  ----
# -26 1888588843 1888588843 average_timer       ----> Average Disk Seconds/Read
# -26 17835 17835 average_base                  ----
# -24 1638326933 1638326933 average_timer       ----> Average Disk Seconds/Write
# -24 18448 18448 average_base                  ----
# -22 36283 36283 counter                       ----> Disk Transfers/sec
# -20 17835 17835 counter                       ----> Disk Reads/sec
# -18 18448 18448 counter                       ----> Disk Writes/sec
# -16 1315437056 1315437056 bulk_count          ----> Disk Bytes/sec
# -14 672711680 672711680 bulk_count            ----> Disk Read Bytes/sec
# -12 642725376 642725376 bulk_count            ----> Disk Write Bytes/sec
# -10 1315437056 1315437056 average_bulk        ----> Avg. Disk Bytes/Transfer
# -10 36283 36283 average_base                  ----
# -8 672711680 672711680 average_bulk           ----> Avg. Disk Bytes/Read
# -8 17835 17835 average_base                   ----
# -6 642725376 642725376 average_bulk           ----> Avg. Disk Bytes/Write
# -6 18448 18448 average_base                   ----
# 1248 769129229 769129229 type(20570500)       ----> % Idle  Time
# 1248 2664021277 2664021277 type(40030500)     ----
# 1250 1330 1330 counter                        ----> Split IO/Sec
#
# Explanation for two-lines values counters:
#
# `average_base` means PERF_COUNT_BASE
# https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc783087(v=ws.10)
# this a DENOMINATOR and usually represents raw data
# `average_timer` means PERF_COUNT_TIMER
# https://docs.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc783087(v=ws.10)
# this a NUMERATOR and usually represents TIME data
#
# To calculate real average you have to get TWO samples and use Formula
# ((N1 - N0) / F) / (D1 - D0), where the numerator (N) represents the number of ticks counted
# during the last sample interval, the variable F represents the frequency of the ticks, and the
# denominator (D) represents the number of operations completed during the last sample interval.
# Example with F = 2
# Sample 0
# ...
# -26 3 average_timer <- N0
# -26 1 average_base  <- D0
# ...
# Sample 1
# ...
# -26 7 average_timer <- N1
# -26 2 average_base  <- D1
# ...
#
# Result is (7 - 3) / 2 /(2 - 1) = 2
#            N1  N0   F   D1  D0

# NOTE! Data Row
# FirstColumn = CounterNameTitleIndex(as in MSDN) - CounterForPhydisk
# CounterNum for phydisk is 234
# Database location:
# Key: HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Perflib\009
# Value: Counter
# Format is multi string:
# Index0
# Title0
# ...
# IndexN
# TitleN
_LINE_TO_METRIC: Final = {
    "-14": "read_throughput",  # 220 Disk Read Bytes/sec
    "-12": "write_throughput",  # 222 Disk Write Bytes/sec
    "-20": "read_ios",  # 214 Disk Reads/sec
    "-18": "write_ios",  # 216 Disk Writes/sec
    "1168": "read_ql",  # 1402 Avg. Disc Read Queue length
    "1170": "write_ql",  # 1402 Avg. Disc Write Queue length
    "-24": "average_read_wait",  # 210 Avg. Disc sec/Write
    "-26": "average_write_wait",  # 208 Avg. Disc sec/Read
}

DiskType = dict[str, Union[int, float]]
SectionsType = dict[str, DiskType]

_METRIC_DENOM_SUFFIX: Final = "_base"


@unique
class TableRows(IntEnum):
    HEADER = 0
    INSTANCES = 1
    DATA = 2


@unique
class DataRowIndex(IntEnum):
    METRIC_ID = 0
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
    # Example of instances(disk num 2 has no letter as a label)
    # From Agent we get:  "4 instances: 0_C: 1_F: 2 _Total\n"
    # Parser does this:  ['4','instances:','0_C','1_F','2_2', '_Total']
    disk_labels = [disk_str.split("_") for disk_str in instances[InstancesRowIndex.FIRST_DISK : -1]]
    for disk_info in disk_labels:
        disk_num = disk_info[0]
        disk_name = disk_info[-1]  # disk_info may contain only disk num
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


def _is_metric_denom(metric_name: str, *, data_row: Sequence[str]) -> bool:
    return (
        metric_name.startswith("average") and data_row[DataRowIndex.METRIC_TYPE] == "average_base"
    )


def _get_metric_name(data_row: Sequence[str]) -> Optional[str]:
    """Converts numeric value at METRIC_ID offset into check_mk metric name with two exceptions:
    - If index is not known returns None
    - If index is known but name is starting from average and type at METRIC_ID is average_base,
    then returns name + "_base", thus having one metric with two name, for example
    average_time_wait and average_time_wait_base. This case valid for two rows metrics
    """
    if metric_name := _LINE_TO_METRIC.get(data_row[DataRowIndex.METRIC_ID]):
        return (
            _as_denom_metric(metric_name)
            if _is_metric_denom(metric_name, data_row=data_row)
            else metric_name
        )

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


@dataclass(frozen=True)
class _Params:
    value_store: MutableMapping[str, Any]
    value_store_suffix: str
    timestamp: float
    frequency: Optional[float]


_DenomType = tuple[Optional[float], bool]


def _compute_rates_single_disk(
    disk: diskstat.Disk,
    value_store: MutableMapping[str, Any],
    value_store_suffix: str = "",
) -> diskstat.Disk:
    params: Final = _Params(
        value_store=value_store,
        value_store_suffix=value_store_suffix,
        timestamp=disk["timestamp"],
        frequency=disk.get("frequency"),
    )

    rates_and_errors = {
        metric: _compute_rate_for_metric(metric, value, disk, params)
        for metric, value in disk.items()
        if _is_work_metric(metric)
    }

    if any(raised for _rate, raised in rates_and_errors.values()):
        raise IgnoreResultsError("Initializing counters")

    return {
        metric: rate for metric, (rate, _raised) in rates_and_errors.items() if rate is not None
    }


def _compute_rate_for_metric(
    metric: str,
    value: float,
    disk: diskstat.Disk,
    params: _Params,
) -> tuple[float | None, bool]:
    scaling = _scaling(metric)
    if scaling is not None:
        return (
            (None, True)
            if (rate := _get_rate(metric, params, value)) is None
            else (rate * scaling, False)
        )

    return _calc_denom_for_wait(metric, disk, params, value)


def _is_work_metric(metric: str) -> bool:
    return metric not in ("timestamp", "frequency") and not metric.endswith("base")


class MetricSuffix(StrEnum):
    QUEUE_LENGTH = "ql"  # Queue Lengths (currently only Windows). Windows uses counters here.
    WAIT = "wait"


def _as_denom_metric(metric: str) -> str:
    return metric + _METRIC_DENOM_SUFFIX


def _scaling(metric: str) -> float | None:
    if metric.endswith(MetricSuffix.QUEUE_LENGTH):
        return 1e-7
    if not metric.endswith(MetricSuffix.WAIT):
        return 1.0
    return None


def _calc_denom_for_wait(
    metric: str, disk: diskstat.Disk, params: _Params, value: float
) -> _DenomType:
    if params.frequency is None:
        return None, False
    denom_value = disk.get(_as_denom_metric(metric))
    if denom_value is None:
        return None, False

    rate = _get_rate(metric, params, value)
    # TODO(jh): get_rate returns Rate for new_metric_value. Fix or explain, please
    match _get_rate(_as_denom_metric(metric), params, denom_value):
        case None:
            # using the value if the rate can not be computed. Why?
            return denom_value, True
        case 0.0:
            # using 1 for the base if the counter didn't increase. This makes little to no sense
            denom, exception_raised = 1 * params.frequency, False
        case denom_rate:
            assert denom_rate is not None
            denom, exception_raised = denom_rate * params.frequency, False

    return (None, True) if rate is None else (rate / denom, exception_raised)


def _get_rate(metric: str, params: _Params, value: float) -> float | None:
    try:
        return get_rate(
            params.value_store,
            metric + params.value_store_suffix,
            params.timestamp,
            value,
            raise_overflow=True,
        )
    except GetRateError:
        return None


def _with_average_in_seconds(params: Mapping[str, Any]) -> Mapping[str, Any]:
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
        params=_with_average_in_seconds(params),
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
