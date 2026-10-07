#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import binascii
import json
import re
import shlex
from collections.abc import Callable, Mapping, Sequence
from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
import requests
import responses
from pytest import MonkeyPatch

import cmk.utils.password_store
from cmk.ccc.exceptions import MKGeneralException
from cmk.notification_plugins import utils
from cmk.testlib.notification_plugins import exit_code, explicit_password


@pytest.mark.parametrize(
    "context, result",
    [
        (  # host context with url parameter
            {
                "PARAMETER_URL_PREFIX_1": "manual",
                "PARAMETER_URL_PREFIX_2": "https://host/site/check_mk",
                "HOSTURL": "/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
                "WHAT": "HOST",
            },
            "https://host/site/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_1": "automatic_https",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "WHAT": "SERVICE",
            },
            "https://localhost/testsite/view?key=val",
        ),
        (  # host context withour url parameter
            {
                "WHAT": "HOST",
            },
            "",
        ),
        (  # service context without url parameter
            {
                "WHAT": "SERVICE",
            },
            "",
        ),
    ],
)
def test_host_url_from_context(context: dict[str, str], result: str) -> None:
    host_url = utils.host_url_from_context(context)
    assert host_url == result


@pytest.mark.parametrize(
    "context, result",
    [
        (  # host context with url parameter
            {
                "PARAMETER_URL_PREFIX_1": "manual",
                "PARAMETER_URL_PREFIX_2": "https://host/site/check_mk",
                "WHAT": "HOST",
            },
            "",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "SERVICEURL": "/check_mk/index.py?start_url=view.py?view_name=service&host=test&service=foos&site=heute",
                "WHAT": "SERVICE",
            },
            "http://localhost/testsite/check_mk/index.py?start_url=view.py?view_name=service&host=test&service=foos&site=heute",
        ),
        (  # host context without url parameter
            {
                "HOSTURL": "/view?key=val",
                "HOSTNAME": "site2",
                "WHAT": "SERVICE",
            },
            "",
        ),
        (  # service context without url parameter
            {
                "WHAT": "SERVICE",
            },
            "",
        ),
    ],
)
def test_service_url_from_context(context: dict[str, str], result: str) -> None:
    service_url = utils.service_url_from_context(context)
    assert service_url == result


@pytest.mark.parametrize(
    "template, url, text, expected_link",
    [
        (
            "<%s|%s>",
            "https://host/site/view?key=val",
            "site",
            "<https://host/site/view?key=val|site>",
        ),
        (
            '<a href="%s">%s</a>',
            "http://localhost/testsite/view?key=val",
            "first",
            '<a href="http://localhost/testsite/view?key=val">first</a>',
        ),
        (
            '<a href="%s">%s</a>',
            "",
            "host1",
            "host1",
        ),
    ],
)
def test_format_link(template: str, url: str, text: str, expected_link: str) -> None:
    actual_link = utils.format_link(template, url, text)
    assert actual_link == expected_link


@pytest.mark.parametrize(
    "display_name, address, expected",
    [
        ("Harri Hirsch", "", ""),
        ("", "harri.hirsch@test.com", "harri.hirsch@test.com"),
        ("Harri Hirsch", "harri.hirsch@test.com", "Harri Hirsch <harri.hirsch@test.com>"),
        # encoded words if non ASCII characters are present:
        (
            "Härri Hürsch",
            "harri.hirsch@test.com",
            "=?utf-8?q?H=C3=A4rri H=C3=BCrsch?= <harri.hirsch@test.com>",
        ),
        # Surround the display name with double quotes if special characters like the '.' are present:
        (
            "Joe Q. Public",
            "john.q.public@example.com",
            '"Joe Q. Public" <john.q.public@example.com>',
        ),
        # Double quotes and backslashes in the display name have to be quoted:
        (
            'Giant; "Big" Box',
            "sysservices@example.net",
            '"Giant; \\"Big\\" Box" <sysservices@example.net>',
        ),
        (
            'Jöe Q. "Big"',
            "joe.q.big@test.com",
            '"=?utf-8?q?J=C3=B6e Q. \\"Big\\"?=" <joe.q.big@test.com>',
        ),
    ],
)
def test_format_address(display_name: str, address: str, expected: str) -> None:
    actual = utils.format_address(display_name, address)
    assert actual == expected


@pytest.mark.parametrize(
    "context, template, result",
    [
        (
            {"HOSTNAME": "localhost", "SERVICENOTESURL": "$HOSTNAME$ is on fire"},
            """
$HOSTNAME$
$SERVICENOTESURL$
$UNKNOWN$
""",
            "\nlocalhost\nlocalhost is on fire\n\n",
        ),
        (
            {"HOSTNAME": "localhost", "SERVICENOTESURL": "$HOSTNAME$"},
            "\n$CONTEXT_ASCII$\n$CONTEXT_HTML$",
            """
HOSTNAME=localhost
SERVICENOTESURL=localhost

<table class=context>
<tr><td class=varname>HOSTNAME</td><td class=value>localhost</td></tr>
<tr><td class=varname>SERVICENOTESURL</td><td class=value>localhost</td></tr>
</table>\n""",
        ),
    ],
)
def test_substitute_context(context: dict[str, str], template: str, result: str) -> None:
    assert result == utils.substitute_context(template, context)


