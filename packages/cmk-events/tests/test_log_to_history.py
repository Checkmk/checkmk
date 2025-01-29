#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import livestatus
import time_machine
from pytest import MonkeyPatch

from cmk.events.log_to_history import (
    log_to_history,
    notification_result_message,
    SanitizedLivestatusLogStr,
)
from cmk.events.notification_result import (
    NotificationContext,
    NotificationPluginName,
    NotificationResultCode,
)


class FakeLocalConnection:
    sent_command = None
    timeout = None

    def command(
        self,
        command: str,
        site: livestatus.SiteId | None = None,  # noqa: ARG002
    ) -> None:
        self.__class__.sent_command = command

    def set_timeout(self, timeout: int) -> None:
        self.__class__.timeout = timeout


def test_log_to_history(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(livestatus, "LocalConnection", FakeLocalConnection)
    with time_machine.travel(datetime.datetime(2018, 4, 15, 16, 50, tzinfo=ZoneInfo("UTC"))):
        log_to_history(SanitizedLivestatusLogStr("ä"))

    assert FakeLocalConnection.sent_command == "[1523811000] LOG;ä"
    assert FakeLocalConnection.timeout == 2


def test_notification_result_message() -> None:
    """Regression test for Werk #8783"""
    plugin = NotificationPluginName("bulk asciimail")
    exit_code = NotificationResultCode(0)
    output: list[str] = []
    actual = notification_result_message(
        plugin, NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"}), exit_code, output
    )
    fields = ";".join(
        (
            "harri",
            "test",
            "OK",
            "bulk asciimail",
            "",
            "",
        )
    )
    expected = f"HOST NOTIFICATION RESULT: {fields}"
    assert actual == expected
