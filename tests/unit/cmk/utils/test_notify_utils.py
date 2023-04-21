#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest import MonkeyPatch

from tests.testlib import on_time

import livestatus

import cmk.utils.notify as notify


class FakeLocalConnection:
    sent_command = None
    timeout = None

    def command(self, command, site=None):
        self.__class__.sent_command = command

    def set_timeout(self, timeout):
        self.__class__.timeout = timeout


def test_log_to_history(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(livestatus, "LocalConnection", FakeLocalConnection)
    with on_time("2018-04-15 16:50", "CET"):
        notify.log_to_history("ä")

    assert FakeLocalConnection.sent_command == "[1523811000] LOG;ä"
    assert FakeLocalConnection.timeout == 2


def test_notification_result_message() -> None:
    """Regression test for Werk #8783"""
    plugin = notify.NotificationPluginName("bulk asciimail")
    exit_code = notify.NotificationResultCode(0)
    output: list[str] = []
    context = notify.NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"})
    actual = notify.notification_result_message(plugin, context, exit_code, output)
    expected = "{}: {};{};{};{};{};{}".format(
        "HOST NOTIFICATION RESULT",
        "harri",
        "test",
        "OK",
        "bulk asciimail",
        "",
        "",
    )
    assert actual == expected
