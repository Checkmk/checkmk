#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Callable, Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from math import ceil

from cmk.agent_based.v2 import (
    check_levels,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    LevelsT,
    Service,
    StringTable,
)

# This set of functions is used for checks that handle "generic" windows
# performance counters as reported via wmi
# They also work with performance counters reported through other means
# (i.e. pdh) as long as the data is transmitted as a csv table.

# Sample data:
# <<<dotnet_clrmemory:sep(44)>>>
# AllocatedBytesPersec,Caption,Description,FinalizationSurvivors,Frequency_Object,...
# 26812621794240,,,32398,0,...
# 2252985000,,,0,0,...

#   .--Parse---------------------------------------------------------------.
#   |                      ____                                            |
#   |                     |  _ \ __ _ _ __ ___  ___                        |
#   |                     | |_) / _` | '__/ __|/ _ \                       |
#   |                     |  __/ (_| | |  \__ \  __/                       |
#   |                     |_|   \__,_|_|  |___/\___|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class WMIQueryTimeoutError(Exception):
    pass


class WMITable:
    """
    Represents a 2-dimensional table of performance metrics.
    Each table represents a class of objects about which metrics are gathered,
    like "processor" or "physical disk" or "network interface"
    columns represent the individiual metrics and are fixed after initialization
    rows represent the actual values, one row per actual instance (i.e. a
    specific processor, disk or interface)
    the table can also contain the sample time where the metrics were read,
    otherwise the caller will have to assume the sampletime is one of the
    metrics.
    """

    TOTAL_NAMES = ["_Total", "", "__Total__", "_Global"]

    def __init__(
        self,
        name: str,
        headers: Iterable[str],
        key_field: str | None,
        timestamp: int | None,
        frequency: int | None,
        rows: Iterable[Sequence[str]] | None = None,
    ) -> None:
        self.__name = name
        self.__headers: MutableMapping[str, int] = {}
        self.__timestamp = timestamp
        self.__frequency = frequency

        prev_header = None
        for index, header in enumerate(headers):
            if not header.strip() and prev_header:
                # MS apparently doesn't bother to provide a name
                # for base columns with performance counters
                header = prev_header + "_Base"
            header = self._normalize_key(header)
            self.__headers[header] = index
            prev_header = header

        self.__key_index = None
        if key_field is not None:
            try:
                self.__key_index = self.__headers[self._normalize_key(key_field)]
            except KeyError as e:
                raise KeyError(str(e) + " missing, valid keys: " + ", ".join(self.__headers))

        self.__row_lookup: MutableMapping[str | None, int] = {}
        self.__rows: MutableSequence[Sequence[str | None]] = []
        self.timed_out = False
        if rows:
            for row in rows:
                self.add_row(row)

    def __repr__(self) -> str:
        key_field = None
        if self.__key_index is not None:
            for header, index in self.__headers.items():
                if index == self.__key_index:
                    key_field = header

        headers = [name for name, index in sorted(iter(self.__headers.items()), key=lambda x: x[1])]

        return f"{self.__class__.__name__}({self.__name!r}, {headers!r}, {key_field!r}, {self.__timestamp!r}, {self.__frequency!r}, {self.__rows!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other: object) -> bool:
        return not self == other

    def add_row(self, row: Sequence[str]) -> None:
        row_mutable: MutableSequence[str | None] = [*row]
        if self.__key_index is not None:
            key: str | None = row[self.__key_index].strip('"')
            # there are multiple names to denote the "total" line, normalize that
            if key in WMITable.TOTAL_NAMES:
                key = row_mutable[self.__key_index] = None
            self.__row_lookup[key] = len(self.__rows)

        self.__rows.append(row_mutable)
        if not self.timed_out:
            # Check if there's a timeout in the last added line
            # ie. row (index) == -1, column 'WMIStatus'
            try:
                wmi_status = self._get_row_col_value(-1, "WMIStatus")
            except IndexError:
                # TODO Why does the agent send data with different length?
                # Eg. skype
                # tablename = [LS:WEB - EventChannel]
                # header = [
                #    u'instance', u'EventChannel - Pending Get', u' Timed Out Request Count',
                #    u'EventChannel - Pending Get', u' Active Request Count', u'EventChannel - Push Events',
                #    u' Channel Clients Active', u'EventChannel - Push Events', u' Channel Clients Disposed',
                #    u'EventChannel - Push Events', u' Notification Requests Sent',
                #    u'EventChannel - Push Events', u' Heartbeat Requests Sent', u'EventChannel - Push Events',
                #    u' Requests Succeeded', u'EventChannel - Push Events', u' Requests Failed'
                # ]
                # row = [u'"_Total"', u'259', u'1', u'0', u'0', u'0', u'0', u'0', u'0']
                # Then we try to check last value of row
                wmi_status = self._get_row_col_value(-1, -1)
            if isinstance(wmi_status, str) and wmi_status.lower() == "timeout":
                self.timed_out = True

    def get(
        self, row: str | int, column: str | int, *, raise_on_timeout: bool = False
    ) -> str | None:
        if raise_on_timeout and self.timed_out:
            raise WMIQueryTimeoutError("WMI query timed out")
        return self._get_row_col_value(row, column)

    def _get_row_col_value(
        self,
        row: str | int,
        column: str | int,
    ) -> str | None:
        if isinstance(row, int):
            row_index = row
        else:
            row_index = self.__row_lookup[row]

        if isinstance(column, int):
            col_index = column
        else:
            try:
                col_index = self.__headers[self._normalize_key(column)]
            except KeyError as e:
                raise KeyError(str(e) + " missing, valid keys: " + ", ".join(self.__headers))
        return self.__rows[row_index][col_index]

    @property
    def row_labels(self) -> Iterable[str | None]:
        return list(self.__row_lookup)

    @property
    def row_count(self) -> int:
        return len(self.__rows)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def timestamp(self) -> int | None:
        return self.__timestamp

    @property
    def frequency(self) -> int | None:
        return self.__frequency

    @staticmethod
    def _normalize_key(key: str) -> str:
        # Different API versions may return different headers/keys
        # for equal objects, eg. "skype.sip_stack":
        # - "SIP - Incoming Responses Dropped /Sec"
        # - "SIP - Incoming Responses Dropped/sec"
        # For these cases we normalize these keys to be independent of
        # upper/lower case and spaces.
        return key.replace(" ", "").lower()


