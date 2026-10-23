#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import base64
import email
import re
import shutil
import socket
import socketserver
import threading
from collections.abc import Callable, Iterator, Mapping
from email.mime.text import MIMEText
from pathlib import Path
from typing import override

import pytest
import responses
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from pytest_mock import MockerFixture

from cmk.notification_plugins import mail
from cmk.testlib.notification_plugins import exit_code, explicit_password
from cmk.utils.mail import InlineImageAttachment

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "mail"

HOSTNAME_ELEMENT = (
    "hostname",
    "both",
    True,
    "all",
    "Host",
    "$HOSTNAME$ ($HOSTALIAS$)",
)
SERVICEDESC_ELEMENT = (
    "servicedesc",
    "service",
    True,
    "all",
    "Service",
    "$SERVICEDESC$",
)

ALERTHANDLER_NAME_ELEMENT = (
    "alerthandler_name",
    "both",
    True,
    "alerthandler",
    "Name of alert handler",
    "$ALERTHANDLERNAME$",
)


@pytest.mark.parametrize(
    "args, expected",
    [
        (  # Show the hostname column in host notifications
            ("host", False, ["hostname"], [HOSTNAME_ELEMENT]),
            "Host:                $HOSTNAME$ ($HOSTALIAS$)\n",
        ),
        (  # Show the hostname column in service notifications
            ("service", False, ["hostname"], [HOSTNAME_ELEMENT]),
            "Host:                $HOSTNAME$ ($HOSTALIAS$)\n",
        ),
        (  # Don't show the servicedesc column in host notifications
            ("host", False, ["servicedesc"], [SERVICEDESC_ELEMENT]),
            "",
        ),
        (  # Show the servicedesc column in service notifications
            ("service", False, ["servicedesc"], [SERVICEDESC_ELEMENT]),
            "Service:             $SERVICEDESC$\n",
        ),
        (  # Columns are concatenated, the order is determined by the body elements
            (
                "service",
                False,
                ["servicedesc", "hostname"],
                [HOSTNAME_ELEMENT, SERVICEDESC_ELEMENT],
            ),
            "Host:                $HOSTNAME$ ($HOSTALIAS$)\nService:             $SERVICEDESC$\n",
        ),
        (  # Don't show the alerthandler_name if is_alert_handler is False
            ("service", False, ["alerthandler_name"], [ALERTHANDLER_NAME_ELEMENT]),
            "",
        ),
        (  # Show the alerthandler_name if is_alert_handler is True
            ("service", True, ["alerthandler_name"], [ALERTHANDLER_NAME_ELEMENT]),
            "Name of alert handler: $ALERTHANDLERNAME$\n",
        ),
    ],
)
def test_body_templates(
    args: tuple[str, bool, list[str], list[tuple[str, str, bool, str, str, str]]],
    expected: str,
) -> None:
    assert mail.body_templates(*args) == expected


def mock_service_context() -> dict[str, str]:
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
        "PARAMETER_URL_PREFIX_1": "automatic_http",
    }


SERVICE_CONTENT_TXT = """\
Host:                heute
Service:             CPU utilization
Event:               OK -> WARN
Address:             127.0.0.1
Time:                Wed Mar 20 16:51:46 CET 2019
Summary:             &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)
Details:             &lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)
another line\\nlast line
"""


