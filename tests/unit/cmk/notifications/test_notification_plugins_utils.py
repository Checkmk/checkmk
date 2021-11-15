#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import Mock

import pytest
import requests

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
def test_host_url_from_context(context, result):
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
def test_service_url_from_context(context, result):
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
def test_format_link(template, url, text, expected_link):
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
def test_format_address(display_name, address, expected):
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
def test_substitute_context(context, template, result):
    assert result == utils.substitute_context(template, context)


def test_read_bulk_contents(monkeypatch, capsys):
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
def test_get_bulk_notification_subject(context, hosts, result):
    assert utils.get_bulk_notification_subject(context, hosts) == result


@pytest.mark.parametrize(
    "value, result",
    [
        ("http://local.host", "http://local.host"),
        ("webhook_url\thttp://webhook.host", "http://webhook.host"),
        ("store\tpwservice", "http://secret.host"),
    ],
)
def test_api_endpoint_url(monkeypatch, value, result):
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
    ],
)
def test_escape_context(input_context, expected_context):
    escaped_context = utils.html_escape_context(input_context)
    assert escaped_context == expected_context


@pytest.mark.parametrize(
    "response, result_map, expected_exit_msg, expected_exit_code",
    [
        (
            Mock(requests.models.Response, status_code=200, text="whatever"),
            {},
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(requests.models.Response, status_code=200, text="whatever"),
            {
                (400, 500): utils.StateInfo(state=0, type="str", title="some title"),
            },
            "Details for Status Code are not defined\n200: OK\n",
            3,
        ),
        (
            Mock(requests.models.Response, status_code=200, text="whatever"),
            {
                (200, 300): utils.StateInfo(state=0, type="str", title="some title"),
            },
            "some title\n200: OK\n",
            0,
        ),
        (
            Mock(requests.models.Response, status_code=201, text="whatever"),
            {
                (200, 300): utils.StateInfo(state=0, type="str", title="some title"),
            },
            "some title\n200: OK\n",
            0,
        ),
        (
            Mock(requests.models.Response, status_code=300, text="whatever"),
            {
                (200, 300): utils.StateInfo(state=0, type="str", title="some title"),
            },
            "some title\n200: OK\n",
            0,
        ),
    ],
)
def test_process_by_result_map(
    response,
    result_map,
    expected_exit_msg,
    expected_exit_code,
):
    with pytest.raises(SystemExit) as sys_exit:
        utils.process_by_result_map(response, result_map)
        assert sys_exit.value == expected_exit_msg
        assert sys_exit.value.code == expected_exit_code
