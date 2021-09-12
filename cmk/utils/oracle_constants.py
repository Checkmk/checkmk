#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2020             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Checkmk.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from typing import NamedTuple


def _convert_to_identifier(value):
    characters = {
        " ": "_",
        "/": "",
        "-": "_",
    }
    for char, repl in characters.items():
        value = value.replace(char, repl)
    return value.lower()


#
# IO Files
#
class OracleIOFile(NamedTuple):
    name: str
    id: str


def make_oracle_io_file_list(name_list):
    return [OracleIOFile(name, _convert_to_identifier(name)) for name in name_list]


oracle_iofiles = make_oracle_io_file_list(
    [
        "Archive Log",
        "Archive Log Backup",
        "Control File",
        "Data File",
        "Data File Backup",
        "Data File Copy",
        "Data File Incremental Backup",
        "Data Pump Dump File",
        "External Table",
        "Flashback Log",
        "Log File",
        "Other",
        "Temp File",
    ]
)

oracle_io_sizes = [
    ("s", "Small"),
    ("l", "Large"),
]

oracle_io_types = [
    ("r", "Reads", "1/s"),
    ("w", "Writes", "1/s"),
    ("rb", "Read Bytes", "bytes/s"),
    ("wb", "Write Bytes", "bytes/s"),
]


#
# Waitclasses
#
class OracleWaitclass(NamedTuple):
    name: str
    id: str
    metric: str
    metric_fg: str


def make_oracle_waitclass(name):
    ident = _convert_to_identifier(name)
    metric = "oracle_wait_class_%s_waited" % ident
    metric_fg = metric + "_fg"
    return OracleWaitclass(name, ident, metric, metric_fg)


def make_oracle_waitclass_list(name_list):
    return [make_oracle_waitclass(name) for name in name_list]


oracle_waitclasses = make_oracle_waitclass_list(
    [
        "Administrative",
        "Application",
        "Cluster",
        "Commit",
        "Concurrency",
        "Configuration",
        "Idle",
        "Network",
        "Other",
        "Scheduler",
        "System I/O",
        "User I/O",
    ]
)


#
# SGAs
#
class OracleSGA(NamedTuple):
    name: str
    id: str
    metric: str


def make_oracle_sga(name, metric):
    ident = _convert_to_identifier(name)
    return OracleSGA(name, ident, metric)


def make_oracle_sga_list(input_list):
    return [make_oracle_sga(name, metric) for name, metric in input_list]


oracle_sga_fields = make_oracle_sga_list(
    [
        ("Maximum SGA Size", "oracle_sga_size"),
        ("Buffer Cache Size", "oracle_sga_buffer_cache"),
        ("Shared Pool Size", "oracle_sga_shared_pool"),
        ("Redo Buffers", "oracle_sga_redo_buffer"),
        ("Java Pool Size", "oracle_sga_java_pool"),
        ("Large Pool Size", "oracle_sga_large_pool"),
        ("Streams Pool Size", "oracle_sga_streams_pool"),
        ("Shared IO Pool Size", "oracle_sga_shared_io_pool"),
    ]
)


#
# PGAs
#
class OraclePGA(NamedTuple):
    name: str
    id: str
    metric: str


def make_oracle_pga(name):
    ident = _convert_to_identifier(name)
    metric = "oracle_pga_%s" % ident
    return OraclePGA(name, ident, metric)


def make_oracle_pga_list(name_list):
    return [make_oracle_pga(name) for name in name_list]


oracle_pga_fields = make_oracle_pga_list(
    [
        "total PGA allocated",
        "total PGA inuse",
        "total freeable PGA memory",
    ]
)