# TODO: validate the HTML content
@pytest.mark.usefixtures("mocker")
def test_mail_content_from_service_context() -> None:
    # The items below are added by the mail plugin
    context = mock_service_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    # TODO remove if images are available on next build
    with pytest.raises((FileNotFoundError, TemplateNotFound)):
        content = mail.SingleEmailContent(mock_service_context)

        # The state markers (!) and (!!) as well as the states in EVENT_TXT have to be
        # replaced with HTML, but raw input from plug-ins has to be escaped.
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
            == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;Packet received via smart PING <b class="stmarkstate1">WARN</b>'
        )
        assert (
            content.context["SERVICEOUTPUT"]
            == "&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok (!)"
        )
        assert (
            content.context["SERVICEOUTPUT_HTML"]
            == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt; Ok <b class="stmarkstate1">WARN</b>'
        )
        assert (
            content.context["LONGSERVICEOUTPUT"]
            == "&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;(!)\nanother line\\nlast line"
        )
        assert (
            content.context["LONGSERVICEOUTPUT_HTML"]
            == '&lt;script&gt;console.log(&quot;evil&quot;);&lt;/script&gt;<b class="stmarkstate1">WARN</b><br>another line<br>last line'
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


def mock_host_context() -> dict[str, str]:
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
        "PARAMETER_URL_PREFIX_1": "automatic_https",
        "PREVIOUSHOSTHARDSHORTSTATE": "DOWN",
        "PREVIOUSHOSTHARDSTATE": "DOWN",
        "PREVIOUSHOSTHARDSTATEID": "1",
        "SHORTDATETIME": "2019-08-23 11:13:17",
        "WHAT": "HOST",
    }


HOST_CONTENT_TXT = """\
Host:                heute
Event:               DOWN -> UP
Address:             127.0.0.1
Time:                Fri Aug 23 11:13:17 CEST 2019
Summary:             Packet received via smart PING
"""


def test_mail_content_from_host_context(mocker: MockerFixture) -> None:
    mocker.patch("cmk.notification_plugins.mail.socket.getfqdn", lambda: "mysite.com")

    context = mock_host_context()
    assert "EVENT_TXT" not in context
    assert "EVENT_HTML" not in context
    assert "HOSTOUTPUT_HTML" not in context
    assert "SERVICEOUTPUT_HTML" not in context
    assert "LONGSERVICEOUTPUT_HTML" not in context
    assert "LINKEDHOSTNAME" not in context
    assert "LINKEDSERVICEDESC" not in context

    # TODO remove if images are available on next build
    with pytest.raises((FileNotFoundError, TemplateNotFound)):
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


def _render_event_overview(elements: list[str]) -> str:
    # Render the "Event overview" template in isolation. The selected ``elements``
    # (from the rule's "HTML email parameters") gate the optional Address/Site rows.
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["timestamp"] = mail.TemplateRenderer.format_timestamp
    macros = env.get_template("macros.html.jinja").module
    data = {
        "WHAT": "HOST",
        "HOSTADDRESS": "127.0.0.1",
        "OMD_SITE": "heute",
        "HOSTOUTPUT_HTML": "Packet received via smart PING",
        "LASTHOSTSTATECHANGE": "1552482625",
    }
    return env.get_template("event_overview.html.jinja").render(
        data=data,
        elements=elements,
        service_notification=False,
        macros=macros,
    )


def test_event_overview_omits_address_and_site_when_not_selected() -> None:
    html = _render_event_overview(["graph"])
    assert "Address:" not in html
    assert "Site:" not in html


def test_event_overview_shows_address_when_selected() -> None:
    html = _render_event_overview(["address"])
    assert "Address:" in html
    assert "127.0.0.1" in html
    assert "Site:" not in html


def test_event_overview_shows_site_when_selected() -> None:
    html = _render_event_overview(["omdsite"])
    assert "Site:" in html
    assert "heute" in html
    assert "Address:" not in html


def _render_event_overview_for_notification(notification_type: str) -> str:
    # Render the "Event overview" template for a specific notification type. The
    # alert handler name and output are only shown for alert handler notifications.
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["timestamp"] = mail.TemplateRenderer.format_timestamp
    macros = env.get_template("macros.html.jinja").module
    data = {
        "WHAT": "HOST",
        "NOTIFICATIONTYPE": notification_type,
        "HOSTOUTPUT_HTML": "Packet received via smart PING",
        "LASTHOSTSTATECHANGE": "1552482625",
        "ALERTHANDLERNAME": "My handler",
        "ALERTHANDLEROUTPUT": "Handler finished successfully",
    }
    return env.get_template("event_overview.html.jinja").render(
        data=data,
        elements=["graph"],
        service_notification=False,
        macros=macros,
    )


