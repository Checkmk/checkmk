#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based import timemachine

NOW = datetime.datetime(2022, 5, 6, 14, 59, 40, 552190)


def test_discovery_timemachine_discovered_service() -> None:
    assert list(
        timemachine.discover_timemachine("/Volumes/Backup/Backups.backupdb/macvm/2013-11-28-202610")
    ) == [Service()]


def test_discovery_timemachine_no_discovered_service() -> None:
    result = timemachine.discover_timemachine("Unable to locate machine directory for host.")
    assert not list(result)


def test_check_timemachine_state_ok() -> None:
    info = "/Volumes/Backup/Backups.backupdb/macvm/2022-05-05-202610"
    result = list(timemachine._check(now=NOW, params={"age": (86400, 172800)}, section=info))
    assert result == [
        Result(
            state=State.OK,
            summary="Last backup was at 2022-05-05 20:26:10: 18 hours 33 minutes ago",
        )
    ]


def test_check_timemachine_state_ok_with_suffix() -> None:
    info = "/Volumes/.timemachine/ACB123AB-C123-ABC1-23AB-C123ABC123AB/2022-05-05-202610.backup/2022-05-05-202610.backup"
    result = list(timemachine._check(now=NOW, params={"age": (86400, 172800)}, section=info))
    assert result == [
        Result(
            state=State.OK,
            summary="Last backup was at 2022-05-05 20:26:10: 18 hours 33 minutes ago",
        )
    ]


def test_check_timemachine_state_crit(monkeypatch: pytest.MonkeyPatch) -> None:
    section = "/Volumes/Backup/Backups.backupdb/macvm/2022-05-01-202610"
    result = list(timemachine._check(now=NOW, params={"age": (86400, 172800)}, section=section))
    assert result == [
        Result(
            state=State.CRIT,
            summary="Last backup was at 2022-05-01 20:26:10: 4 days 18 hours ago (warn/crit at 1 day 0 hours ago/2 days 0 hours ago)",
        )
    ]


def test_check_timemachine_state_warn() -> None:
    section = "/Volumes/Backup/Backups.backupdb/macvm/2022-05-04-202610"
    result = list(timemachine._check(now=NOW, params={"age": (86400, 172800)}, section=section))
    assert result == [
        Result(
            state=State.WARN,
            summary="Last backup was at 2022-05-04 20:26:10: 1 day 18 hours ago (warn/crit at 1 day 0 hours ago/2 days 0 hours ago)",
        )
    ]


def test_check_agent_failure() -> None:
    info = "Unable to locate machine directory for host."
    result = list(timemachine.check_timemachine(params={"age": (86400, 172800)}, section=info))
    assert result == [
        Result(state=State.CRIT, summary=f"Backup seems to have failed, message was: {info}")
    ]


def test_check_future_backup_date() -> None:
    section = "/Volumes/Backup/Backups.backupdb/macvm/2022-05-07-202610"
    result = list(timemachine._check(now=NOW, params={"age": (86400, 172800)}, section=section))
    assert result == [
        Result(
            state=State.UNKNOWN,
            summary="Timestamp of last backup is in the future: 2022-05-07 20:26:10",
        )
    ]
