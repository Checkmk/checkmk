# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from cmk.notification_plugins.pagerduty import pagerduty_msg


@pytest.mark.parametrize("context, result", [
    ({
        "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
        "PARAMETER_ROUTING_KEY": "routing_key\tsomehex",
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
        "SERVICEPERFDATA": "last_updated=20.599114;;;; new_files=0;;;;",
    }, {
        "dedup_key": "first/site1:127.0.0.1",
        "event_action": "trigger",
        "payload": {
            "custom_details": {
                "host": "site1",
                "host_address": "127.0.0.1",
                "info": "Service Down",
            },
            "severity": "critical",
            "source": "127.0.0.1",
            "summary": "CRITICAL: first on site1"
        },
        "routing_key": "somehex",
        "client": "Check_MK",
        "client_url": "http://localhost/testsite/view?key=val2",
    }),
    ({
        "HOSTOUTPUT": "Packet received via smart PING",
        "HOSTADDRESS": "10.3.1.239",
        "PARAMETER_ROUTING_KEY": "routing_key\tsomehex",
        "NOTIFICATIONTYPE": "RECOVERY",
        "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
        "HOSTNAME": "win7vm",
        "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
        "HOSTSTATE": "UP",
        "OMD_SITE": "heute",
        "MONITORING_HOST": "localhost",
        "WHAT": "HOST",
        "HOSTPERFDATA": "",
    }, {
        "client": "Check_MK",
        "client_url": "http://localhost/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
        "dedup_key": "win7vm:10.3.1.239",
        "event_action": "resolve",
        "payload": {
            "custom_details": {
                "host": "win7vm",
                "host_address": "10.3.1.239",
                "info": "Packet received via smart PING",
            },
            "severity": "info",
            "source": "10.3.1.239",
            "summary": "win7vm is UP"
        },
        "routing_key": "somehex",
    })
])
def test_pagerduty_message(context, result):
    msg = pagerduty_msg(context)
    assert msg == result