def test_event_overview_shows_alert_handler_details_for_alert_handler_notification() -> None:
    html = _render_event_overview_for_notification("ALERTHANDLER (0)")
    assert "Name of alert handler:" in html
    assert "My handler" in html
    assert "Output of alert handler:" in html
    assert "Handler finished successfully" in html


def test_event_overview_omits_alert_handler_details_for_regular_notification() -> None:
    html = _render_event_overview_for_notification("PROBLEM")
    assert "Name of alert handler:" not in html
    assert "Output of alert handler:" not in html


def _render_additional(elements: list[str], service_notification: bool) -> str:
    # Render the "Additional details" template in isolation. The selected
    # ``elements`` are passed via PARAMETER_ELEMENTSS, mirroring how the mail
    # plug-in feeds the rule's "HTML email parameters" into the template.
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["timestamp"] = mail.TemplateRenderer.format_timestamp
    macros = env.get_template("macros.html.jinja").module
    data = {
        "PARAMETER_ELEMENTSS": " ".join(elements),
        "HOSTNOTESURL": "http://host-notes",
        "SERVICENOTESURL": "http://service-notes",
    }
    return env.get_template("additional.html.jinja").render(
        data=data,
        service_notification=service_notification,
        macros=macros,
    )


def test_additional_shows_host_notes_url_for_host_notification() -> None:
    html = _render_additional(["notesurl"], service_notification=False)
    assert "Custom host notes URL:" in html
    assert "http://host-notes" in html
    assert "Custom service notes URL:" not in html


def test_additional_shows_both_notes_urls_for_service_notification() -> None:
    html = _render_additional(["notesurl"], service_notification=True)
    assert "Custom host notes URL:" in html
    assert "http://host-notes" in html
    assert "Custom service notes URL:" in html
    assert "http://service-notes" in html


_ICONS = (
    "checkmk_logo.png",
    "overview.png",
    "contact_groups.png",
    "graph.png",
    "additional.png",
    "label.png",
    "vector.png",
)


@pytest.fixture(name="mail_site_root")
def fixture_mail_site_root(site_root: Path) -> None:
    shutil.copytree(TEMPLATE_DIR, site_root / "share/check_mk/notifications/templates/mail")
    icons_dir = site_root / "share/check_mk/web/htdocs/images/icons"
    icons_dir.mkdir(parents=True)
    for icon in _ICONS:
        # The PNG signature lets the multipart mail detect the image type.
        (icons_dir / icon).write_bytes(b"\x89PNG\r\n\x1a\n")


def _host_context(**overrides: str) -> dict[str, str]:
    context = {
        "WHAT": "HOST",
        "NOTIFICATIONTYPE": "PROBLEM",
        "HOSTNAME": "heute",
        "HOSTALIAS": "heute",
        "HOSTADDRESS": "127.0.0.1",
        "HOSTOUTPUT": "No response <b>",
        "HOSTSTATE": "DOWN",
        "HOSTSHORTSTATE": "DOWN",
        "PREVIOUSHOSTHARDSTATE": "UP",
        "PREVIOUSHOSTHARDSHORTSTATE": "UP",
        "EVENT_TXT": "UP -> DOWN",
        "LONGDATETIME": "Fri Aug 23 11:13:17 CEST 2019",
        "SHORTDATETIME": "2019-08-23 11:13:17",
        "LASTHOSTSTATECHANGE": "1566551597",
        "HOSTURL": "/check_mk/index.py?host=heute",
        "OMD_SITE": "heute",
        "MONITORING_HOST": "mon",
        "CONTACTEMAIL": "test@example.com",
        "PARAMETER_FROM_ADDRESS": "from@example.com",
        "PARAMETER_ELEMENTSS": "abstime address",
    }
    context.update(overrides)
    return context