def test_read_bulk_contents(monkeypatch: MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        (
            "key=val",
            "\n",
            "key2=val2",
            "a comment",
            "NOTIFICATIONTYPE=PROBLEM",
            "WHAT=HOST",
            "PREVIOUSHOSTHARDSHORTSTATE=UP",
            "HOSTSHORTSTATE=DOWN",
        ),
    )
    assert utils.read_bulk_contexts() == (
        {"key": "val"},
        [
            {
                "key2": "val2",
                "NOTIFICATIONTYPE": "PROBLEM",
                "WHAT": "HOST",
                "PREVIOUSHOSTHARDSHORTSTATE": "UP",
                "HOSTSHORTSTATE": "DOWN",
                "EVENT_TXT": "UP -> DOWN",
            }
        ],
    )
    assert capsys.readouterr().err == "Invalid line 'a comment' in bulked notification context\n"


@pytest.mark.parametrize(
    "context, hosts, result",
    [
        ([{"k": "y"}], ["local", "host"], "Check_MK: 1 notifications for 2 hosts"),
        ([{"k": "y"}, {"l": "p"}], ["first"], "Check_MK: 2 notifications for first"),
        (
            [
                {
                    "PARAMETER_BULK_SUBJECT": "Check_MK: $FOLDER$ gone $COUNT_HOSTS$ host",
                    "HOSTTAGS": "/wato/lan cmk-agent ip-v4 prod site:heute tcp wato",
                }
            ],
            ["first"],
            "Check_MK: lan gone 1 host",
        ),
    ],
)
def test_get_bulk_notification_subject(
    context: list[dict[str, str]], hosts: Sequence[str], result: str
) -> None:
    assert utils.get_bulk_notification_subject(context, hosts) == result


@pytest.mark.parametrize(
    "value, result",
    [
        ("http://local.host", "http://local.host"),
        ("webhook_url\thttp://webhook.host", "http://webhook.host"),
        ("store\tpwservice", "http://secret.host"),
    ],
)
def test_api_endpoint_url(monkeypatch: MonkeyPatch, value: str, result: str) -> None:
    monkeypatch.setattr("cmk.utils.password_store.extract", lambda _x: "http://secret.host")
    assert utils.retrieve_from_passwordstore(value) == result


