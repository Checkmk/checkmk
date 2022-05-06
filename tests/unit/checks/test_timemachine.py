#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import datetime

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

pytestmark = pytest.mark.checks


class MockedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2022, 5, 6, 14, 59, 40, 552190)


def test_discovery_timemachine_discovered_service(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    assert list(
        check.discovery_function("/Volumes/Backup/Backups.backupdb/macvm/2013-11-28-202610")
    ) == [Service()]


def test_discovery_timemachine_no_discovered_service(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    result = check.discovery_function("Unable to locate machine directory for host.")
    assert list(result) == []


def test_check_timemachine_state_ok(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    info = "/Volumes/Backup/Backups.backupdb/macvm/2022-05-05-202610"
    monkeypatch.setattr(datetime, "datetime", MockedDateTime)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = list(check.check_function(params={"age": (86400, 172800)}, section=info))
    assert result == [
        Result(state=State.OK, summary="Last backup was at 2022-05-05 20:26:10: 18 h ago")
    ]


def test_check_timemachine_state_crit(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    monkeypatch.setattr(datetime, "datetime", MockedDateTime)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = list(
        check.check_function(
            params={"age": (86400, 172800)},
            section="/Volumes/Backup/Backups.backupdb/macvm/2022-05-01-202610",
        )
    )
    assert result == [
        Result(
            state=State.CRIT,
            summary="Last backup was at 2022-05-01 20:26:10: 4.8 d ago (warn/crit at 24 h ago/2 d ago)",
        )
    ]


def test_check_timemachine_state_warn(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    monkeypatch.setattr(datetime, "datetime", MockedDateTime)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = list(
        check.check_function(
            params={"age": (86400, 172800)},
            section="/Volumes/Backup/Backups.backupdb/macvm/2022-05-04-202610",
        )
    )
    assert result == [
        Result(
            state=State.WARN,
            summary="Last backup was at 2022-05-04 20:26:10: 42 h ago (warn/crit at 24 h ago/2 d ago)",
        )
    ]


def test_check_agent_failure(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    info = "Unable to locate machine directory for host."
    result = list(check.check_function(params={"age": (86400, 172800)}, section=info))
    assert result == [
        Result(state=State.CRIT, summary=f"Backup seems to have failed, message was: {info}")
    ]


def test_check_future_backup_date(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    monkeypatch.setattr(datetime, "datetime", MockedDateTime)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = list(
        check.check_function(
            params={"age": (86400, 172800)},
            section="/Volumes/Backup/Backups.backupdb/macvm/2022-05-07-202610",
        )
    )
    assert result == [
        Result(
            state=State.UNKNOWN,
            summary="Timestamp of last backup is in the future: 2022-05-07 20:26:10",
        )
    ]
