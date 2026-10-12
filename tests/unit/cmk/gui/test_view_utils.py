#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from typing import cast

import pytest

from livestatus import SiteConfigurations

from cmk.gui.http import request
from cmk.gui.view_utils import (
    determine_must_escape,
    format_plugin_output,
    replace_action_url_macros,
)
from cmk.web.utils.html import HTML


@pytest.mark.usefixtures("patch_theme", "request_context")
@pytest.mark.parametrize(
    "args, expected",
    [
        pytest.param(
            "https://example.com A simple example",
            HTML.without_escaping(
                """<a href="https://example.com" title="https://example.com" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a> A simple example"""
            ),
            id="nothing fancy",
        ),
        pytest.param(
            '"http://127.0.0.1:5000/heute/che\'ck_mk"',
            HTML.without_escaping(
                """<a href="http://127.0.0.1:5000/heute/che&#x27;ck_mk" title="http://127.0.0.1:5000/heute/che&#x27;ck_mk" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>"""
            ),
            id="single quote in url",
        ),
        pytest.param(
            '"http://127.0.0.1:5000/heute/check_mk\'"',
            HTML.without_escaping(
                """<a href="http://127.0.0.1:5000/heute/check_mk&#x27;" title="http://127.0.0.1:5000/heute/check_mk&#x27;" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>"""
            ),
            id="trailing quote in url",
        ),
        pytest.param(
            "'http://127.0.0.1:5000/heute/check_mk'",
            HTML.without_escaping(
                """<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>"""
            ),
            id="enclosed in single quotes",
        ),
        pytest.param(
            """<A HREF="http://127.0.0.1:5000/heute/check_mk" target="_blank">Some text </A>""",
            HTML.without_escaping(
                """<a href="http://127.0.0.1:5000/heute/check_mk" title="http://127.0.0.1:5000/heute/check_mk" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a> Some text"""
            ),
            id="A HREF Replacement",
        ),
        pytest.param(
            "Don't look at this: https://bitly.com/98K8eH, This is another summary",
            HTML.without_escaping(
                """Don&#x27;t look at this: <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>, This is another summary"""
            ),
            id="The comma is not part of the URL",
        ),
        pytest.param(
            "Link with a state marker: https://bitly.com/98K8eH(!), This is another summary(!!), Another summary with a link https://bitly.com/98K8eH(.)",
            HTML.without_escaping(
                """Link with a state marker: <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a><b class="stmark state1">WARN</b>, This is another summary<b class="stmark state2">CRIT</b>, Another summary with a link <a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a><b class="stmark state0">OK</b>"""
            ),
            id="The link has appended state marker",
        ),
        pytest.param(
            "Link with parentheses: (https://bitly.com/98K8eH), Another one with trailing colon: (https://bitly.com/98K8eH): Some Stuff",
            HTML.without_escaping(
                """Link with parentheses: (<a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>), Another one with trailing colon: (<a href="https://bitly.com/98K8eH" title="https://bitly.com/98K8eH" target="_blank" class="cmk-url-icon-link"><cmk-static-icon data="{&quot;icon&quot;: &quot;link&quot;}" class="iconbutton icon"></cmk-static-icon></a>): Some Stuff"""
            ),
            id="The link is surrounded by parentheses",
        ),
    ],
)
def test_button_url(args: str, expected: HTML) -> None:
    assert format_plugin_output(args, request=request, must_escape=False) == expected


class TestDetermineMustEscape:
    """Regression tests for crash groups 4410 / 4421.

    Before the fix, ``determine_must_escape`` accessed ``active_config.sites[row["site"]]``
    directly, raising ``KeyError`` when the site ID stored in the row was no longer present
    in the site configuration (e.g. after a remote site was removed).
    """

    def test_no_site_key_in_row_returns_true(self) -> None:
        # Row has no "site" key at all — we must escape to stay safe.
        assert determine_must_escape(SiteConfigurations({}), {}) is True

    def test_unknown_site_id_returns_true(self) -> None:
        # Site ID is present in the row but not in the configuration — must escape and
        # must not raise KeyError (the original crash).
        assert determine_must_escape(SiteConfigurations({}), {"site": "nonexistent_site"}) is True

    def test_untrusted_site_returns_true(self) -> None:
        sites = cast(SiteConfigurations, {"mysite": {"is_trusted": False}})
        assert determine_must_escape(sites, {"site": "mysite"}) is True

    def test_trusted_site_returns_false(self) -> None:
        sites = cast(SiteConfigurations, {"mysite": {"is_trusted": True}})
        assert determine_must_escape(sites, {"site": "mysite"}) is False


@pytest.mark.usefixtures("request_context")
def test_host_row_without_service_data_uses_host_escaping_option() -> None:
    row = {
        "host_custom_variables": {"ESCAPE_PLUGIN_OUTPUT": "0"},
        "service_custom_variables": None,
    }

    assert format_plugin_output(
        "<b>OK</b>", request=request, must_escape=False, row=row
    ) == HTML.without_escaping("<b>OK</b>")


_ROW = {"host_name": "h1", "host_address": "127.0.0.1"}


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://wiki/$HOSTNAME$", "http://wiki/h1", id="http"),
        pytest.param("view.py?host=$HOSTNAME_URL_ENCODED$", "view.py?host=h1", id="relative"),
        pytest.param("ssh://$HOSTADDRESS$", "ssh://127.0.0.1", id="ssh"),
        pytest.param("smb://share/$HOSTNAME$", "smb://share/h1", id="other_scheme"),
        pytest.param(
            "https://kibana/app?_a=(query:'host.name:\"$HOSTNAME$\"')",
            "https://kibana/app?_a=(query:'host.name:\"h1\"')",
            id="quotes_and_parentheses",
        ),
        pytest.param(
            "https://grafana/d/x?var-host={$HOSTNAME$}",
            "https://grafana/d/x?var-host={h1}",
            id="braces",
        ),
        pytest.param(
            "onclick:cmk.views.reschedule_check(this, '$HOSTNAME$', '', '', '');",
            "onclick:cmk.views.reschedule_check(this, 'h1', '', '', '');",
            id="builtin_onclick_icon",
        ),
    ],
)
@pytest.mark.usefixtures("request_context", "with_user_login")
def test_replace_action_url_macros_expands_urls(url: str, expected: str) -> None:
    assert replace_action_url_macros(url, "host", _ROW) == expected


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("javascript:alert(1)", id="javascript"),
        pytest.param(" JavaScript:alert('$HOSTNAME$')", id="javascript_mixed_case"),
        pytest.param("java\tscript:alert(1)", id="javascript_with_tab"),
        pytest.param("data:text/html,<script>alert(1)</script>", id="data"),
        pytest.param("VBScript:msgbox(1)", id="vbscript"),
    ],
)
@pytest.mark.usefixtures("request_context", "with_user_login")
def test_replace_action_url_macros_neutralizes_script_urls(url: str) -> None:
    assert replace_action_url_macros(url, "host", _ROW) == "#"


@pytest.mark.usefixtures("request_context", "with_user_login")
def test_replace_action_url_macros_logs_script_url_once(caplog: pytest.LogCaptureFixture) -> None:
    url = "javascript:logged_once('$HOSTNAME$')"

    with caplog.at_level(logging.WARNING, logger="cmk.web"):
        replace_action_url_macros(url, "host", {"host_name": "h1", "host_address": "127.0.0.1"})
        replace_action_url_macros(url, "host", {"host_name": "h2", "host_address": "127.0.0.2"})

    assert [r.message for r in caplog.records if "logged_once" in r.message] == [
        f"Ignoring configured script URL: {url!r}"
    ]