def _service_context(**overrides: str) -> dict[str, str]:
    context = _host_context(
        WHAT="SERVICE",
        SERVICEDESC="CPU load",
        SERVICEOUTPUT="load 5",
        LONGSERVICEOUTPUT="",
        SERVICESTATE="WARNING",
        SERVICESHORTSTATE="WARN",
        PREVIOUSSERVICEHARDSTATE="OK",
        PREVIOUSSERVICEHARDSHORTSTATE="OK",
        EVENT_TXT="OK -> WARN",
        SERVICEURL="/check_mk/index.py?service=cpu",
        LASTSERVICESTATECHANGE="1566551597",
    )
    context.update(overrides)
    return context


_HOST_TXT = """\
Host:                heute
Event:               UP -> DOWN
Address:             127.0.0.1
Time:                Fri Aug 23 11:13:17 CEST 2019
Summary:             No response &lt;b&gt;
"""


@pytest.mark.usefixtures("mail_site_root")
def test_host_mail_text_lists_forced_and_selected_elements() -> None:
    content = mail.SingleEmailContent(_host_context)

    assert content.content_txt == _HOST_TXT


@pytest.mark.usefixtures("mail_site_root")
def test_service_mail_text_includes_long_output_when_selected() -> None:
    content = mail.SingleEmailContent(
        lambda: _service_context(PARAMETER_ELEMENTSS="longoutput", LONGSERVICEOUTPUT="details")
    )

    assert content.content_txt == (
        "Host:                heute\n"
        "Service:             CPU load\n"
        "Event:               OK -> WARN\n"
        "Summary:             load 5\n"
        "Details:             details\n"
    )


@pytest.mark.usefixtures("mail_site_root")
def test_service_mail_html_breaks_long_output_lines() -> None:
    content = mail.SingleEmailContent(
        lambda: _service_context(
            PARAMETER_ELEMENTSS="longoutput", LONGSERVICEOUTPUT="line1\\nline2\nline3"
        )
    )

    assert "line1<br>line2<br>line3" in content.content_html


@pytest.mark.usefixtures("mail_site_root")
def test_default_elements_include_address_and_time() -> None:
    context = _host_context()
    del context["PARAMETER_ELEMENTSS"]

    content = mail.SingleEmailContent(lambda: context)

    assert content.content_txt == _HOST_TXT


# Without etc/omd/site.conf the Apache port lookup fails before any graph is requested.
@pytest.mark.usefixtures("mail_site_root")
@responses.activate
def test_graph_failure_is_reported_and_mail_is_sent_without_graphs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = mail.SingleEmailContent(lambda: _host_context(PARAMETER_ELEMENTSS="graph"))

    assert capsys.readouterr().err.startswith(
        "Failed to add graphs to mail. Continue without them."
    )
    assert [a.name for a in content.attachments] == [
        "checkmk_logo.png",
        "overview.png",
        "graph.png",
    ]


@pytest.mark.usefixtures("mail_site_root")
@responses.activate
def test_rendered_graphs_are_embedded_inline(graph_url: re.Pattern[str]) -> None:
    responses.get(graph_url, json={"result_code": 0, "result": ["YQ=="]})

    content = mail.SingleEmailContent(lambda: _host_context(PARAMETER_ELEMENTSS="graph"))

    assert InlineImageAttachment(name="heute-_HOST_-0.png", contents=b"a") in content.attachments
    assert 'src="cid:heute-_HOST_-0.png"' in content.content_html


@pytest.mark.usefixtures("mail_site_root")
def test_alert_handler_mail_does_not_fetch_graphs(capsys: pytest.CaptureFixture[str]) -> None:
    mail.SingleEmailContent(
        lambda: _host_context(
            NOTIFICATIONTYPE="ALERTHANDLER (0)",
            ALERTHANDLERNAME="restart",
            ALERTHANDLEROUTPUT="ok",
            PARAMETER_ELEMENTSS="graph",
        )
    )

    assert capsys.readouterr().err == ""


@pytest.mark.usefixtures("mail_site_root")
def test_alert_handler_mail_text_shows_handler_result() -> None:
    content = mail.SingleEmailContent(
        lambda: _host_context(
            NOTIFICATIONTYPE="ALERTHANDLER (0)",
            ALERTHANDLERNAME="restart",
            ALERTHANDLEROUTPUT="ok",
            PARAMETER_ELEMENTSS="",
        )
    )

    assert content.content_txt == (
        "Host:                heute\n"
        "Event:               UP -> DOWN\n"
        "Name of alert handler: restart\n"
        "Output of alert handler: ok\n"
    )


