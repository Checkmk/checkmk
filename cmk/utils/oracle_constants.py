#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final, NamedTuple


def _convert_to_identifier(value: str) -> str:
    characters: Final = ((" ", "_"), ("/", ""), ("-", "_"))
    for char, repl in characters:
        value = value.replace(char, repl)
    return value.lower()


#
# IO Files
#
class OracleIOFile(NamedTuple):
    name: str
    id: str


def make_oracle_io_file_list(name_list: Sequence[str]) -> list[OracleIOFile]:
    return [OracleIOFile(name, _convert_to_identifier(name)) for name in name_list]


oracle_iofiles: Final = make_oracle_io_file_list(
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

oracle_io_sizes: Final = [
    ("s", "Small"),
    ("l", "Large"),
]

oracle_io_types: Final = [
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


def make_oracle_waitclass(name: str) -> OracleWaitclass:
    ident = _convert_to_identifier(name)
    metric = f"oracle_wait_class_{ident}_waited"
    metric_fg = f"{metric}_fg"
    return OracleWaitclass(name, ident, metric, metric_fg)


def make_oracle_waitclass_list(name_list: Sequence[str]) -> list[OracleWaitclass]:
    return [make_oracle_waitclass(name) for name in name_list]


oracle_waitclasses: Final = make_oracle_waitclass_list(
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


def make_oracle_sga(name: str, metric: str) -> OracleSGA:
    ident = _convert_to_identifier(name)
    return OracleSGA(name, ident, metric)


def make_oracle_sga_list(input_list: Sequence[tuple[str, str]]) -> list[OracleSGA]:
    return [make_oracle_sga(name, metric) for name, metric in input_list]


oracle_sga_fields: Final = make_oracle_sga_list(
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


def make_oracle_pga(name: str) -> OraclePGA:
    ident = _convert_to_identifier(name)
    metric = f"oracle_pga_{ident}"
    return OraclePGA(name, ident, metric)


def make_oracle_pga_list(name_list: Sequence[str]) -> list[OraclePGA]:
    return [make_oracle_pga(name) for name in name_list]


oracle_pga_fields: Final = make_oracle_pga_list(
    [
        "total PGA allocated",
        "total PGA inuse",
        "total freeable PGA memory",
    ]
)
