#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from enum import IntEnum, StrEnum, unique
from typing import Any, cast, Final, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    GetRateError,
    IgnoreResultsError,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib import diskstat


class GetRateErrorEmpty(GetRateError):
    """The exception raised by :func:`.get_rate`.
    Indicates empty store.
        You may use this exception to improve logging.
    """


class GetRateErrorTime(GetRateError):
    """The exception raised by :func:`.get_rate`.
    Indicates negative time
        You may use this exception to improve logging.
    """


class GetRateErrorCounter(GetRateError):
    """The exception raised by :func:`.get_rate`.
    Indicates negative counter
        You may use this exception to improve logging.
    """


def update_value_and_calc_rate(
    value_store: MutableMapping[str, Any],
    key: str,
    *,
    timestamp: float,
    value: float,
    raise_overflow: bool = False,
) -> float:
    """
    1. Update value store.
    2. Calculate rate based on current value and time and last value and time

    Basically its replicates behavior of the get_rate function but uses more precise Exceptions to
    handle abnormal situation.

    Args:

        value_store:     The mapping that holds the last value.
                         Usually this will be the value store provided by the APIs
                         :func:`get_value_store`.
        key:             Unique ID for storing the time/value pair until the next check
        timestamp:       Timestamp of new value
        value:           The new value
        raise_overflow:  Raise a :class:`GetRateError` if the rate is negative

    This function returns the rate of a measurement rₙ as the quotient of the `value` and `time`
    provided to the current function call (xₙ, tₙ) and the `value` and `time` provided to the
    previous function call (xₙ₋₁, tₙ₋₁):

        rₙ = (xₙ - xₙ₋₁) / (tₙ - tₙ₋₁)

    Note that the function simply computes the quotient of the values and times given,
    regardless of any unit. You might as well pass something different than the time.
    However, this function is written with the use case of passing timestamps in mind.

    A :class:`GetRateError` will be raised if one of the following happens:

        * the function is called for the first time
        * the time has not changed
        * the rate is negative and `raise_overflow` is set to True (useful
          for instance when dealing with counters)

    In general there is no need to catch a :class:`.GetRateError`, as it
    inherits :class:`.IgnoreResultsError`.

    Returns:

        The computed rate

    """
    try:
        data_point = DataPoint(timestamp, value)
        prev = update_store(value_store, key, data_point)
        return calc_rate(prev, new=data_point, raise_overflow=raise_overflow)
    except GetRateError as e:
        raise type(e)(f"At {key!r}: {str(e)}")


class DataPoint(NamedTuple):
    """represents a timestamp/value pair"""

    timestamp: float
    value: float


# TODO(sk): typing must be improved i.e. value_store must be statically typed
def update_store(
    value_store: MutableMapping[str, Any],
    key: str,
    data_point: DataPoint,
) -> DataPoint:
    """
    Update value store.

    Args:

        value_store:     The mapping that holds the last value.
                         Usually this will be the value store provided by the APIs
                         :func:`get_value_store`.
        key:             Unique ID for storing the time/value pair until the next check
        data_point:      Timestamp + value

    A `GetRateErrorEmpty` will be raised if the function is called for the first time

    Returns:

        The last pair (time, val) from the store

    """
    # Cast to avoid lots of mypy suppressions. It better reflects the truth anyway.
    value_store = cast(MutableMapping[str, object], value_store)

    last_state = value_store.get(key)
    value_store[key] = (data_point.timestamp, data_point.value)
    match last_state:
        case (
            float()
            | int() as last_time,
            float()
            | int() as last_value,
        ):
            return DataPoint(float(last_time), float(last_value))
        case _other:
            raise GetRateErrorEmpty("Initialized")


def calc_rate(
    prev: DataPoint,
    *,
    new: DataPoint,
    raise_overflow: bool = False,
) -> float:
    """
    Calculate rate based on two data points, last one and new one.

    Args:

        prev:      timestamp + value from update_store
        new:       current timestamp + value
        raise_overflow:  Raise a :class:`GetRateError` if the rate is negative

    This function returns the rate of a measurement rₙ as the quotient of the `value` and `time`
    provided to the current function call (xₙ, tₙ) and the `value` and `time` provided to the
    previous function call (xₙ₋₁, tₙ₋₁):

        rₙ = (xₙ - xₙ₋₁) / (tₙ - tₙ₋₁)

    Note that the function simply computes the quotient of the values and times given,
    regardless of any unit. You might as well pass something different than the time.
    However, this function is written with the use case of passing timestamps in mind.

    A :class:`GetRateError` will be raised if one of the following happens:

        * the time has not changed -> raise GetRateErrorTime
        * the rate is negative and `raise_overflow` is set to True (useful
          for instance when dealing with counters) -> raise GetRateErrorCounter

    In general there is no need to catch a :class:`.GetRateError`, as it
    inherits :class:`.IgnoreResultsError`.

    Returns:

        The computed rate

    """
    prev_time, prev_value = prev
    new_time, new_value = new
    if new_time <= prev_time:
        raise GetRateErrorTime(f"No time difference: {new_time} <= {prev_time}")

    rate = (new_value - prev_value) / (new_time - prev_time)
    if raise_overflow and rate < 0:
        # Do not try to handle wrapped counters. We do not know
        # whether they are 32 or 64 bit. It also could happen counter
        # reset (reboot, etc.). Better is to leave this value undefined
        # and wait for the next check interval.
        raise GetRateErrorCounter(f"Value overflow: {new_value} <= {prev_value}")

    return rate


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

