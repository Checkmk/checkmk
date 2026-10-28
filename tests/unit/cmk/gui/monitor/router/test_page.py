#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from urllib.parse import parse_qs, urlsplit

import pytest
from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.http import Request
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.router import MonitorRouterPage, route
from cmk.gui.monitor.setup_folders import SetupFolders, SetupFoldersConfig
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.ruleset_matcher.tags import TagConfig
from cmk.web.context import SessionInfoProtocol, SessionUserProtocol


def _no_folders() -> Mapping[str, str]:
    raise AssertionError("the query names no folder")


def _unused_setup_folders(_config: SetupFoldersConfig, _user: LoggedInUser) -> SetupFolders:
    raise AssertionError("the query names no folder")


def test_query_without_prefix_goes_to_all_hosts_search_box_as_typed() -> None:
    assert (
        route(Request(create_environ()), "  web*  ", TagConfig(), _no_folders)
        == "monitor_all_hosts.py?q=web%2A"
    )


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("web\nserver", id="line-break"),
        pytest.param("web\tserver", id="tab"),
    ],
)
def test_control_character_in_query_without_prefix_goes_to_search_box_as_space(
    query: str,
) -> None:
    assert (
        route(Request(create_environ()), query, TagConfig(), _no_folders)
        == "monitor_all_hosts.py?q=web+server"
    )


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("hl:os:linux", id="label"),
        pytest.param("hl:cmk/aws*", id="label-key-prefix"),
        pytest.param("hl:os:*", id="label-any-value"),
        pytest.param("tg:os:*", id="tag-any-of-group"),
        pytest.param("hl:os:lin* hl:os:lin*", id="repeated-label"),
        pytest.param("tg:dc:fra tg:os:lin*", id="tags"),
        pytest.param("hg:linux hg:web*", id="host-groups"),
    ],
)
def test_label_tag_or_group_query_goes_to_a_filter_the_page_accepts(query: str) -> None:
    # all_hosts_url() validates the tree against the page's filter model.
    assert route(Request(create_environ()), query, TagConfig(), _no_folders).startswith(
        "monitor_all_hosts.py?filter="
    )


def test_host_query_goes_to_all_hosts_filter() -> None:
    parts = urlsplit(route(Request(create_environ()), "h:web", TagConfig(), _no_folders))

    assert parts.path == "monitor_all_hosts.py"
    assert {name: json.loads(value) for name, [value] in parse_qs(parts.query).items()} == {
        "filter": {"type": "condition", "field": "name", "op": "contains", "value": "web"}
    }


def test_folder_query_goes_to_all_hosts_folder_filter() -> None:
    parts = urlsplit(
        route(
            Request(create_environ()),
            "hf:dc_muc",
            TagConfig(),
            lambda: {"dc_muc": "Data center Munich", "linux": "Linux servers"},
        )
    )

    assert parts.path == "monitor_all_hosts.py"
    assert {name: json.loads(value) for name, [value] in parse_qs(parts.query).items()} == {
        "filter": {
            "type": "condition",
            "field": "folder",
            "op": "contains",
            "value": "Data center Munich",
        }
    }


def test_service_query_goes_to_all_services_filter() -> None:
    parts = urlsplit(route(Request(create_environ()), "s:cpu", TagConfig(), _no_folders))

    assert parts.path == "monitor_all_services.py"
    assert {name: json.loads(value) for name, [value] in parse_qs(parts.query).items()} == {
        "filter": {"type": "condition", "field": "name", "op": "contains", "value": "cpu"}
    }


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("h:web s:cpu", id="host-and-service"),
        pytest.param("st:warn|crit sl:os:* sg:web*", id="state-label-and-group"),
    ],
)
def test_service_query_goes_to_a_filter_all_services_accepts(query: str) -> None:
    assert route(Request(create_environ()), query, TagConfig(), _no_folders).startswith(
        "monitor_all_services.py?filter="
    )


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("", "enter a search term", id="empty"),
        pytest.param("x:web", "Unknown search prefix", id="invalid"),
        pytest.param("tg:*", "needs text before it", id="tag-without-group-only-star"),
        pytest.param("s:cpu al:web", "can only be searched by", id="no-page-for-it"),
    ],
)
def test_query_that_cannot_be_shown_is_rejected(query: str, message: str) -> None:
    with pytest.raises(MKUserError, match=message):
        route(Request(create_environ()), query, TagConfig(), _no_folders)


def test_page_redirects_to_the_url_of_the_query() -> None:
    page_request = Request(create_environ(query_string="q=h:web"))
    ctx = PageContext(
        config=Config(),
        request=page_request,
        session=_UnusedSession(),
        transactions=TransactionManager(None, lambda **_: [], lambda _: None),
        user_permissions=UserPermissions.from_config(Config(), all_permissions()),
    )

    with pytest.raises(HTTPRedirect) as redirect:
        MonitorRouterPage(_unused_setup_folders).page(ctx)

    assert redirect.value.url == route(page_request, "h:web", TagConfig(), _no_folders)


class _UnusedSession:
    @property
    def user(self) -> SessionUserProtocol:
        raise AssertionError("the page has no use for the session")

    @property
    def session_info(self) -> SessionInfoProtocol:
        raise AssertionError("the page has no use for the session")
