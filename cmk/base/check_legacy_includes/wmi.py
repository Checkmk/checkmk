#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import regex
from cmk.base.check_api import MKCounterWrapped
from cmk.base.check_api import get_age_human_readable
from cmk.base.check_api import get_percent_human_readable
from cmk.base.check_api import get_rate
from cmk.base.check_api import check_levels
# This set of functions are used for checks that handle "generic" windows
# performance counters as reported via wmi
# They also work with performance counters reported through other means
# (i.e. pdh) as long as the data transmitted as a csv table.

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

    def __init__(self, name, headers, key_field, timestamp, frequency, rows=None):
        self.__name = name
        self.__headers = {}
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

        self.__row_lookup = {}
        self.__rows = []
        self.timed_out = False
        if rows:
            for row in rows:
                self.add_row(row)

    def __repr__(self):
        key_field = None
        if self.__key_index is not None:
            for header, index in self.__headers.items():
                if index == self.__key_index:
                    key_field = header

        headers = [
            name for name, index in sorted(iter(self.__headers.items()), lambda x, y: x[1] - y[1])
        ]

        return "%s(%r, %r, %r, %r, %r, %r)" % (self.__class__.__name__, self.__name, headers,
                                               key_field, self.__timestamp, self.__frequency,
                                               self.__rows)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        return not self == other

    def add_row(self, row):
        row = row[:]
        if self.__key_index is not None:
            key = row[self.__key_index].strip("\"")
            # there are multiple names to denote the "total" line, normalize that
            if key in WMITable.TOTAL_NAMES:
                key = row[self.__key_index] = None
            self.__row_lookup[key] = len(self.__rows)

        self.__rows.append(row)
        if not self.timed_out:
            # Check if there's a timeout in the last added line
            # ie. row (index) == -1, column 'WMIStatus'
            try:
                wmi_status = self._get_row_col_value(-1, 'WMIStatus')
            except IndexError:
                #TODO Why does the agent send data with different length?
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
            if wmi_status.lower() == "timeout":
                self.timed_out = True

    def get(self, row, column, silently_skip_timed_out=False):
        if not silently_skip_timed_out and self.timed_out:
            raise MKCounterWrapped('WMI query timed out')
        return self._get_row_col_value(row, column)

    def _get_row_col_value(self, row, column):
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

    def row_labels(self):
        return list(self.__row_lookup)

    def row_count(self):
        return len(self.__rows)

    def name(self):
        return self.__name

    def timestamp(self):
        return self.__timestamp

    def frequency(self):
        return self.__frequency

    def _normalize_key(self, key):
        # Different API versions may return different headers/keys
        # for equal objects, eg. "skype.sip_stack":
        # - "SIP - Incoming Responses Dropped /Sec"
        # - "SIP - Incoming Responses Dropped/sec"
        # For these cases we normalize these keys to be independent of
        # upper/lower case and spaces.
        return key.replace(" ", "").lower()


def parse_wmi_table(info, key="Name"):
    parsed = {}
    info_iter = iter(info)

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
                tablename = regex(r"\[(.*)\]").search(line[0]).group(1)

                # Did subsection get WMI timeout?
                line = next(info_iter)
            else:
                # single-table input
                tablename = ""

            missing_wmi_status, current_table =\
                _prepare_wmi_table(parsed, tablename, line, key, timestamp, frequency)

            # read table content
            line = next(info_iter)
            while not line[0].startswith("["):
                current_table.add_row(line + ['OK'] * bool(missing_wmi_status))
                line = next(info_iter)
    except (StopIteration, ValueError):
        # regular end of block
        pass

    return parsed


def _prepare_wmi_table(parsed, tablename, line, key, timestamp, frequency):
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
        header = ['WMIStatus']
        key = None
    else:
        old_timed_out = False
        header = line[:]

    missing_wmi_status = False
    if 'WMIStatus' not in header:
        missing_wmi_status = True
        header.append('WMIStatus')

    current_table = parsed.setdefault(tablename,
                                      WMITable(tablename, header, key, timestamp, frequency))
    if old_timed_out:
        current_table.add_row(['Timeout'])
    return missing_wmi_status, current_table


#.
#   .--Filters-------------------------------------------------------------.
#   |                     _____ _ _ _                                      |
#   |                    |  ___(_) | |_ ___ _ __ ___                       |
#   |                    | |_  | | | __/ _ \ '__/ __|                      |
#   |                    |  _| | | | ||  __/ |  \__ \                      |
#   |                    |_|   |_|_|\__\___|_|  |___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def wmi_filter_global_only(tables, row):
    for table in tables.values():
        try:
            value = table.get(row, "Name", silently_skip_timed_out=True)
        except KeyError:
            return False
        if value != "_Global_":
            return False
    return True


#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'


def required_tables_missing(tables, required_tables):
    return not set(required_tables).issubset(set(tables))


