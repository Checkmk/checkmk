#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import binascii
import json
from collections.abc import Mapping, Sequence
from unittest.mock import Mock, patch

import pytest
import requests
from pytest import MonkeyPatch

from cmk.notification_plugins import utils


@pytest.mark.parametrize(
    "context, result",
    [
        (  # host context with url parameter
            {
                "PARAMETER_URL_PREFIX": "https://host/site/check_mk",
                "HOSTURL": "/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
                "WHAT": "HOST",
            },
            "https://host/site/check_mk/index.py?start_url=view.py?view_name=hoststatus&host=test&site=heute",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "https",
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
                "PARAMETER_URL_PREFIX": "https://host/site/check_mk",
                "WHAT": "HOST",
            },
            "",
        ),
        (  # service context with url parameter
            {
                "PARAMETER_URL_PREFIX_AUTOMATIC": "http",
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
    monkeypatch.setattr("sys.stdin", ("key=val", "\n", "key2=val2", "a comment"))
    assert utils.read_bulk_contexts() == ({"key": "val"}, [{"key2": "val2"}])
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
    monkeypatch.setattr("cmk.utils.password_store.extract", lambda x: "http://secret.host")
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
            Mock(requests.models.Response, status_code=200, text="whatever"),
            [],
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(requests.models.Response, status_code=200, text="whatever"),
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
            Mock(requests.models.Response, status_code=200, text="whatever"),
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
            Mock(requests.models.Response, status_code=201, text="whatever"),
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
            Mock(requests.models.Response, status_code=300, text="whatever"),
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
                status_code=200,
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
                status_code=200,
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
                status_code=200,
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
                status_code=200,
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
                status_code=400,
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

    def send(self, request: object, timeout: int) -> ResponseMock:
        if self.side_effect:
            # pylint thinks this could be None here but it cannot...
            raise self.side_effect
        return ResponseMock(self.data)


@patch("cmk.notification_plugins.utils.site", new=SiteMock())
def test_render_cmk_graphs(capsys: pytest.CaptureFixture) -> None:
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
        mock.data = '["foo"]'
        with pytest.raises(binascii.Error):
            utils.render_cmk_graphs(context=context)

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '[""]'
        assert utils.render_cmk_graphs(context=context) == [utils.Graph("heute-_HOST_-0.png", b"")]
        assert capsys.readouterr().err == ""

    with patch(
        "cmk.notification_plugins.utils.requests.Session", new=RequestsSessionMock()
    ) as mock:
        mock.data = '["YQ==", "Yg==", "Yw=="]'
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
        mock.data = '["YQ==", "Yg=="]'
        assert utils.render_cmk_graphs(context=context) == [
            utils.Graph("heute-Filesystem_x47boot-0.png", b"a"),
            utils.Graph("heute-Filesystem_x47boot-1.png", b"b"),
        ]
        assert capsys.readouterr().err == ""
