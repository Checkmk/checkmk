#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

pytestmark = pytest.mark.checks


def test_discovery_timemachine_discovered_service(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    assert list(
        check.discovery_function(
            section=[["/Volumes/Backup/Backups.backupdb/macvm/2013-11-28-202610"]]
        )
    ) == [Service()]


def test_discovery_timemachine_no_discovered_service(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    result = check.discovery_function(
        [["Unable", "to", "locate", "machine", "directory", "for", "host."]]
    )
    assert list(result) == []


def test_check_timemachine_state_ok(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    info = [["/Volumes/Backup/Backups.backupdb/macvm/2022-05-05-202610"]]

    def mock_time():
        return 1651836706.2052822

    monkeypatch.setattr(time, "time", mock_time)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = check.check_function(params={"age": (86400, 172800)}, section=info)
    assert list(result) == [
        Result(state=State.OK, summary="Last backup was at Thu May  5 20:26:10 2022 (17 h ago)")
    ]


def test_check_timemachine_state_crit(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]

    def mock_time():
        return 1651836706.2052822

    monkeypatch.setattr(time, "time", mock_time)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = check.check_function(
        params={"age": (86400, 172800)},
        section=[["/Volumes/Backup/Backups.backupdb/macvm/2022-05-01-202610"]],
    )
    assert list(result) == [
        Result(
            state=State.CRIT,
            summary="Last backup was at Sun May  1 20:26:10 2022 (4.7 d ago), more than 2 d ago",
        )
    ]


def test_check_timemachine_state_warn(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]

    def mock_time():
        return 1651836706.2052822

    monkeypatch.setattr(time, "time", mock_time)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = check.check_function(
        params={"age": (86400, 172800)},
        section=[["/Volumes/Backup/Backups.backupdb/macvm/2022-05-04-202610"]],
    )
    assert list(result) == [
        Result(
            state=State.WARN,
            summary="Last backup was at Wed May  4 20:26:10 2022 (41 h ago), more than 24 h ago",
        )
    ]


def test_check_agent_failure(fix_register: FixRegister):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]
    info = [["Unable", "to", "locate", "machine", "directory", "for", "host."]]
    result = check.check_function(params={"age": (86400, 172800)}, section=info)
    line = " ".join(info[0])
    assert list(result) == [
        Result(state=State.CRIT, summary="Backup seems to have failed, message was: " + line)
    ]


def test_check_future_backup_date(fix_register: FixRegister, monkeypatch):
    check = fix_register.check_plugins[CheckPluginName("timemachine")]

    def mock_time():
        return 1651836706.2052822

    monkeypatch.setattr(time, "time", mock_time)
    monkeypatch.setenv("TZ", "Europe/Berlin")
    result = check.check_function(
        params={"age": (86400, 172800)},
        section=[["/Volumes/Backup/Backups.backupdb/macvm/2022-05-07-202610"]],
    )
    assert list(result) == [
        Result(
            state=State.UNKNOWN,
            summary="Timestamp of last backup is in the future: 2022-05-07-202610",
        )
    ]