def inventory_wmi_table_instances(tables, required_tables=None, filt=None, levels=None):
    if required_tables is None:
        required_tables = tables

    if required_tables_missing(tables, required_tables):
        return []

    potential_instances = set()
    # inventarize one item per instance that exists in all tables
    for required_table in required_tables:
        table_rows = tables[required_table].row_labels()
        if potential_instances:
            potential_instances &= set(table_rows)
        else:
            potential_instances = set(table_rows)

    # don't include the summary line
    potential_instances.discard(None)

    return [(row, levels) for row in potential_instances if filt is None or filt(tables, row)]


def inventory_wmi_table_total(tables, required_tables=None, filt=None, levels=None):
    if required_tables is None:
        required_tables = tables

    if not tables or required_tables_missing(tables, required_tables):
        return []

    if filt is not None and not filt(tables, None):
        return []

    total_present = all(
        None in tables[required_table].row_labels() for required_table in required_tables)

    if not total_present:
        return []
    return [(None, levels)]


#.
#   .--Check---------------------------------------------------------------.
#   |                      ____ _               _                          |
#   |                     / ___| |__   ___  ___| | __                      |
#   |                    | |   | '_ \ / _ \/ __| |/ /                      |
#   |                    | |___| | | |  __/ (__|   <                       |
#   |                     \____|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# determine time at which a sample was taken
def get_wmi_time(table, row):
    timestamp = table.timestamp() or table.get(row, "Timestamp_PerfTime")
    frequency = table.frequency() or table.get(row, "Frequency_PerfTime")
    if not frequency:
        frequency = 1
    return float(timestamp) / float(frequency)


# to make wato rules simpler, levels are allowed to be passed as tuples if the level
# specifies the upper limit
def _get_levels_quadruple(params):
    if params is None:
        return (None, None, None, None)
    if isinstance(params, tuple):
        return (params[0], params[1], None, None)
    upper = params.get('upper') or (None, None)
    lower = params.get('lower') or (None, None)
    return upper + lower


def wmi_yield_raw_persec(table, row, column, infoname, perfvar, levels=None):
    if table is None:
        # This case may be when a check was discovered with a table which subsequently
        # disappeared again. We expect to get None in this case and return some "nothing happened"
        return 0, "", []

    if row == "":
        row = 0

    try:
        value = int(table.get(row, column))
    except KeyError:
        return 3, "Item not present anymore", []

    value_per_sec = get_rate("%s_%s" % (column, table.name()), get_wmi_time(table, row), value)

    return check_levels(
        value_per_sec,
        perfvar,
        _get_levels_quadruple(levels),
        infoname=infoname,
    )


def wmi_yield_raw_counter(table, row, column, infoname, perfvar, levels=None, unit=""):
    if row == "":
        row = 0

    try:
        value = int(table.get(row, column))
    except KeyError:
        return 3, "counter %r not present anymore" % ((row, column),), []

    return check_levels(
        value,
        perfvar,
        _get_levels_quadruple(levels),
        infoname=infoname,
        unit=unit,
        human_readable_func=str,
    )


def wmi_calculate_raw_average(table, row, column, factor):
    if row == "":
        row = 0

    measure = int(table.get(row, column)) * factor
    base = int(table.get(row, column + "_Base"))

    if base < 0:
        # this is confusing as hell. why does wmi return this value as a 4 byte signed int
        # when it clearly needs to be unsigned? And how does WMI Explorer know to cast this
        # to unsigned?
        base += 1 << 32

    if base == 0:
        return 0.0

    # This is a total counter which can overflow on long-running systems
    # (great choice of datatype, microsoft!)
    # the following forces the counter into a range of 0.0-1.0, but there is no way to know
    # how often the counter overran, so this bay still be wrong
    while (base * factor) < measure:
        base += 1 << 32

    return float(measure) / base


def wmi_calculate_raw_average_time(table, row, column):
    measure = int(table.get(row, column))
    base = int(table.get(row, column + "_Base"))

    sample_time = get_wmi_time(table, row)

    measure_per_sec = get_rate("%s_%s" % (column, table.name()), sample_time, measure)
    base_per_sec = get_rate("%s_%s_Base" % (column, table.name()), sample_time, base)

    if base_per_sec == 0:
        return 0
    return measure_per_sec / base_per_sec  # fixed: true-division


def wmi_yield_raw_average(table, row, column, infoname, perfvar, levels=None, perfscale=1.0):
    try:
        average = wmi_calculate_raw_average(table, row, column, 1) * perfscale
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        _get_levels_quadruple(levels),
        infoname=infoname,
        human_readable_func=get_age_human_readable,
    )


def wmi_yield_raw_average_timer(table, row, column, infoname, perfvar, levels=None):
    try:
        average = wmi_calculate_raw_average_time(table, row,
                                                 column) / table.frequency()  # fixed: true-division
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        _get_levels_quadruple(levels),
        infoname=infoname,
    )


def wmi_yield_raw_fraction(table, row, column, infoname, perfvar, levels=None):
    try:
        average = wmi_calculate_raw_average(table, row, column, 100)
    except KeyError:
        return 3, "item not present anymore", []

    return check_levels(
        average,
        perfvar,
        _get_levels_quadruple(levels),
        infoname=infoname,
        human_readable_func=get_percent_human_readable,
        boundaries=(0, 100),
    )


#.
