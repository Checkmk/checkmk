#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.notification_plugins.mail as mail


@pytest.mark.parametrize(
    "notification_type, expected",
    [
        (
            "PROBLEM",
            (
                "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
                '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; <span class="state$@STATE$">$@STATE$</span>',
            ),
        ),
        (
            "RECOVERY",
            (
                "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
                '<span class="state$PREVIOUS@HARDSTATE$">$PREVIOUS@HARDSTATE$</span> &rarr; <span class="state$@STATE$">$@STATE$</span>',
            ),
        ),
        (
            "FLAPPINGSTART",
            (
                "Started Flapping",
                "Started Flapping",
            ),
        ),
        (
            "FLAPPINGSTOP",
            (
                "Stopped Flapping ($@SHORTSTATE$)",
                'Stopped Flapping (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "FLAPPINGDISABLED",
            (
                "Disabled Flapping ($@SHORTSTATE$)",
                'Disabled Flapping (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "DOWNTIMESTART",
            (
                "Downtime Start ($@SHORTSTATE$)",
                'Downtime Start (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "DOWNTIMEEND",
            (
                "Downtime End ($@SHORTSTATE$)",
                'Downtime End (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "DOWNTIMECANCELLED",
            (
                "Downtime Cancelled ($@SHORTSTATE$)",
                'Downtime Cancelled (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "ACKNOWLEDGEMENT",
            (
                "Acknowledged ($@SHORTSTATE$)",
                'Acknowledged (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "CUSTOM",
            (
                "Custom Notification ($@SHORTSTATE$)",
                'Custom Notification (while <span class="state$@STATE$">$@STATE$</span>)',
            ),
        ),
        (
            "ALERTHANDLER (OK)",
            (
                "ALERTHANDLER (OK)",
                "ALERTHANDLER (OK)",
            ),
        ),
        (
            "UNKNOWN",
            (
                "UNKNOWN",
                "UNKNOWN",
            ),
        ),
    ],
)
def test_event_templates(notification_type, expected):
    assert mail.event_templates(notification_type) == expected


HOSTNAME_ELEMENT = (
    "hostname",
    "both",
    True,
    "all",
    "Host",
    "$HOSTNAME$ ($HOSTALIAS$)",
    "$LINKEDHOSTNAME$ ($HOSTALIAS$)",
)
SERVICEDESC_ELEMENT = (
    "servicedesc",
    "service",
    True,
    "all",
    "Service",
    "$SERVICEDESC$",
    "$LINKEDSERVICEDESC$",
)

ALERTHANDLER_NAME_ELEMENT = (
    "alerthandler_name",
    "both",
    True,
    "alerthandler",
    "Name of alert handler",
    "$ALERTHANDLERNAME$",
    "$ALERTHANDLERNAME$",
)


@pytest.mark.parametrize(
    "args, expected",
    [
        (  # Show the hostname column in host notifications
            ("host", False, ["hostname"], [HOSTNAME_ELEMENT]),
            (
                "Host:                $HOSTNAME$ ($HOSTALIAS$)\n",
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr>',
            ),
        ),
        (  # Show the hostname column in service notifications
            ("service", False, ["hostname"], [HOSTNAME_ELEMENT]),
            (
                "Host:                $HOSTNAME$ ($HOSTALIAS$)\n",
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr>',
            ),
        ),
        (  # Don't show the servicedesc column in host notifications
            ("host", False, ["servicedesc"], [SERVICEDESC_ELEMENT]),
            ("", ""),
        ),
        (  # Show the servicedesc column in service notifications
            ("service", False, ["servicedesc"], [SERVICEDESC_ELEMENT]),
            (
                "Service:             $SERVICEDESC$\n",
                '<tr class="even0"><td class=left>Service</td><td>$LINKEDSERVICEDESC$</td></tr>',
            ),
        ),
        (  # Columns are concatenated, the order is determined by the body elements
            (
                "service",
                False,
                ["servicedesc", "hostname"],
                [HOSTNAME_ELEMENT, SERVICEDESC_ELEMENT],
            ),
            (
                "Host:                $HOSTNAME$ ($HOSTALIAS$)\nService:             $SERVICEDESC$\n",
                '<tr class="even0"><td class=left>Host</td><td>$LINKEDHOSTNAME$ ($HOSTALIAS$)</td></tr><tr class="odd0"><td class=left>Service</td><td>$LINKEDSERVICEDESC$</td></tr>',
            ),
        ),
        (  # Don't show the alerthandler_name if is_alert_handler is False
            ("service", False, ["alerthandler_name"], [ALERTHANDLER_NAME_ELEMENT]),
            ("", ""),
        ),
        (  # Show the alerthandler_name if is_alert_handler is True
            ("service", True, ["alerthandler_name"], [ALERTHANDLER_NAME_ELEMENT]),
            (
                "Name of alert handler: $ALERTHANDLERNAME$\n",
                '<tr class="even0"><td class=left>Name of alert handler</td><td>$ALERTHANDLERNAME$</td></tr>',
            ),
        ),
    ],
)
def test_body_templates(args, expected):
    assert mail.body_templates(*args) == expected


def mock_service_context():
    return {
        "CONTACTALIAS": "cmkadmin",
        "CONTACTEMAIL": "test@abc.de",
        "CONTACTNAME": "cmkadmin",
        "CONTACTPAGER": "",
        "CONTACTS": "cmkadmin",
        "DATE": "2019-03-20",
        "HOSTACKAUTHOR": "",
        "HOSTACKCOMMENT": "",
        "HOSTADDRESS": "127.0.0.1",
        "HOSTALIAS": "heute",
        "HOSTATTEMPT": "1",
        "HOSTCHECKCOMMAND": "check-mk-host-smart",
        "HOSTCONTACTGROUPNAMES": "all",
        "HOSTDOWNTIME": "0",
        "HOSTFORURL": "heute",
        "HOSTGROUPNAMES": "check_mk",
        "HOSTNAME": "heute",
        "HOSTNOTES": "",
        "HOSTNOTESURL": "",
        "HOSTNOTIFICATIONNUMBER": "1",
        "HOSTOUTPUT": '<script>console.log("evil");</script>Packet received via smart PING (!)',
        "HOSTPERFDATA": "",
        "HOSTPROBLEMID": "0",
        "HOSTSHORTSTATE": "UP",
        "HOSTSTATE": "UP",
        "HOSTSTATEID": "0",
        "HOSTTAGS": "/wato/ cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp wato",
        "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute",
        "HOST_ADDRESS_4": "127.0.0.1",
        "HOST_ADDRESS_6": "",
        "HOST_ADDRESS_FAMILY": "4",
        "HOST_EC_CONTACT": "",
        "HOST_FILENAME": "/wato/hosts.mk",
        "HOST_SL": "",
        "HOST_TAGS": "/wato/ cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp wato",
        "LASTHOSTPROBLEMID": "0",
        "LASTHOSTSHORTSTATE": "UP",
        "LASTHOSTSTATE": "UP",
        "LASTHOSTSTATECHANGE": "1552482625",
        "LASTHOSTSTATECHANGE_REL": "7d 02:41:21",
        "LASTHOSTSTATEID": "0",
        "LASTHOSTUP": "1553097106",
        "LASTHOSTUP_REL": "0d 00:00:00",
        "LASTSERVICEOK": "1553097092",
        "LASTSERVICEOK_REL": "0d 00:00:14",
        "LASTSERVICEPROBLEMID": "171",
        "LASTSERVICESHORTSTATE": "OK",
        "LASTSERVICESTATE": "OK",
        "LASTSERVICESTATECHANGE": "1553097106",
        "LASTSERVICESTATECHANGE_REL": "0d 00:00:00",
        "LASTSERVICESTATEID": "0",
        "LOGDIR": "/omd/sites/heute/var/check_mk/notify",
        "LONGDATETIME": "Wed Mar 20 16:51:46 CET 2019",
        "LONGHOSTOUTPUT": "",
        "LONGSERVICEOUTPUT": '<script>console.log("evil");</script>(!)\nanother line\\nlast line',
        "MAIL_COMMAND": "mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
        "MAXHOSTATTEMPTS": "1",
        "MAXSERVICEATTEMPTS": "1",
        "MICROTIME": "1553097106779348",
        "MONITORING_HOST": "Klappschloss",
        "NOTIFICATIONAUTHOR": "",
        "NOTIFICATIONAUTHORALIAS": "",
        "NOTIFICATIONAUTHORNAME": "",
        "NOTIFICATIONCOMMENT": "",
        "NOTIFICATIONTYPE": "PROBLEM",
        "OMD_ROOT": "/omd/sites/heute",
        "OMD_SITE": "heute",
        "PARAMETER_INSERT_HTML_SECTION": "<h1>This is important</h1>\n",
        "PREVIOUSHOSTHARDSHORTSTATE": "UP",
        "PREVIOUSHOSTHARDSTATE": "UP",
        "PREVIOUSHOSTHARDSTATEID": "0",
        "PREVIOUSSERVICEHARDSHORTSTATE": "OK",
        "PREVIOUSSERVICEHARDSTATE": "OK",
        "PREVIOUSSERVICEHARDSTATEID": "0",
        "SERVICEACKAUTHOR": "",
        "SERVICEACKCOMMENT": "",
        "SERVICEATTEMPT": "1",
        "SERVICECHECKCOMMAND": "check_mk-kernel.util",
        "SERVICECONTACTGROUPNAMES": "all",
        "SERVICEDESC": "CPU utilization",
        "SERVICEDISPLAYNAME": "CPU utilization",
        "SERVICEDOWNTIME": "0",
        "SERVICEFORURL": "CPU%20utilization",
        "SERVICEGROUPNAMES": "",
        "SERVICENOTES": "",
        "SERVICENOTESURL": "",
        "SERVICENOTIFICATIONNUMBER": "1",
        "SERVICEOUTPUT": '<script>console.log("evil");</script> Ok (!)',
        "SERVICEPERFDATA": "",
        "SERVICEPROBLEMID": "171",
        "SERVICESHORTSTATE": "WARN",
        "SERVICESTATE": "WARNING",
        "SERVICESTATEID": "1",
        "SERVICEURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20utilization%26site%3Dheute",
        "SERVICE_EC_CONTACT": "",
        "SERVICE_SL": "",
        "SHORTDATETIME": "2019-03-20 16:51:46",
        "SUBJECT": "Check_MK: heute/CPU utilization OK -> WARN",
        "SVC_SL": "",
        "WHAT": "SERVICE",
        "PARAMETER_FROM_ADDRESS": "check_mk@myinstance.com",
        "PARAMETER_REPLY_TO_ADDRESS": "reply@myinstance.com",
        "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
    }


SERVICE_CONTENT_TXT = """\
Host:                heute (heute)
Service:             CPU utilization
Event:               OK -> WARN
Address:             127.0.0.1
Date / Time:         Wed Mar 20 16:51:46 CET 2019
Summary:             &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)
Details:             &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)
another line\\nlast line
Host Metrics:        \n\
Service Metrics:     \n\
"""


# TODO: validate the HTML content
def test_mail_content_from_service_context(mocker):
    # The items below are added by the mail plugin
    context = mock_service_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    content = mail.SingleEmailContent(mock_service_context)

    # The state markers (!) and (!!) as well as the states in EVENT_TXT have to be
    # replaced with HTML, but raw input from plugins has to be escaped.
    # LONGSERVICEOUTPUT_HTML additionally replaces '\n' and '\\n' by '<br>'.
    assert content.context["EVENT_TXT"] == "OK -> WARN"
    assert (
        content.context["EVENT_HTML"]
        == '<span class="stateOK">OK</span> &rarr; <span class="stateWARNING">WARNING</span>'
    )
    assert (
        content.context["HOSTOUTPUT"]
        == "&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;Packet received via smart PING (!)"
    )
    assert (
        content.context["HOSTOUTPUT_HTML"]
        == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;Packet received via smart PING <b class="stmarkWARNING">WARN</b>'
    )
    assert (
        content.context["SERVICEOUTPUT"]
        == "&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)"
    )
    assert (
        content.context["SERVICEOUTPUT_HTML"]
        == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok <b class="stmarkWARNING">WARN</b>'
    )
    assert (
        content.context["LONGSERVICEOUTPUT"]
        == "&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)\nanother line\\nlast line"
    )
    assert (
        content.context["LONGSERVICEOUTPUT_HTML"]
        == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;<b class="stmarkWARNING">WARN</b><br>another line<br>last line'
    )

    assert (
        content.context["LINKEDHOSTNAME"]
        == '<a href="http://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute">heute</a>'
    )
    assert (
        content.context["LINKEDSERVICEDESC"]
        == '<a href="http://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dservice%26host%3Dheute%26service%3DCPU%20utilization%26site%3Dheute">CPU utilization</a>'
    )

    assert content.mailto == "test@abc.de"
    assert content.subject == "Check_MK: heute/CPU utilization OK -> WARN"
    assert content.from_address == "check_mk@myinstance.com"
    assert content.reply_to == "reply@myinstance.com"
    assert content.content_txt == SERVICE_CONTENT_TXT
    assert content.attachments == []


def mock_host_context():
    return {
        "CONTACTALIAS": "cmkadmin",
        "CONTACTEMAIL": "test@abc.de",
        "CONTACTNAME": "cmkadmin",
        "CONTACTPAGER": "",
        "CONTACTS": "cmkadmin",
        "DATE": "2019-08-23",
        "HOSTACKAUTHOR": "",
        "HOSTACKCOMMENT": "",
        "HOSTADDRESS": "127.0.0.1",
        "HOSTALIAS": "heute",
        "HOSTATTEMPT": "1",
        "HOSTCHECKCOMMAND": "check-mk-host-smart",
        "HOSTCONTACTGROUPNAMES": "all",
        "HOSTDOWNTIME": "0",
        "HOSTFORURL": "heute",
        "HOSTGROUPNAMES": "check_mk",
        "HOSTNAME": "heute",
        "HOSTNOTES": "",
        "HOSTNOTESURL": "",
        "HOSTNOTIFICATIONNUMBER": "1",
        "HOSTOUTPUT": "Packet received via smart PING",
        "HOSTPERFDATA": "",
        "HOSTPROBLEMID": "10",
        "HOSTSHORTSTATE": "UP",
        "HOSTSTATE": "UP",
        "HOSTSTATEID": "0",
        "HOSTTAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute",
        "HOST_ADDRESS_4": "127.0.0.1",
        "HOST_ADDRESS_6": "",
        "HOST_ADDRESS_FAMILY": "4",
        "HOST_EC_CONTACT": "",
        "HOST_FILENAME": "/wato/hosts.mk",
        "HOST_SL": "",
        "HOST_TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
        "LASTHOSTPROBLEMID": "10",
        "LASTHOSTSHORTSTATE": "DOWN",
        "LASTHOSTSTATE": "DOWN",
        "LASTHOSTSTATECHANGE": "1566551597",
        "LASTHOSTSTATECHANGE_REL": "0d 00:00:00",
        "LASTHOSTSTATEID": "1",
        "LASTHOSTUP": "1566551597",
        "LASTHOSTUP_REL": "0d 00:00:00",
        "LOGDIR": "/omd/sites/heute/var/check_mk/notify",
        "LONGDATETIME": "Fri Aug 23 11:13:17 CEST 2019",
        "LONGHOSTOUTPUT": "",
        "MAIL_COMMAND": "mail -s '$SUBJECT$' '$CONTACTEMAIL$'",
        "MAXHOSTATTEMPTS": "1",
        "MICROTIME": "1566551597286646",
        "MONITORING_HOST": "Klappschloss",
        "NOTIFICATIONAUTHOR": "",
        "NOTIFICATIONAUTHORALIAS": "",
        "NOTIFICATIONAUTHORNAME": "",
        "NOTIFICATIONCOMMENT": "",
        "NOTIFICATIONTYPE": "RECOVERY",
        "OMD_ROOT": "/omd/sites/heute",
        "OMD_SITE": "heute",
        "PARAMETER_URL_PREFIX_AUTOMATIC": "https",
        "PREVIOUSHOSTHARDSHORTSTATE": "DOWN",
        "PREVIOUSHOSTHARDSTATE": "DOWN",
        "PREVIOUSHOSTHARDSTATEID": "1",
        "SHORTDATETIME": "2019-08-23 11:13:17",
        "WHAT": "HOST",
    }


HOST_CONTENT_TXT = """\
Host:                heute (heute)
Event:               DOWN -> UP
Address:             127.0.0.1
Date / Time:         Fri Aug 23 11:13:17 CEST 2019
Summary:             Packet received via smart PING
Metrics:             \n\
"""


def test_mail_content_from_host_context(mocker):
    mocker.patch("cmk.notification_plugins.mail.socket.getfqdn", lambda: "mysite.com")

    context = mock_host_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    content = mail.SingleEmailContent(mock_host_context)

    assert content.context["EVENT_TXT"] == "DOWN -> UP"
    assert (
        content.context["EVENT_HTML"]
        == '<span class="stateDOWN">DOWN</span> &rarr; <span class="stateUP">UP</span>'
    )
    assert content.context["HOSTOUTPUT"] == "Packet received via smart PING"
    assert content.context["HOSTOUTPUT_HTML"] == "Packet received via smart PING"
    assert "SERVICEOUTPUT" not in content.context
    assert "SERVICEOUTPUT_HTML" not in content.context
    assert "LONGSERVICEOUTPUT" not in content.context
    assert "LONGSERVICEOUTPUT_HTML" not in content.context

    assert (
        content.context["LINKEDHOSTNAME"]
        == '<a href="https://Klappschloss/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dheute%26site%3Dheute">heute</a>'
    )
    assert content.context["LINKEDSERVICEDESC"] == ""

    assert content.mailto == "test@abc.de"
    assert content.subject == "Check_MK: heute - DOWN -> UP"
    assert content.from_address == "NO_SITE@mysite.com"
    assert content.reply_to == ""
    assert content.content_txt == HOST_CONTENT_TXT
    assert content.attachments == []
