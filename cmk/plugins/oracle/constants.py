#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Final


def _to_id(value: str) -> str:
    for char, repl in ((" ", "_"), ("/", ""), ("-", "_")):
        value = value.replace(char, repl)
    return value.lower()


@dataclass(frozen=True)
class OracleIOFile:
    name: str

    @property
    def id(self) -> str:
        return _to_id(self.name)


ORACLE_IO_FILES: Final = (
    OracleIOFile("Archive Log"),
    OracleIOFile("Archive Log Backup"),
    OracleIOFile("Control File"),
    OracleIOFile("Data File"),
    OracleIOFile("Data File Backup"),
    OracleIOFile("Data File Copy"),
    OracleIOFile("Data File Incremental Backup"),
    OracleIOFile("Data Pump Dump File"),
    OracleIOFile("External Table"),
    OracleIOFile("Flashback Log"),
    OracleIOFile("Log File"),
    OracleIOFile("Other"),
    OracleIOFile("Temp File"),
)


ORACLE_IO_SIZES: Final = (
    ("s", "Small"),
    ("l", "Large"),
)

ORACLE_IO_TYPES: Final = (
    ("r", "Reads", "1/s"),
    ("w", "Writes", "1/s"),
    ("rb", "Read Bytes", "bytes/s"),
    ("wb", "Write Bytes", "bytes/s"),
)


@dataclass(frozen=True)
class OracleWaitclass:
    name: str

    @property
    def id(self) -> str:
        return _to_id(self.name)

    @property
    def metric(self) -> str:
        return f"oracle_wait_class_{self.id}_waited"

    @property
    def metric_fg(self) -> str:
        return f"{self.metric}_fg"


ORACLE_WAITCLASSES: Final = (
    OracleWaitclass("Administrative"),
    OracleWaitclass("Application"),
    OracleWaitclass("Cluster"),
    OracleWaitclass("Commit"),
    OracleWaitclass("Concurrency"),
    OracleWaitclass("Configuration"),
    OracleWaitclass("Idle"),
    OracleWaitclass("Network"),
    OracleWaitclass("Other"),
    OracleWaitclass("Scheduler"),
    OracleWaitclass("System I/O"),
    OracleWaitclass("User I/O"),
)


@dataclass(frozen=True)
class OracleSGA:
    name: str
    metric: str

    @property
    def id(self) -> str:
        return _to_id(self.name)


ORACLE_SGA_FIELDS: Final = (
    OracleSGA("Maximum SGA Size", "oracle_sga_size"),
    OracleSGA("Buffer Cache Size", "oracle_sga_buffer_cache"),
    OracleSGA("Shared Pool Size", "oracle_sga_shared_pool"),
    OracleSGA("Redo Buffers", "oracle_sga_redo_buffer"),
    OracleSGA("Java Pool Size", "oracle_sga_java_pool"),
    OracleSGA("Large Pool Size", "oracle_sga_large_pool"),
    OracleSGA("Streams Pool Size", "oracle_sga_streams_pool"),
    OracleSGA("Shared IO Pool Size", "oracle_sga_shared_io_pool"),
)


@dataclass(frozen=True)
class OraclePGA:
    name: str

    @property
    def id(self) -> str:
        return _to_id(self.name)

    @property
    def metric(self) -> str:
        return f"oracle_pga_{self.id}"


ORACLE_PGA_FIELDS: Final = (
    OraclePGA("total PGA allocated"),
    OraclePGA("total PGA inuse"),
    OraclePGA("total freeable PGA memory"),
)
