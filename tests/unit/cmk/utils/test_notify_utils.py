#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import cmk.utils.notify as notify


def test_notification_result_message():
    """Regression test for Werk #8783"""
    plugin = notify.NotificationPluginName("bulk asciimail")
    exit_code = notify.NotificationResultCode(0)
    output: List[str] = []
    context = notify.NotificationContext({"CONTACTNAME": "harri", "HOSTNAME": "test"})
    actual = notify.notification_result_message(plugin, context, exit_code, output)
    expected = "%s: %s;%s;%s;%s;%s;%s" % (
        "HOST NOTIFICATION RESULT",
        "harri",
        "test",
        "OK",
        "bulk asciimail",
        "",
        "",
    )
    assert actual == expected