WMISection = Mapping[str, WMITable]


def parse_wmi_table(
    string_table: StringTable,
    key: str = "Name",
    # Needed in check_legacy_includes/wmi.py
    table_type: type[WMITable] = WMITable,
) -> WMISection:
    parsed: MutableMapping[str, WMITable] = {}
    info_iter = iter(string_table)

    try:
        # read input line by line. rows with [] start the table name.
        # Each table has to start with a header line
        line = next(info_iter)

        timestamp, frequency = None, None
        if line[0] == "sampletime":
            timestamp, frequency = int(line[1]), int(line[2])
            line = next(info_iter)

        while True:
            if len(line) == 1 and line[0].startswith("["):
                # multi-table input
                match = re.search(r"\[(.*)\]", line[0])
                assert match is not None
                tablename = str(match.group(1))

                # Did subsection get WMI timeout?
                line = next(info_iter)
            else:
                # single-table input
                tablename = ""

            missing_wmi_status, current_table = _prepare_wmi_table(
                parsed,
                tablename,
                line,
                key,
                timestamp,
                frequency,
                table_type,
            )

            # read table content
            line = next(info_iter)
            while not line[0].startswith("["):
                current_table.add_row(line + ["OK"] * bool(missing_wmi_status))
                line = next(info_iter)
    except (StopIteration, ValueError):
        # regular end of block
        pass

    return parsed


def _prepare_wmi_table(
    parsed: MutableMapping[str, WMITable],
    tablename: str,
    line: Sequence[str],
    key: str | None,
    timestamp: int | None,
    frequency: int | None,
    # Needed in check_legacy_includes/wmi.py
    table_type: type[WMITable],
) -> tuple[bool, WMITable]:
    # Possibilities:
    # #1 Agent provides extra column for WMIStatus; since 1.5.0p14
    # <<<SEC>>>
    # [foo]
    # Name,...,WMIStatus
    # ABC,...,OK/Timeout
    # [bar]
    # Name,...,WMIStatus
    # DEF,...,OK/Timeout
    #
    # #2 Old agents have no WMIStatus column; before 1.5.0p14
    # <<<SEC>>>
    # [foo]
    # Name,...,
    # ABC,...,
    # [bar]
    # Name,...,
    # DEF,...,
    #
    # #3 Old agents which report a WMITimeout in any sub section; before 1.5.0p14
    # <<<SEC>>>
    # [foo]
    # WMItimeout
    # [bar]
    # Name,...,
    # DEF,...,
    if line[0].lower() == "wmitimeout":
        old_timed_out = True
        header: Iterable[str] = ["WMIStatus"]
        key = None
    else:
        old_timed_out = False
        header = line

    missing_wmi_status = False
    if "WMIStatus" not in header:
        missing_wmi_status = True
        header = [*header, "WMIStatus"]

    current_table = parsed.setdefault(
        tablename,
        table_type(
            tablename,
            header,
            key,
            timestamp,
            frequency,
        ),
    )
    if old_timed_out:
        current_table.add_row(["Timeout"])
    return missing_wmi_status, current_table


def required_tables_missing(
    tables: Iterable[str],
    required_tables: Iterable[str],
) -> bool:
    return not set(required_tables).issubset(set(tables))