@pytest.mark.parametrize(
    "input_context,expected_context",
    [
        # If not explicitly allowed as unescaped...
        (
            {
                "CONTACTALIAS": "d&d&+$@example.com",
                "CONTACTNAME": "d&d&+$@example.com",
                "CONTACTEMAIL": "d&d&+$@example.com",
                "PARAMETER_HOST_SUBJECT": "$HOSTALIAS$ > $HOSTSTATE$ < $HOST_SERVERTYP$",
                "PARAMETER_SERVICE_SUBJECT": "<>&",
                "PARAMETER_BULK_SUBJECT": "<>&",
                "PARAMETER_INSERT_HTML_SECTION": "<h1>Important</h1>",
                "PARAMETER_FROM_ADDRESS": "Harri Hirsch <harri.hirsch@test.de>",
                "PARAMETER_REPLY_TO": "Harri Hirsch <harri.hirsch@test.de>",
                "PARAMETER_REPLY_TO_ADDRESS": "d&d&+$@example.com",
            },
            {
                "CONTACTALIAS": "d&d&+$@example.com",
                "CONTACTNAME": "d&d&+$@example.com",
                "CONTACTEMAIL": "d&d&+$@example.com",
                "PARAMETER_HOST_SUBJECT": "$HOSTALIAS$ > $HOSTSTATE$ < $HOST_SERVERTYP$",
                "PARAMETER_SERVICE_SUBJECT": "<>&",
                "PARAMETER_BULK_SUBJECT": "<>&",
                "PARAMETER_INSERT_HTML_SECTION": "<h1>Important</h1>",
                "PARAMETER_FROM_ADDRESS": "Harri Hirsch <harri.hirsch@test.de>",
                "PARAMETER_REPLY_TO": "Harri Hirsch <harri.hirsch@test.de>",
                "PARAMETER_REPLY_TO_ADDRESS": "d&d&+$@example.com",
            },
        ),
        (
            {
                "PARAMETER_INSERT_HTML_SECTION": "<h1>Important</h1><script>alert(1)</script>",
            },
            {
                "PARAMETER_INSERT_HTML_SECTION": "<h1>Important</h1>&lt;script&gt;alert(1)&lt;/script&gt;",
            },
        ),
        # ... all variables will be escaped
        (
            {"FOO": "<h1>Important</h1>"},
            {"FOO": "&lt;h1&gt;Important&lt;/h1&gt;"},
        ),
        # Host and service output will be escaped:
        (
            {
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": "<h1>B</h1>",
                "HOSTOUTPUT": "<h1>C</h1>",
                "LONGHOSTOUTPUT": "<h1>D</h1>",
            },
            {
                "SERVICEOUTPUT": "&lt;h1&gt;A&lt;/h1&gt;",
                "LONGSERVICEOUTPUT": "&lt;h1&gt;B&lt;/h1&gt;",
                "HOSTOUTPUT": "&lt;h1&gt;C&lt;/h1&gt;",
                "LONGHOSTOUTPUT": "&lt;h1&gt;D&lt;/h1&gt;",
            },
        ),
        # if not disabled with the rule "HTML codes in service output" for services:
        (
            {
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": "<h1>B</h1>",
                "HOSTOUTPUT": "<h1>C</h1>",
                "LONGHOSTOUTPUT": "<h1>D</h1>",
                "SERVICE_ESCAPE_PLUGIN_OUTPUT": "0",  # variable set via the rule
            },
            {
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": "<h1>B</h1>",
                "HOSTOUTPUT": "&lt;h1&gt;C&lt;/h1&gt;",
                "LONGHOSTOUTPUT": "&lt;h1&gt;D&lt;/h1&gt;",
                "SERVICE_ESCAPE_PLUGIN_OUTPUT": "0",  # variable set via the rule
            },
        ),
        # or with the rule "HTML codes in host output" for hosts:
        (
            {
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": "<h1>B</h1>",
                "HOSTOUTPUT": "<h1>C</h1>",
                "LONGHOSTOUTPUT": "<h1>D</h1>",
                "HOST_ESCAPE_PLUGIN_OUTPUT": "0",  # variable set via the rule
            },
            {
                "SERVICEOUTPUT": "&lt;h1&gt;A&lt;/h1&gt;",
                "LONGSERVICEOUTPUT": "&lt;h1&gt;B&lt;/h1&gt;",
                "HOSTOUTPUT": "<h1>C</h1>",
                "LONGHOSTOUTPUT": "<h1>D</h1>",
                "HOST_ESCAPE_PLUGIN_OUTPUT": "0",  # variable set via the rule
            },
        ),
        # special case 'check_mk-ps' with HTML Long output
        (
            {
                "SERVICE_ESCAPE_PLUGIN_OUTPUT": "0",
                "SERVICECHECKCOMMAND": "check_mk-ps",
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": r"Processes: 1\nVirtual memory: 2.02 MiB\nResident memory: 10.2 MiB\nCPU: 0%\nProcess handles: 223\nRunning for: 11 days 12 hours\n<table><tr><th>name</th><th>user</th><th>virtual size</th><th>resident size</th><th>creation time</th><th>cpu usage (user space)</th><th>cpu usage (kernel space)</th><th>pid</th><th>cpu usage</th><th>pagefile usage</th><th>handle count</th></tr><tr><td>C:&bsol;Windows&bsol;system32&bsol;winlogon.exe</td><td>&bsol;&bsol;NT AUTHORITY&bsol;SYSTEM</td><td>2.02 MiB</td><td>10.2 MiB</td><td>Apr 20 2024 21:19:21</td><td>0.0%</td><td>0.0%</td><td>620</td><td>0.0%</td><td>2</td><td>223</td></tr></table>",
                "HOSTOUTPUT": "<h1>C</h1>",
                "LONGHOSTOUTPUT": "<h1>D</h1>",
            },
            {
                "SERVICECHECKCOMMAND": "check_mk-ps",
                "SERVICEOUTPUT": "<h1>A</h1>",
                "LONGSERVICEOUTPUT": r"Processes: 1\nVirtual memory: 2.02 MiB\nResident memory: 10.2 MiB\nCPU: 0%\nProcess handles: 223\nRunning for: 11 days 12 hours\n<table><tr><th>name</th><th>user</th><th>virtual size</th><th>resident size</th><th>creation time</th><th>cpu usage (user space)</th><th>cpu usage (kernel space)</th><th>pid</th><th>cpu usage</th><th>pagefile usage</th><th>handle count</th></tr><tr><td>C:\Windows\system32\winlogon.exe</td><td>\\NT AUTHORITY\SYSTEM</td><td>2.02 MiB</td><td>10.2 MiB</td><td>Apr 20 2024 21:19:21</td><td>0.0%</td><td>0.0%</td><td>620</td><td>0.0%</td><td>2</td><td>223</td></tr></table>",
                "HOSTOUTPUT": "&lt;h1&gt;C&lt;/h1&gt;",
                "LONGHOSTOUTPUT": "&lt;h1&gt;D&lt;/h1&gt;",
                "SERVICE_ESCAPE_PLUGIN_OUTPUT": "0",  # variable set via the rule
            },
        ),
    ],
)
def test_escape_context(input_context: dict[str, str], expected_context: Mapping[str, str]) -> None:
    escaped_context = utils.html_escape_context(input_context)
    assert escaped_context == expected_context


