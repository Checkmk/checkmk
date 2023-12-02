#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib import on_time

from cmk.base.plugins.agent_based import mssql_backup as msb
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

STRING_TABLE = [
    ["MSSQL_SQL0x4", "master", "2016-07-08 20:20:27", "D"],
    ["MSSQL_SQL0x4", "model", "2016-07-08 20:20:28", "D"],
    ["MSSQL_SQL0x4", "model", "2016-07-12 09:09:42", "L"],
    ["MSSQL_SQL0x4", "model", "2016-07-11 20:20:07", "I"],
    ["MSSQL_SQL0x4", "msdb", "2016-07-08", "20:20:43", "D"],
    ["MSSQL_SQL0x4", "msdb", "-", "-", "-", "no backup found"],
    ["MSSQL_SQL0x4", "foo"],
    ["MSSQL_SQL0x4", "bar", "12345678"],
    ["MSSQL_Parrot", "Polly", "-", "-", "-", "ERROR: Polly has no crackers"],
]


def _get_section() -> msb.Section:
    return msb.parse_mssql_backup(STRING_TABLE)


def test_discovery_default() -> None:
    assert sorted(msb.discover_mssql_backup({"mode": "summary"}, _get_section())) == sorted(
        [
            Service(item="MSSQL_SQL0x4 master"),
            Service(item="MSSQL_SQL0x4 model"),
            Service(item="MSSQL_SQL0x4 msdb"),
            Service(item="MSSQL_SQL0x4 bar"),
            Service(item="MSSQL_Parrot Polly"),
        ]
    )
    assert not list(msb.discover_mssql_backup_per_type({"mode": "summary"}, _get_section()))


def test_discovery_single() -> None:
    assert not list(msb.discover_mssql_backup({"mode": "per_type"}, _get_section()))
    assert sorted(
        msb.discover_mssql_backup_per_type({"mode": "per_type"}, _get_section())
    ) == sorted(
        [
            Service(item="MSSQL_SQL0x4 master Database"),
            Service(item="MSSQL_SQL0x4 model Database"),
            Service(item="MSSQL_SQL0x4 model Database Diff"),
            Service(item="MSSQL_SQL0x4 model Log"),
            Service(item="MSSQL_SQL0x4 msdb Database"),
            Service(item="MSSQL_SQL0x4 msdb Unspecific"),
            Service(item="MSSQL_SQL0x4 bar UNKNOWN"),
            Service(item="MSSQL_Parrot Polly Unspecific"),
        ]
    )


def test_check() -> None:
    with on_time("2016-07-15", "UTC"):
        assert list(msb.check_mssql_backup("MSSQL_SQL0x4 master", {}, _get_section())) == [
            Result(state=State.OK, summary="[database] Last backup: 2016-07-08 20:20:27"),
            Result(state=State.OK, summary="Time since last backup: 6 days 3 hours"),
            Metric("backup_age_database", 531573.0),
        ]


def test_check_with_seconds_metric() -> None:
    with on_time("2016-07-15", "UTC"):
        assert list(msb.check_mssql_backup("MSSQL_SQL0x4 bar", {}, _get_section())) == [
            Result(state=State.OK, summary="[database] Last backup: 1970-05-23 21:21:18"),
            Result(state=State.OK, summary="Time since last backup: 46 years 64 days"),
            Metric("seconds", 1456195122.0),
        ]


def test_check_error() -> None:
    assert list(msb.check_mssql_backup("MSSQL_Parrot Polly", {}, _get_section())) == [
        Result(state=State.CRIT, summary="Polly has no crackers"),
    ]
