#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.notification_plugins.cisco_webex_teams import cisco_webex_teams_msg


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
                "markdown": "#### Service PROBLEM notification"
                "  \nHost: <http://localhost/testsite/view?key=val|site1> (IP: 127.0.0.1)"
                "  \nService: <http://localhost/testsite/view?key=val2|first>"
                "  \nState: CRITICAL"
                "  \n#### Additional Info"
                "  \nService Down"
                "  \nPlease take a look: @John, @Doe"
                "  \nCheck_MK notification: Wed Sep 19 15:29:14 CEST 2018"
            },
        ),
        (
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "site1",
                "HOSTSTATE": "DOWN",
                "HOSTOUTPUT": "Manually set to Down by cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "WHAT": "HOST",
                "CONTACTNAME": "John",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
            },
            {
                "markdown": "#### Host PROBLEM notification"
                "  \nHost: <https://localhost/testsite/view?key=val|site1> (IP: 127.0.0.1)"
                "  \nState: DOWN  \n#### Additional Info"
                "  \nManually set to Down by cmkadmin"
                "  \nPlease take a look: @John"
                "  \nCheck_MK notification: Wed Sep 19 15:29:14 CEST 2018"
            },
        ),
    ],
)
def test_cisco_webex_teams_message(context, result):
    msg = cisco_webex_teams_msg(context)
    assert msg == result