# fmt: off
@pytest.mark.parametrize(
    "make_context, overrides, expected_subject",
    [
        pytest.param(_host_context, {}, "Checkmk: heute - UP -> DOWN", id="host default"),
        pytest.param(_service_context, {}, "Checkmk: heute/CPU load OK -> WARN", id="service default"),
        pytest.param(_host_context, {"PARAMETER_HOST_SUBJECT": "$HOSTNAME$ is $HOSTSTATE$"}, "heute is DOWN", id="host custom"),
        pytest.param(_service_context, {"PARAMETER_SERVICE_SUBJECT": "$SERVICEDESC$: $SERVICESTATE$"}, "CPU load: WARNING", id="service custom"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("mail_site_root")
def test_mail_subject(
    make_context: Callable[[], dict[str, str]], overrides: dict[str, str], expected_subject: str
) -> None:
    content = mail.SingleEmailContent(lambda: make_context() | overrides)

    assert content.subject == expected_subject


@pytest.mark.usefixtures("mail_site_root")
def test_sender_and_reply_to_include_display_names() -> None:
    content = mail.SingleEmailContent(
        lambda: _host_context(
            PARAMETER_FROM_DISPLAY_NAME="Checkmk",
            PARAMETER_REPLY_TO_ADDRESS="reply@example.com",
            PARAMETER_REPLY_TO_DISPLAY_NAME="Ops",
        )
    )

    assert (content.from_address, content.reply_to) == (
        "Checkmk <from@example.com>",
        "Ops <reply@example.com>",
    )


@pytest.mark.usefixtures("mail_site_root")
def test_differing_host_alias_is_shown_next_to_hostname() -> None:
    content = mail.SingleEmailContent(lambda: _host_context(HOSTALIAS="Today"))

    assert content.content_txt.startswith("Host:                heute (Today)\n")


@pytest.mark.usefixtures("mail_site_root")
def test_custom_html_section_is_embedded() -> None:
    content = mail.SingleEmailContent(
        lambda: _host_context(PARAMETER_INSERT_HTML_SECTION="<h1>Hello</h1>")
    )

    assert "<h1>Hello</h1>" in content.content_html


@pytest.mark.usefixtures("mail_site_root")
def test_context_element_lists_all_variables() -> None:
    content = mail.SingleEmailContent(lambda: _host_context(PARAMETER_ELEMENTSS="context"))

    assert "Complete variable list: CONTACTEMAIL=test@example.com\n" in content.content_txt


@pytest.mark.usefixtures("mail_site_root")
def test_host_link_uses_configured_url_prefix() -> None:
    content = mail.SingleEmailContent(
        lambda: _host_context(PARAMETER_URL_PREFIX_1="automatic_https")
    )

    assert 'href="https://mon/heute/check_mk/index.py?host=heute"' in content.content_html


# fmt: off
@pytest.mark.parametrize(
    "parameters, expected_icons",
    [
        pytest.param({}, ["checkmk_logo.png", "overview.png"], id="always"),
        pytest.param({"PARAMETER_CONTACT_GROUPS": "1"}, ["checkmk_logo.png", "overview.png", "contact_groups.png"], id="contact groups"),
        pytest.param({"PARAMETER_ELEMENTSS": "omdsite hosttags"}, ["checkmk_logo.png", "overview.png", "additional.png"], id="additional details"),
        pytest.param({"PARAMETER_HOST_LABELS": "1"}, ["checkmk_logo.png", "overview.png", "label.png"], id="host labels"),
        pytest.param({"PARAMETER_SVC_LABELS": "1"}, ["checkmk_logo.png", "overview.png", "label.png"], id="service labels"),
        pytest.param({"PARAMETER_HOST_TAGS": "1"}, ["checkmk_logo.png", "overview.png", "vector.png"], id="host tags"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("mail_site_root")
def test_section_icons_are_attached_for_shown_sections(
    parameters: dict[str, str], expected_icons: list[str]
) -> None:
    content = mail.SingleEmailContent(lambda: _host_context(**parameters))

    assert [a.name for a in content.attachments] == expected_icons


@pytest.mark.usefixtures("mail_site_root")
def test_bulk_subject_counts_notifications() -> None:
    content = mail.BulkEmailContent(lambda: ({}, [_host_context(), _service_context()]))

    assert content.subject == "Check_MK: 2 notifications for heute"


@pytest.mark.usefixtures("mail_site_root")
def test_bulk_with_single_notification_uses_its_subject() -> None:
    content = mail.BulkEmailContent(lambda: ({}, [_host_context()]))

    assert content.subject == "Checkmk: heute - UP -> DOWN"


@pytest.mark.usefixtures("mail_site_root")
def test_bulk_text_concatenates_all_notifications() -> None:
    content = mail.BulkEmailContent(
        lambda: ({"PARAMETER_ELEMENTSS": "abstime address"}, [_host_context(), _host_context()])
    )

    assert content.content_txt == _HOST_TXT + _HOST_TXT


@pytest.mark.usefixtures("mail_site_root")
def test_bulk_html_has_a_single_footer() -> None:
    content = mail.BulkEmailContent(lambda: ({}, [_host_context(), _service_context()]))

    assert content.content_html.count("Sent by Checkmk") == 1


@pytest.mark.usefixtures("mail_site_root")
@responses.activate
def test_bulk_attaches_graphs_only_for_the_first_notifications(graph_url: re.Pattern[str]) -> None:
    responses.get(graph_url, json={"result_code": 0, "result": ["YQ=="]})

    content = mail.BulkEmailContent(
        lambda: (
            {"PARAMETER_ELEMENTSS": "graph", "PARAMETER_NOTIFICATIONS_WITH_GRAPHS": "1"},
            [_host_context(), _service_context()],
        )
    )

    assert [a.name for a in content.attachments if a.name.startswith("heute-")] == [
        "heute-_HOST_-0.png"
    ]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="BulkEmailContent reads PARAMETER_REPLY_TO, the rule sets PARAMETER_REPLY_TO_ADDRESS",
)
@pytest.mark.usefixtures("mail_site_root")
def test_bulk_reply_to_uses_configured_address() -> None:
    content = mail.BulkEmailContent(
        lambda: ({"PARAMETER_REPLY_TO_ADDRESS": "reply@example.com"}, [_host_context()])
    )

    assert content.reply_to == "reply@example.com"


def test_send_mail_without_smtp_port_spools_to_sendmail(
    fake_sendmail: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = mail.send_mail(MIMEText("hello"), "to@example.com", "from@example.com", {})

    assert (result, capsys.readouterr().out) == (
        0,
        "Spooled mail to local mail transmission agent\n",
    )
    assert "hello" in fake_sendmail.read_text()


@pytest.mark.usefixtures("failing_sendmail")
def test_send_mail_raises_when_sendmail_fails() -> None:
    with pytest.raises(RuntimeError, match="sendmail returned with exit code: 3; boom"):
        mail.send_mail(MIMEText("hello"), "to@example.com", "from@example.com", {})


class _FakeSmtpServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    # A failed login leaves the client connection open; do not wait for it on shutdown.
    block_on_close = False

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _FakeSmtpHandler)
        self.replies = {
            "EHLO": "250-fake.test\r\n250 AUTH PLAIN",
            "HELO": "250 fake.test",
            "AUTH": "235 accepted",
            "MAIL": "250 sender ok",
            "RCPT": "250 recipient ok",
            "DATA": "354 go ahead",
            "END_OF_DATA": "250 queued as 1",
            "RSET": "250 reset",
            "QUIT": "221 bye",
        }
        self.commands: list[str] = []
        self.messages: list[str] = []

    @property
    def port(self) -> int:
        return int(self.socket.getsockname()[1])


class _FakeSmtpHandler(socketserver.StreamRequestHandler):
    @override
    def setup(self) -> None:
        # Accepted sockets inherit the client-side default timeout; a lingering connection
        # must not time out later and print a traceback into another test's stderr.
        self.request.settimeout(None)
        super().setup()

    @override
    def handle(self) -> None:
        if not isinstance(self.server, _FakeSmtpServer):
            raise RuntimeError("handler is bound to the wrong server")
        server = self.server
        self._reply("220 fake.test ESMTP")
        while line := self.rfile.readline():
            command = line.decode().rstrip("\r\n")
            server.commands.append(command)
            verb = command.split(" ", 1)[0].upper()
            if verb == "DATA" and server.replies["DATA"].startswith("354"):
                self._reply(server.replies["DATA"])
                server.messages.append(self._read_data())
                self._reply(server.replies["END_OF_DATA"])
                continue
            self._reply(server.replies.get(verb, "500 unknown command"))
            if verb == "QUIT":
                return

    def _read_data(self) -> str:
        lines = []
        while (raw := self.rfile.readline()) and (line := raw.decode().rstrip("\r\n")) != ".":
            lines.append(line)
        return "\n".join(lines)

    def _reply(self, reply: str) -> None:
        self.wfile.write(reply.encode() + b"\r\n")


@pytest.fixture(name="smtp_server")
def fixture_smtp_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSmtpServer]:
    # smtplib asks for the local FQDN, a reverse DNS lookup that can hang in sandboxes.
    monkeypatch.setattr(socket, "getfqdn", lambda *_args: "client.test")
    server = _FakeSmtpServer()
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    # A dead fake server makes the client fail instead of hang. Set last, so that a failing
    # set-up cannot leave it behind.
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(5)
    yield server
    socket.setdefaulttimeout(previous_timeout)
    server.shutdown()
    server.server_close()


def _smtp_context(server: _FakeSmtpServer, **overrides: str) -> dict[str, str]:
    return {
        "PARAMETER_SMTP_PORT": str(server.port),
        "PARAMETER_SMTP_SMARTHOSTS_1": "127.0.0.1",
        **overrides,
    }


def test_send_mail_via_smtp_reports_server_reply(
    smtp_server: _FakeSmtpServer, capsys: pytest.CaptureFixture[str]
) -> None:
    result = mail.send_mail(
        MIMEText("hello"), "to@example.com", "from@example.com", _smtp_context(smtp_server)
    )

    assert (result, capsys.readouterr().out) == (0, "success 250 - queued as 1\n")


def test_send_mail_via_smtp_delivers_to_every_recipient(smtp_server: _FakeSmtpServer) -> None:
    mail.send_mail(
        MIMEText("hello"),
        "a@example.com,b@example.com",
        "from@example.com",
        _smtp_context(smtp_server),
    )

    assert [c.split(":", 1)[1] for c in smtp_server.commands if c.upper().startswith("RCPT")] == [
        "<a@example.com>",
        "<b@example.com>",
    ]


# fmt: off
@pytest.mark.parametrize(
    "replies, expected_result, expected_stderr",
    [
        pytest.param({"RCPT": "550 no such user"}, 2, 'mail from from@example.com" to "to@example.com" refused: 550, b\'no such user\'\n', id="recipient unknown"),
        pytest.param({"RCPT": "450 domain not found"}, 2, 'mail from from@example.com" to "to@example.com" refused: 450, b\'domain not found\'\n', id="recipient domain unknown"),
        pytest.param({"RCPT": "451 local error"}, 1, 'mail from from@example.com" to "to@example.com" refused: 451, b\'local error\'\n', id="recipient temporarily refused"),
        pytest.param({"MAIL": "553 sender rejected"}, 2, 'server didn\'t accept from-address "from@example.com" refused: sender rejected\n', id="sender refused"),
        pytest.param({"DATA": "554 rejected"}, 1, 'unexpected error code from "127.0.0.1": rejected\n', id="data refused"),
        pytest.param({"EHLO": "502 no", "HELO": "502 no"}, 1, 'protocol error from "127.0.0.1": no\n', id="greeting refused"),
    ],
)
# fmt: on
def test_send_mail_via_smtp_failure(
    replies: dict[str, str],
    expected_result: int,
    expected_stderr: str,
    smtp_server: _FakeSmtpServer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    smtp_server.replies.update(replies)

    result = mail.send_mail(
        MIMEText("hello"), "to@example.com", "from@example.com", _smtp_context(smtp_server)
    )

    assert (result, capsys.readouterr().err) == (expected_result, expected_stderr)


_SMTP_AUTH = {
    "PARAMETER_SMTP_AUTH_USER": "smtpuser",
    **explicit_password("PARAMETER_SMTP_AUTH_PASSWORD", "s3cret"),
}


def test_send_mail_via_smtp_logs_in_with_configured_credentials(
    smtp_server: _FakeSmtpServer,
) -> None:
    mail.send_mail(
        MIMEText("hello"),
        "to@example.com",
        "from@example.com",
        _smtp_context(smtp_server, **_SMTP_AUTH),
    )

    auth = [c.split(" ")[2] for c in smtp_server.commands if c.upper().startswith("AUTH PLAIN")]
    assert [base64.b64decode(a) for a in auth] == [b"\x00smtpuser\x00s3cret"]


def test_send_mail_via_smtp_rejected_login_is_final(
    smtp_server: _FakeSmtpServer, capsys: pytest.CaptureFixture[str]
) -> None:
    smtp_server.replies["AUTH"] = "535 bad credentials"

    result = mail.send_mail(
        MIMEText("hello"),
        "to@example.com",
        "from@example.com",
        _smtp_context(smtp_server, **_SMTP_AUTH),
    )

    assert (result, capsys.readouterr().err) == (
        2,
        'authentication failed on "127.0.0.1": bad credentials\n',
    )


def test_send_mail_via_smtp_without_smarthost_is_final() -> None:
    result = mail.send_mail(
        MIMEText("hello"), "to@example.com", "from@example.com", {"PARAMETER_SMTP_PORT": "25"}
    )

    assert result == 2


@pytest.mark.xfail(
    strict=True,
    raises=ConnectionRefusedError,
    reason="a refused connection is not caught, so the next smarthost is never tried",
)
def test_send_mail_via_smtp_falls_back_to_next_smarthost(smtp_server: _FakeSmtpServer) -> None:
    context = _smtp_context(
        smtp_server,
        PARAMETER_SMTP_SMARTHOSTS_1="127.0.0.2",
        PARAMETER_SMTP_SMARTHOSTS_2="127.0.0.1",
    )

    # All smarthosts share PARAMETER_SMTP_PORT; bound but not listening refuses connections.
    with socket.socket() as refusing:
        refusing.bind(("127.0.0.2", smtp_server.port))
        result = mail.send_mail(MIMEText("hello"), "to@example.com", "from@example.com", context)

    assert result == 0


@pytest.mark.usefixtures("mail_site_root")
def test_main_sends_html_mail_and_exits_successfully(
    fake_sendmail: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context(_host_context())

    result = exit_code(mail.main)

    message = email.message_from_string(fake_sendmail.read_text())
    assert (result, message["Subject"]) == (0, "Checkmk: heute - UP -> DOWN")


@pytest.mark.usefixtures("mail_site_root", "fake_sendmail")
def test_main_rejects_empty_recipient(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context(_host_context(CONTACTEMAIL=""))

    assert (exit_code(mail.main), capsys.readouterr().err) == (
        2,
        "Cannot send HTML email: empty destination email address\n",
    )


@pytest.mark.usefixtures("mail_site_root", "failing_sendmail")
def test_main_send_failure_is_final(
    notify_context: Callable[[Mapping[str, str]], None], capsys: pytest.CaptureFixture[str]
) -> None:
    notify_context(_host_context())

    assert (exit_code(mail.main), capsys.readouterr().err) == (
        2,
        "Unhandled exception: sendmail returned with exit code: 3; boom\n; \n",
    )