DiskType = dict[str, int | float]
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


def parse_winperf_phydisk(string_table: StringTable) -> diskstat.Section | None:
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


def _is_data_absent(data_table: StringTable) -> bool:
    # In case disk performance counters are not enabled, the agent sends
    # an almost empty section, where the second line is missing completely
    return len(data_table) <= 1


def _create_disk_template(header_row: Sequence[str]) -> DiskType:
    timestamp, frequency = _parse_header(header_row)
    disk_template = {"timestamp": timestamp}
    if frequency is not None:
        disk_template["frequency"] = frequency
    return disk_template


def _parse_header(header_row: Sequence[str]) -> tuple[float, int | None]:
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


def _get_metric_name(data_row: Sequence[str]) -> str | None:
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


agent_section_winperf_phydisk = AgentSection(
    name="winperf_phydisk",
    parse_function=parse_winperf_phydisk,
)


def discover_winperf_phydisk(
    params: Sequence[Mapping[str, Any]],
    section: diskstat.Section,
) -> DiscoveryResult:
    yield from diskstat.discovery_diskstat_generic(
        params,
        section,
    )


@dataclass(frozen=True)
class _ComputeSpec:
    value_store: MutableMapping[str, Any]
    value_store_suffix: str
    timestamp: float
    frequency: float | None


class _Denom(NamedTuple):
    value: float | None
    exception: bool

    def calc_smart(self, nom: float) -> float:
        """
        Throws exception if exception registered or denom is not defined
        Returns nom/denom if denom is defined and not 0
        Returns 0 if nom and denom both are 0: this is quite special case related to Windows.
        Windows can send the same data again and again. With normal counter we get 0, but for
        """
        if self.exception or self.value is None:
            raise IgnoreResultsError
        if self.value != 0:
            return nom / self.value
        if nom == 0:
            return 0
        raise IgnoreResultsError


def _compute_rates_single_disk(
    disk: diskstat.Disk,
    value_store: MutableMapping[str, Any],
    value_store_suffix: str = "",
) -> diskstat.Disk:
    disk_with_rates = {}
    compute_specs: Final = _ComputeSpec(
        value_store=value_store,
        value_store_suffix=value_store_suffix,
        timestamp=disk["timestamp"],
        frequency=disk.get("frequency"),
    )
    bad_results = False
    metric_values = [(metric, value) for metric, value in disk.items() if _is_work_metric(metric)]
    for metric, value in metric_values:
        denom = _calc_denom(metric, disk, compute_specs)
        try:
            # we must update value_store here
            nom = _update_value_and_calc_rate(metric, compute_specs, value)
            disk_with_rates[metric] = denom.calc_smart(nom)
        except IgnoreResultsError:
            bad_results = True

    if bad_results:
        raise IgnoreResultsError("Initializing counters!")

    return disk_with_rates


def _is_work_metric(metric: str) -> bool:
    return metric not in ("timestamp", "frequency") and not metric.endswith("base")


class MetricSuffix(StrEnum):
    QUEUE_LENGTH = "ql"  # Queue Lengths (currently only Windows). Windows uses counters here.
    WAIT = "wait"


def _as_denom_metric(metric: str) -> str:
    return metric + _METRIC_DENOM_SUFFIX


def _calc_denom(metric: str, disk: diskstat.Disk, compute_specs: _ComputeSpec) -> _Denom:
    if metric.endswith(MetricSuffix.QUEUE_LENGTH):
        return _Denom(10_000_000.0, False)
    if not metric.endswith(MetricSuffix.WAIT):
        return _Denom(1.0, False)

    return _calc_denom_for_wait(metric, disk, compute_specs)


def _calc_denom_for_wait(metric: str, disk: diskstat.Disk, compute_specs: _ComputeSpec) -> _Denom:
    if compute_specs.frequency is None:
        return _Denom(None, False)
    denom_value = disk.get(_as_denom_metric(metric))
    if denom_value is None:
        return _Denom(None, False)

    try:
        # we may get `None` from the counter only when Windows agent output is broken
        # get_rate must throw an exception
        denom_rate = _update_value_and_calc_rate(
            _as_denom_metric(metric), compute_specs, denom_value
        )
    except IgnoreResultsError:
        return _Denom(None, True)

    return _Denom(denom_rate * compute_specs.frequency, False)


def _update_value_and_calc_rate(metric: str, compute_specs: _ComputeSpec, value: float) -> float:
    return update_value_and_calc_rate(
        compute_specs.value_store,
        metric + compute_specs.value_store_suffix,
        timestamp=compute_specs.timestamp,
        value=value,
        raise_overflow=True,
    )


def check_winperf_phydisk(
    item: str,
    params: Mapping[str, Any],
    section: diskstat.Section,
) -> CheckResult:
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

    yield from diskstat.check_diskstat_dict_legacy(
        params=params,
        disk=disk_with_rates,
        value_store=value_store,
        this_time=time.time(),
    )


def cluster_check_winperf_phydisk(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, diskstat.Section | None],
) -> CheckResult:
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


check_plugin_winperf_phydisk = CheckPlugin(
    name="winperf_phydisk",
    service_name="Disk IO %s",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=diskstat.DISKSTAT_DEFAULT_PARAMS,
    discovery_ruleset_name="diskstat_inventory",
    discovery_function=discover_winperf_phydisk,
    check_ruleset_name="disk_io",
    check_default_parameters={},
    check_function=check_winperf_phydisk,
    cluster_check_function=cluster_check_winperf_phydisk,
)
