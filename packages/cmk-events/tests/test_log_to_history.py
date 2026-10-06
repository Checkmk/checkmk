#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.events.log_to_history import notification_result_message
from cmk.events.notification_result import (
    NotificationContext,
    NotificationPluginName,
    NotificationResultCode,
)


def test_notification_result_message() -> None:
    """Regression test for Werk #8783"""
    plugin = NotificationPluginName("bulk asciimail")
    exit_code = NotificationResultCode(0)
    output: list[str] = []
    actual = notification_result_message(
        plugin, NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"}), exit_code, output
    )
    fields = "harri;test;OK;bulk asciimail;;"
    expected = f"HOST NOTIFICATION RESULT: {fields}"
    assert actual == expected
