# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from cmk.notification_plugins.slack import slack_msg


@pytest.mark.parametrize("context, result", [
    ({
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
        "WHAT": 'SERVICE',
        "CONTACTNAME": "John,Doe",
        "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
    }, {
        "attachments": [
            {
                "color":
                    "#EE0000",
                "title":
                    "Service PROBLEM notification",
                "text":
                    "Host: <http://localhost/testsite/view?key=val|site1> (IP: 127.0.0.1)\nService: <http://localhost/testsite/view?key=val2|first>\nState: CRITICAL",
            },
            {
                "color": "#EE0000",
                "title": "Additional Info",
                "text": "Service Down\nPlease take a look: @John, @Doe",
                "footer": "Check_MK notification: Wed Sep 19 15:29:14 CEST 2018",
            },
        ]
    }),
])
def test_slack_message(context, result):
    msg = slack_msg(context)
    assert msg == result