@pytest.mark.parametrize(
    "response, matchers, expected_exit_msg, expected_exit_code",
    [
        (
            Mock(requests.models.Response, status_code=HTTPStatus.OK, text="whatever"),
            [],
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(requests.models.Response, status_code=HTTPStatus.OK, text="whatever"),
            [
                (
                    utils.StatusCodeMatcher(range=(400, 500)),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(requests.models.Response, status_code=HTTPStatus.OK, text="whatever"),
            [
                (
                    utils.StatusCodeMatcher(range=(200, 300)),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "some title: whatever\n200: OK\n",
            0,
        ),
        (
            Mock(requests.models.Response, status_code=HTTPStatus.CREATED, text="whatever"),
            [
                (
                    utils.StatusCodeMatcher(range=(200, 300)),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "some title: whatever\n201: Created\n",
            0,
        ),
        (
            Mock(
                requests.models.Response, status_code=HTTPStatus.MULTIPLE_CHOICES, text="whatever"
            ),
            [
                (
                    utils.StatusCodeMatcher(range=(200, 300)),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "some title: whatever\n300: Multiple Choices\n",
            0,
        ),
        (
            Mock(
                requests.models.Response,
                status_code=HTTPStatus.OK,
                text="whatever",
                json=lambda: {"code": "all good"},
            ),
            [
                (
                    utils.JsonFieldMatcher(field="not_found", value="all good"),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(
                requests.models.Response,
                status_code=HTTPStatus.OK,
                text="whatever",
                json=lambda: {"code": "all good"},
            ),
            [
                (
                    utils.JsonFieldMatcher(field="code", value="wrong value"),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(
                requests.models.Response,
                status_code=HTTPStatus.OK,
                text="whatever",
                json=lambda: {"code": "all good"},
            ),
            [
                (
                    utils.JsonFieldMatcher(field="code", value="all good"),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "some title: whatever\n200: OK\n",
            0,
        ),
        (
            Mock(
                requests.models.Response,
                status_code=HTTPStatus.OK,
                text="whatever",
                json=lambda: {"code": "all good"},
            ),
            [
                (
                    utils.StatusCodeMatcher(range=(200, 300)).and_(
                        utils.JsonFieldMatcher(field="code", value="all good")
                    ),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "some title: whatever\n200: OK\n",
            0,
        ),
        (
            Mock(
                requests.models.Response,
                status_code=HTTPStatus.BAD_REQUEST,
                text="whatever",
                json=lambda: {"code": "all good"},
            ),
            [
                (
                    utils.StatusCodeMatcher(range=(200, 300)).and_(
                        utils.JsonFieldMatcher(field="code", value="all good")
                    ),
                    utils.StateInfo(state=0, type="str", title="some title"),
                ),
            ],
            "Details for Status Code are not defined\n400: Bad Request\n",
            3,
        ),
    ],
)
def test_process_by_matchers(
    response: Mock,
    matchers: list[tuple[utils.ResponseMatcher, utils.StateInfo]],
    expected_exit_msg: str,
    expected_exit_code: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as sys_exit:
        utils.process_by_matchers(response, matchers)
    assert sys_exit.value.code == expected_exit_code
    assert capsys.readouterr().err == expected_exit_msg


class SiteMock:
    def get_apache_port(self, _omd_root: object) -> int:
        return 80


class ResponseMock:
    def __init__(self, data: str) -> None:
        self.data = data

    @property
    def text(self) -> str:
        return self.data

    def json(self) -> dict | list:
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            raise requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)


class RequestsSessionMock:
    def __init__(self) -> None:
        self.data: str = ""
        self.side_effect: type[Exception] | None = None

    def __call__(self) -> object:
        return self

    def send(self, request: object, timeout: int) -> ResponseMock:  # noqa: ARG002
        if self.side_effect:
            raise self.side_effect
        return ResponseMock(self.data)


@patch("cmk.notification_plugins.utils.site", new=SiteMock())
def test_render_cmk_graphs(capsys: pytest.CaptureFixture) -> None:  # type: ignore[misc]
    context = {
        "HOSTNAME": "heute",
        "PARAMETER_GRAPHS_PER_NOTIFICATION": "1",
        "WHAT": "HOST",
    }
    with patch("cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()):
        assert utils.render_cmk_graphs(context=context) == []

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.side_effect = requests.exceptions.ReadTimeout
        assert utils.render_cmk_graphs(context=context) == []
        assert capsys.readouterr().err == (
            "ERROR: Timed out fetching graphs (10 sec)\n"
            "URL: http://localhost:80/NO_SITE/check_mk/ajax_graph_images.py?host=heute&service=_HOST_&num_graphs=1\n"
        )

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = "foo"
        assert utils.render_cmk_graphs(context=context) == []
        assert capsys.readouterr().err == (
            "ERROR: Failed to decode graphs: Expecting value: line 1 column 1 (char 0)\n"
            "URL: http://localhost:80/NO_SITE/check_mk/ajax_graph_images.py?host=heute&service=_HOST_&num_graphs=1\n"
            "Data: 'foo'\n"
        )

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '{"result_code": 0, "result": ["foo"], "severity": "success"}'
        with pytest.raises(binascii.Error):
            utils.render_cmk_graphs(context=context)

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '{"result_code": 0, "result": [""], "severity": "success"}'
        assert utils.render_cmk_graphs(context=context) == [utils.Graph("heute-_HOST_-0.png", b"")]
        assert capsys.readouterr().err == ""

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '{"result_code": 0, "result": ["YQ==", "Yg==", "Yw=="], "severity": "success"}'
        assert utils.render_cmk_graphs(context=context) == [
            utils.Graph("heute-_HOST_-0.png", b"a"),
            utils.Graph("heute-_HOST_-1.png", b"b"),
            utils.Graph("heute-_HOST_-2.png", b"c"),
        ]
        assert capsys.readouterr().err == ""

    context["WHAT"] = "SERVICE"
    context["SERVICEDESC"] = "Filesystem /boot"
    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '{"result_code": 0, "result": ["YQ==", "Yg=="], "severity": "success"}'
        assert utils.render_cmk_graphs(context=context) == [
            utils.Graph("heute-Filesystem_x47boot-0.png", b"a"),
            utils.Graph("heute-Filesystem_x47boot-1.png", b"b"),
        ]
        assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "notification_type, expected",
    [
        (
            "PROBLEM",
            "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
        ),
        (
            "RECOVERY",
            "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$",
        ),
        (
            "FLAPPINGSTART",
            "Started Flapping",
        ),
        (
            "FLAPPINGSTOP",
            "Stopped Flapping ($@SHORTSTATE$)",
        ),
        (
            "FLAPPINGDISABLED",
            "Disabled Flapping ($@SHORTSTATE$)",
        ),
        (
            "DOWNTIMESTART",
            "Downtime Start ($@SHORTSTATE$)",
        ),
        (
            "DOWNTIMEEND",
            "Downtime End ($@SHORTSTATE$)",
        ),
        (
            "DOWNTIMECANCELLED",
            "Downtime Cancelled ($@SHORTSTATE$)",
        ),
        (
            "ACKNOWLEDGEMENT",
            "Acknowledged ($@SHORTSTATE$)",
        ),
        (
            "CUSTOM",
            "Custom Notification ($@SHORTSTATE$)",
        ),
        (
            "ALERTHANDLER (OK)",
            "ALERTHANDLER (OK)",
        ),
        (
            "UNKNOWN",
            "UNKNOWN",
        ),
    ],
)
def test_event_text_templates(notification_type: str, expected: str) -> None:
    assert utils._event_text_template(notification_type) == expected  # noqa: SLF001


def test_collect_context_reads_notify_variables_and_adds_event_text(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("NOTIFY_WHAT", "HOST")
    monkeypatch.setenv("NOTIFY_NOTIFICATIONTYPE", "PROBLEM")
    monkeypatch.setenv("NOTIFY_PREVIOUSHOSTHARDSHORTSTATE", "UP")
    monkeypatch.setenv("NOTIFY_HOSTSHORTSTATE", "DOWN")
    monkeypatch.setenv("NOT_A_NOTIFICATION_VARIABLE", "ignored")

    assert utils.collect_context() == {
        "WHAT": "HOST",
        "NOTIFICATIONTYPE": "PROBLEM",
        "PREVIOUSHOSTHARDSHORTSTATE": "UP",
        "HOSTSHORTSTATE": "DOWN",
        "EVENT_TXT": "UP -> DOWN",
    }


_URL_CONTEXT = {
    "PARAMETER_URL_PREFIX_1": "automatic_https",
    "MONITORING_HOST": "mon",
    "OMD_SITE": "heute",
    "HOSTNAME": "host1",
    "SERVICEDESC": "CPU load",
}


# fmt: off
@pytest.mark.parametrize(
    "what, expected_url",
    [
        pytest.param("HOST", "https://mon/heute/check_mk/view.py?siteopt=heute&view_name=host_graphs&host=host1", id="host"),
        pytest.param("SERVICE", "https://mon/heute/check_mk/view.py?siteopt=heute&view_name=service_graphs&host=host1&service=CPU load", id="service"),
    ],
)
# fmt: on
def test_graph_url_from_context(what: str, expected_url: str) -> None:
    assert utils.graph_url_from_context({**_URL_CONTEXT, "WHAT": what}) == expected_url


def test_eventhistory_url_from_context_points_to_events_view() -> None:
    assert (
        utils.eventhistory_url_from_context(_URL_CONTEXT)
        == "https://mon/heute/check_mk/view.py?view_name=events"
    )


def test_manual_url_prefix_drops_check_mk_suffix() -> None:
    context = {
        "PARAMETER_URL_PREFIX_1": "manual",
        "PARAMETER_URL_PREFIX_2": "https://mon/heute/check_mk/",
        "HOSTURL": "/check_mk/index.py",
    }

    assert utils.host_url_from_context(context) == "https://mon/heute/check_mk/index.py"


def test_explicit_formspec_password_is_returned_as_is() -> None:
    password = list(explicit_password("PARAMETER_PASSWORD", "s3cret").values())

    assert utils.retrieve_from_passwordstore(password) == "s3cret"


@pytest.mark.usefixtures("site_root")
def test_stored_formspec_password_is_read_from_password_store() -> None:
    cmk.utils.password_store.save(
        {"my_pw": "s3cret"}, cmk.utils.password_store.pending_secrets_path_site()
    )

    assert (
        utils.retrieve_from_passwordstore(
            ["cmk_postprocessed", "stored_password", "my_pw\t", "my_pw", ""]
        )
        == "s3cret"
    )


@pytest.mark.usefixtures("site_root")
def test_stored_legacy_password_is_read_from_password_store() -> None:
    cmk.utils.password_store.save(
        {"my_pw": "s3cret"}, cmk.utils.password_store.pending_secrets_path_site()
    )

    assert utils.retrieve_from_passwordstore("store\tmy_pw") == "s3cret"


@pytest.mark.usefixtures("site_root")
def test_missing_stored_password_raises() -> None:
    with pytest.raises(MKGeneralException, match="Password not found"):
        utils.retrieve_from_passwordstore("store\tmissing")


def test_password_is_collected_from_context_keys_with_prefix() -> None:
    context = {
        **explicit_password("PARAMETER_PASSWORD", "from-context"),
        "PARAMETER_OTHER": "ignored",
    }

    assert utils.get_password_from_env_or_context("PARAMETER_PASSWORD", context) == "from-context"


def test_password_is_collected_from_environment_without_context(
    monkeypatch: MonkeyPatch,
) -> None:
    for key, value in explicit_password("NOTIFY_PARAMETER_PASSWORD", "from-env").items():
        monkeypatch.setenv(key, value)

    assert utils.get_password_from_env_or_context("NOTIFY_PARAMETER_PASSWORD") == "from-env"


_WEBHOOK_URL = "https://hook.example.com/notify"
_POST_CONTEXT = {"WHAT": "HOST", "NOTIFICATIONTYPE": "PROBLEM", "HOSTNAME": "host1"}


def _message(context: dict[str, str]) -> dict[str, str | object]:
    return {"text": f"{context['HOSTNAME']} is down"}


@responses.activate
def test_post_request_sends_message_to_webhook_from_context(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    responses.post(_WEBHOOK_URL)
    notify_context({**_POST_CONTEXT, "PARAMETER_WEBHOOK_URL": f"webhook_url\t{_WEBHOOK_URL}"})

    utils.post_request(_message)

    assert json.loads(responses.calls[0].request.body or b"") == {"text": "host1 is down"}


@responses.activate
def test_post_request_uses_given_url_and_headers(
    notify_context: Callable[[Mapping[str, str]], None],
) -> None:
    responses.post(_WEBHOOK_URL)
    notify_context(_POST_CONTEXT)

    utils.post_request(_message, url=_WEBHOOK_URL, headers={"X-Token": "abc"})

    assert responses.calls[0].request.headers["X-Token"] == "abc"


# fmt: off
@pytest.mark.parametrize(
    "error, expected_stderr",
    [
        pytest.param(requests.exceptions.ProxyError("refused"), "Cannot connect to proxy: http://***@proxy.lan:3128\n", id="proxy error"),
        pytest.param(requests.exceptions.ConnectTimeout("slow"), "Connection timeout in notification plugin \n", id="timeout"),
    ],
)
# fmt: on
@responses.activate
def test_post_request_connection_failure_is_final(
    error: requests.exceptions.RequestException,
    expected_stderr: str,
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    responses.post(_WEBHOOK_URL, body=error)
    notify_context({**_POST_CONTEXT, "PARAMETER_PROXY_URL": "http://user:secret@proxy.lan:3128"})

    result = exit_code(lambda: utils.post_request(_message, url=_WEBHOOK_URL))

    assert (result, capsys.readouterr().err) == (2, expected_stderr)


# fmt: off
@pytest.mark.parametrize(
    "status_code, success_code, expected_result",
    [
        pytest.param(HTTPStatus.OK, HTTPStatus.OK, 0, id="expected status"),
        pytest.param(HTTPStatus.ACCEPTED, {HTTPStatus.OK, HTTPStatus.ACCEPTED}, 0, id="one of expected statuses"),
        pytest.param(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.OK, 1, id="server error is retried"),
        pytest.param(HTTPStatus.BAD_REQUEST, {HTTPStatus.OK}, 2, id="client error is final"),
    ],
)
# fmt: on
def test_process_by_status_code_result(
    status_code: int, success_code: int | set[int], expected_result: int
) -> None:
    response = Mock(spec=requests.Response, status_code=status_code, text="details")

    assert utils.process_by_status_code(response, success_code) == expected_result


def test_process_by_status_code_reports_failed_response(
    capsys: pytest.CaptureFixture[str],
) -> None:
    response = Mock(spec=requests.Response, status_code=HTTPStatus.NOT_FOUND, text="nope")

    utils.process_by_status_code(response)

    assert capsys.readouterr().err == "Failed to send notification.\nResponse: nope\n404: Not Found"


def test_status_code_matcher_rejects_inverted_range() -> None:
    with pytest.raises(ValueError, match="Invalid range: 300 - 200"):
        utils.StatusCodeMatcher(range=(300, 200))


def test_extended_combined_matcher_requires_all_matchers() -> None:
    response = Mock(spec=requests.Response, status_code=HTTPStatus.OK)
    matcher = (
        utils.StatusCodeMatcher(range=(200, 299))
        .and_(utils.JsonFieldMatcher(field="ok", value=True))
        .and_(utils.JsonFieldMatcher(field="code", value="E1"))
    )

    assert matcher.matches(response, {"ok": True, "code": "E2"}) is False


def test_process_by_matchers_reports_nested_json_detail(
    capsys: pytest.CaptureFixture[str],
) -> None:
    response = Mock(
        spec=requests.Response,
        status_code=HTTPStatus.BAD_REQUEST,
        text="",
        json=lambda: {"error": {"message": "invalid key"}},
    )

    result = exit_code(
        lambda: utils.process_by_matchers(
            response, [((400, 499), utils.StateInfo(state=2, type="json", title="message"))]
        )
    )

    assert (result, capsys.readouterr().err) == (
        2,
        "message: invalid key\n400: Bad Request\n",
    )


def test_json_field_matcher_does_not_match_non_json_body(
    capsys: pytest.CaptureFixture[str],
) -> None:
    response = Mock(spec=requests.Response, status_code=HTTPStatus.OK, text="plain")
    response.json.side_effect = requests.JSONDecodeError("Expecting value", "plain", 0)

    exit_code(
        lambda: utils.process_by_matchers(
            response,
            [(utils.JsonFieldMatcher(field="ok", value=True), utils.StateInfo(0, "str", "ok"))],
        )
    )

    assert capsys.readouterr().err == "Details for Status Code are not defined\n200: OK\n"


# fmt: off
@pytest.mark.parametrize(
    "context, expected_message",
    [
        pytest.param({"WHAT": "SERVICE", "NOTIFICATIONTYPE": "PROBLEM", "SERVICESTATE": "CRITICAL", "SERVICEDESC": "CPU", "SERVICEOUTPUT": "high"}, "host1 CR CPU high", id="service problem"),
        pytest.param({"WHAT": "SERVICE", "NOTIFICATIONTYPE": "ACKNOWLEDGEMENT", "SERVICEDESC": "CPU", "NOTIFICATIONCOMMENT": "mine"}, "host1 CPU Acknowledged mine", id="service acknowledgement"),
        pytest.param({"WHAT": "HOST", "NOTIFICATIONTYPE": "RECOVERY", "HOSTSTATE": "UP"}, "host1 is UP", id="host recovery"),
        pytest.param({"WHAT": "HOST", "NOTIFICATIONTYPE": "FLAPPINGSTART"}, "host1  Started Flapping", id="flapping start"),
        pytest.param({"WHAT": "HOST", "NOTIFICATIONTYPE": "FLAPPINGSTOP"}, "host1  Stopped Flapping", id="flapping stop"),
        pytest.param({"WHAT": "HOST", "NOTIFICATIONTYPE": "DOWNTIMEEND", "NOTIFICATIONCOMMENT": "done"}, "host1  Downtime End done", id="downtime end"),
        pytest.param({"WHAT": "HOST", "NOTIFICATIONTYPE": "CUSTOM", "NOTIFICATIONCOMMENT": "hello"}, "host1  Custom Notification hello", id="custom"),
    ],
)
# fmt: on
def test_sms_message_from_context(context: dict[str, str], expected_message: str) -> None:
    assert utils.get_sms_message_from_context({"HOSTNAME": "host1", **context}) == expected_message


def test_sms_message_truncates_service_problem_to_160_characters() -> None:
    context = {
        "HOSTNAME": "host1",
        "WHAT": "SERVICE",
        "NOTIFICATIONTYPE": "PROBLEM",
        "SERVICESTATE": "CRITICAL",
        "SERVICEDESC": "CPU",
        "SERVICEOUTPUT": "x" * 200,
    }

    assert len(utils.get_sms_message_from_context(context)) == 160


@pytest.mark.parametrize(
    "max_length, expected",
    [
        pytest.param(None, "'it'\"'\"'s down'", id="unlimited"),
        pytest.param(8, "'it'\"'\"'", id="truncated"),
    ],
)
def test_quote_message_escapes_single_quotes(max_length: int | None, expected: str) -> None:
    assert utils.quote_message("it's down", max_length) == expected


@pytest.mark.xfail(
    strict=True, raises=ValueError, reason="truncation can cut through an escaped single quote"
)
def test_quote_message_truncation_keeps_shell_quoting_balanced() -> None:
    assert shlex.split(utils.quote_message("it's down", 6)) == ["it"]


@pytest.mark.parametrize(
    "notification_type, expected",
    [
        pytest.param("DOWNTIMESTART", "Downtime Start", id="downtime start"),
        pytest.param("DOWNTIMEEND", "Downtime End", id="downtime end"),
        pytest.param("DOWNTIMECANCELLED", "Downtime Cancelled", id="downtime cancelled"),
        pytest.param("FLAPPINGSTART", "Flapping Start", id="flapping start"),
        pytest.param("FLAPPINGSTOP", "Flapping Stop", id="flapping stop"),
        pytest.param("FLAPPINGDISABLED", "Flapping Disabled", id="flapping disabled"),
        pytest.param("ALERTHANDLER (OK)", "Alert Handler (Ok)", id="alert handler with result"),
        pytest.param("ALERTHANDLER", "Alert Handler", id="alert handler"),
        pytest.param("PROBLEM", "Problem", id="other"),
    ],
)
def test_pretty_notification_type(notification_type: str, expected: str) -> None:
    assert utils.pretty_notification_type(notification_type) == expected


@pytest.mark.parametrize(
    "state, expected",
    [
        pytest.param("OK", "OK", id="ok stays upper case"),
        pytest.param("CRITICAL", "Critical", id="others are title case"),
    ],
)
def test_pretty_state(state: str, expected: str) -> None:
    assert utils.pretty_state(state) == expected


_GRAPH_CONTEXT = {"HOSTNAME": "heute", "WHAT": "HOST"}


@responses.activate
def test_render_cmk_graphs_authenticates_with_site_internal_secret(
    graph_url: re.Pattern[str],
) -> None:
    responses.get(graph_url, json={"result_code": 0, "result": []})

    utils.render_cmk_graphs(_GRAPH_CONTEXT)

    assert responses.calls[0].request.headers["Authorization"].startswith("InternalToken ")


@responses.activate
def test_render_cmk_graphs_reports_connection_failure(
    graph_url: re.Pattern[str], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.get(graph_url, body=requests.exceptions.ConnectionError("refused"))

    graphs = utils.render_cmk_graphs(_GRAPH_CONTEXT)

    assert (graphs, capsys.readouterr().err.splitlines()[0]) == (
        [],
        "ERROR: Failed to fetch graphs: refused",
    )


@responses.activate
def test_render_cmk_graphs_treats_empty_response_as_no_graphs(
    graph_url: re.Pattern[str], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.get(graph_url, body="")

    graphs = utils.render_cmk_graphs(_GRAPH_CONTEXT)

    assert (graphs, capsys.readouterr().err) == ([], "")


@responses.activate
def test_render_cmk_graphs_reports_rendering_error(
    graph_url: re.Pattern[str], capsys: pytest.CaptureFixture[str]
) -> None:
    responses.get(graph_url, json={"result_code": 1, "result": "no permission"})

    graphs = utils.render_cmk_graphs(_GRAPH_CONTEXT)

    assert (graphs, capsys.readouterr().err.splitlines()[0]) == (
        [],
        "ERROR: Graph rendering failed: no permission",
    )


# fmt: off
@pytest.mark.parametrize(
    "body, expected_error",
    [
        pytest.param(requests.exceptions.ReadTimeout("slow"), requests.exceptions.ReadTimeout, id="timeout"),
        pytest.param(requests.exceptions.ConnectionError("refused"), requests.exceptions.ConnectionError, id="connection error"),
        pytest.param("not json", requests.exceptions.JSONDecodeError, id="invalid JSON"),
        pytest.param('{"result_code": 1, "result": "no permission"}', RuntimeError, id="rendering error"),
    ],
)
# fmt: on
@responses.activate
def test_render_cmk_graphs_raises_when_requested(
    graph_url: re.Pattern[str], body: str | Exception, expected_error: type[Exception]
) -> None:
    responses.get(graph_url, body=body)

    with pytest.raises(expected_error):
        utils.render_cmk_graphs(_GRAPH_CONTEXT, raise_exception=True)
