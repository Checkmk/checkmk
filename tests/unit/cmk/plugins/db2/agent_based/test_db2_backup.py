#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime

import pytest
import time_machine

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State
from cmk.plugins.db2.agent_based.db2_backup import check_db2_backup, discover_db2_backup
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

SECTION = parse_db2_dbs(
    [
        ["[[[db2taddm:CMDBS1]]]"],
        ["2015-03-12-04.00.13.000000"],
        ["[[[db2taddm:NOBACKUP]]]"],
        ["-"],
        ["[[[db2taddm:GARBAGE]]]"],
        ["yesterday"],
        ["[[[db2taddm:LOGINFAILED]]]"],
    ]
)


def test_every_database_is_discovered() -> None:
    assert list(discover_db2_backup(SECTION)) == [
        Service(item="db2taddm:CMDBS1"),
        Service(item="db2taddm:NOBACKUP"),
        Service(item="db2taddm:GARBAGE"),
        Service(item="db2taddm:LOGINFAILED"),
    ]


def test_backup_older_than_warn_level_is_warn() -> None:
    # The agent reports local time, so freeze the clock relative to it.
    with time_machine.travel(datetime.datetime(2015, 3, 13, 4, 0, 13).astimezone(), tick=False):
        results = list(check_db2_backup("db2taddm:CMDBS1", {"levels": (3600, 2 * 86400)}, SECTION))

    assert results == [
        Result(
            state=State.WARN,
            summary="Time since last backup: 1 day 0 hours (warn/crit at 1 hour 0 minutes/2 days 0 hours)",
        ),
    ]


def test_missing_backup_is_warn() -> None:
    assert list(check_db2_backup("db2taddm:NOBACKUP", {"levels": (1, 2)}, SECTION)) == [
        Result(state=State.WARN, summary="No backup available"),
    ]


def test_invalid_timestamp_is_unknown() -> None:
    assert list(check_db2_backup("db2taddm:GARBAGE", {"levels": (1, 2)}, SECTION)) == [
        Result(state=State.UNKNOWN, summary="Last backup contains an invalid timestamp: yesterday"),
    ]


def test_database_without_data_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_db2_backup("db2taddm:LOGINFAILED", {"levels": (1, 2)}, SECTION))
