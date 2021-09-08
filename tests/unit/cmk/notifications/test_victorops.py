#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins.victorops import victorops_msg


@pytest.mark.parametrize(
    "context, result",
    [
        (
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "SERVICEURL": "/view?key=val2",
                "HOSTNAME": "site1",
                "SERVICEDESC": "first",
                "SERVICESTATE": "CRITICAL",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "SERVICEOUTPUT": "Service Down",
                "WHAT": "SERVICE",
                "CONTACTNAME": "John,Doe",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "entity_display_name": "first on site1",
                "entity_id": "first/site1:127.0.0.1",
                "host_name": "site1",
                "message_type": "CRITICAL",
                "monitoring_tool": "Check_MK notification",
                "state_message": "Service Down\n\nhttp://localhost/testsite/view?key=val2",
            },
        ),
        (
            {
                "HOSTOUTPUT": "Packet received via smart PING",
                "HOSTADDRESS": "10.3.1.239",
                "NOTIFICATIONTYPE": "RECOVERY",
                "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
                "HOSTNAME": "win7vm",
                "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
                "HOSTSTATE": "UP",
                "OMD_SITE": "heute",
                "MONITORING_HOST": "localhost",
                "WHAT": "HOST",
            },
            {
                "entity_display_name": "win7vm is UP",
                "entity_id": "win7vm:10.3.1.239",
                "host_name": "win7vm",
                "message_type": "RECOVERY",
                "monitoring_tool": "Check_MK notification",
                "state_message": "Packet received via smart PING\n\nhttp://localhost/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
            },
        ),
    ],
)
def test_victorops_message(context, result):
    msg = victorops_msg(context)
    assert msg == result
