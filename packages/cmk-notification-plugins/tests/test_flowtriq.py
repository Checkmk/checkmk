#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins.flowtriq import _flowtriq_msg


@pytest.mark.parametrize(
    "context, result",
    [
        (
            {
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "SERVICEURL": "/view?key=val2",
                "HOSTNAME": "site1",
                "HOSTADDRESS": "127.0.0.1",
                "SERVICEDESC": "CPU load",
                "SERVICESTATE": "CRITICAL",
                "SERVICEOUTPUT": "CPU load is critical",
                "NOTIFICATIONTYPE": "PROBLEM",
                "WHAT": "SERVICE",
            },
            {
                "source": "checkmk",
                "host": "site1",
                "host_address": "127.0.0.1",
                "service": "CPU load",
                "state": "CRITICAL",
                "output": "CPU load is critical",
                "notification_type": "PROBLEM",
                "url": "http://localhost/testsite/view?key=val2",
            },
        ),
        (
            {
                "PARAMETER_URL_PREFIX_1": "automatic_https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "webserver01",
                "HOSTADDRESS": "10.0.0.5",
                "HOSTSTATE": "DOWN",
                "HOSTOUTPUT": "PING CRITICAL - Packet loss = 100%",
                "NOTIFICATIONTYPE": "PROBLEM",
                "WHAT": "HOST",
            },
            {
                "source": "checkmk",
                "host": "webserver01",
                "host_address": "10.0.0.5",
                "service": "",
                "state": "DOWN",
                "output": "PING CRITICAL - Packet loss = 100%",
                "notification_type": "PROBLEM",
                "url": "https://localhost/testsite/view?key=val",
            },
        ),
        (
            {
                "HOSTNAME": "router01",
                "HOSTADDRESS": "192.168.1.1",
                "HOSTSTATE": "UP",
                "HOSTOUTPUT": "PING OK - Packet loss = 0%",
                "NOTIFICATIONTYPE": "RECOVERY",
                "WHAT": "HOST",
            },
            {
                "source": "checkmk",
                "host": "router01",
                "host_address": "192.168.1.1",
                "service": "",
                "state": "UP",
                "output": "PING OK - Packet loss = 0%",
                "notification_type": "RECOVERY",
            },
        ),
    ],
)
def test_flowtriq_message(context: dict[str, str], result: dict[str, str]) -> None:
    msg = _flowtriq_msg(context)
    assert msg == result