def get_wmi_time(table: WMITable, row: str | int, *, raise_on_timeout: bool = False) -> float:
    timestamp = table.timestamp or table.get(
        row, "Timestamp_PerfTime", raise_on_timeout=raise_on_timeout
    )
    frequency = table.frequency or table.get(
        row, "Frequency_PerfTime", raise_on_timeout=raise_on_timeout
    )
    assert timestamp is not None
    if not frequency:
        frequency = 1
    return float(timestamp) / float(frequency)


def discover_wmi_table_instances(
    tables: WMISection,
    required_tables: Iterable[str] | None = None,
    filt: Callable[[WMISection, str | int], bool] | None = None,
    levels: Mapping[str, object] | None = None,
) -> DiscoveryResult:
    if required_tables is None:
        required_tables = tables

    if required_tables_missing(tables, required_tables):
        return

    potential_instances: set = set()
    # inventarize one item per instance that exists in all tables
    for required_table in required_tables:
        table_rows = tables[required_table].row_labels
        if potential_instances:
            potential_instances &= set(table_rows)
        else:
            potential_instances = set(table_rows)

    # don't include the summary line
    potential_instances.discard(None)

    for instance in potential_instances:
        if filt is None or filt(tables, instance):
            yield Service(item=instance, parameters=levels or {})


def discover_wmi_table_total(
    tables: WMISection,
    required_tables: Iterable[str] | None = None,
    filt: Callable[[WMISection, None], bool] | None = None,
) -> DiscoveryResult:
    if required_tables is None:
        required_tables = tables

    if not tables or required_tables_missing(tables, required_tables):
        return

    if filt is not None and not filt(tables, None):
        return

    total_present = all(
        None in tables[required_table].row_labels for required_table in required_tables
    )

    if not total_present:
        return
    yield Service(item=None)


# .
#   .--Check---------------------------------------------------------------.
#   |                      ____ _               _                          |
#   |                     / ___| |__   ___  ___| | __                      |
#   |                    | |   | '_ \ / _ \/ __| |/ /                      |
#   |                    | |___| | | |  __/ (__|   <                       |
#   |                     \____|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_wmi_raw_counter(
    table: WMITable,
    row: str | int,
    column: str | int,
    metric_name: str | None = None,
    label: str | None = None,
    levels_upper: LevelsT | None = None,
    levels_lower: LevelsT | None = None,
    render_func: Callable[[float], str] | None = None,
) -> CheckResult:
    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    yield from check_levels(
        int(value),
        metric_name=metric_name,
        label=label,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=render_func,
    )


def wmi_calculate_raw_average(
    table: WMITable,
    row: str | int,
    column: str,
    factor: float,
) -> float:
    if row == "":
        row = 0

    measure = table.get(row, column)
    base = table.get(row, column + "_Base")
    assert measure
    assert base

    base_int = int(base)

    if base_int < 0:
        # this is confusing as hell. why does wmi return this value as a 4 byte signed int
        # when it clearly needs to be unsigned? And how does WMI Explorer know to cast this
        # to unsigned?
        base_int += 1 << 32

    if base_int == 0:
        return 0.0

    return scale_counter(int(measure) * factor, factor, base_int)


def check_wmi_raw_average(
    table: WMITable,
    row: str | int,
    column: str,
    factor: float,
    metric_name: str | None = None,
    label: str | None = None,
    levels_upper: LevelsT | None = None,
    levels_lower: LevelsT | None = None,
    render_func: Callable[[float], str] | None = None,
) -> CheckResult:
    try:
        value = wmi_calculate_raw_average(table, row, column, factor)
    except KeyError:
        return

    yield from check_levels(
        value,
        metric_name=metric_name,
        label=label,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=render_func,
    )


def scale_counter(
    measure: float,
    factor: float,
    base: float,
) -> float:
    # This is a total counter which can overflow on long-running systems
    # the following forces the counter into a range of 0.0-1.0, but there is no way to know
    # how often the counter overran, so this may still be wrong
    times = (measure / factor - base) / (1 << 32)
    base += ceil(times) * (1 << 32)
    return measure / base


def check_wmi_raw_persec(
    table: WMITable,
    row: str | int,
    column: str | int,
    metric_name: str | None = None,
    label: str | None = None,
    levels_upper: LevelsT | None = None,
    levels_lower: LevelsT | None = None,
    render_func: Callable[[float], str] | None = None,
) -> CheckResult:
    if table is None:
        # This case may be when a check was discovered with a table which subsequently disappeared again.
        # We expect to get `None` in this case.
        return

    if row == "":
        row = 0

    try:
        value = table.get(row, column)
        assert value
    except KeyError:
        return

    rate = get_rate(
        get_value_store(),
        f"{column}_{table.name}",
        get_wmi_time(table, row),
        int(value),
        raise_overflow=True,
    )

    yield from check_levels(
        rate,
        metric_name=metric_name,
        label=label,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        render_func=render_func,
    )
