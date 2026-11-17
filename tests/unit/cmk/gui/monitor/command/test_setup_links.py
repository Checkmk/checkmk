#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import Config
from cmk.gui.monitor.command import (
    host_setup_links,
    service_parameters_link,
    service_setup_links,
    SetupLink,
)


class _StubUser:
    def __init__(self, granted: set[str]) -> None:
        self._granted = granted

    def may(self, permission_name: str) -> bool:
        return permission_name in self._granted


def _host_idents(granted: set[str], *, wato_enabled: bool = True) -> list[str]:
    config = Config()
    config.wato_enabled = wato_enabled
    return [link.ident for link in host_setup_links(config, _StubUser(granted))]


_ALL = {"wato.use", "wato.seeall", "wato.hosts", "wato.rulesets"}


def test_offers_editing_and_parameters_to_a_user_granted_all() -> None:
    assert _host_idents(_ALL) == ["edit", "parameters"]


def test_host_links_keep_the_host_placeholder() -> None:
    config = Config()
    config.wato_enabled = True

    assert [link.url for link in host_setup_links(config, _StubUser(_ALL))] == [
        "wato.py?mode=edit_host&host={host}",
        "wato.py?mode=object_parameters&host={host}",
    ]


def test_offers_no_host_links_where_setup_is_off() -> None:
    assert _host_idents(_ALL, wato_enabled=False) == []


def test_offers_both_to_a_user_who_may_see_all_of_setup() -> None:
    assert _host_idents({"wato.use", "wato.seeall"}) == ["edit", "parameters"]


def test_offers_editing_with_setup_and_access_to_the_hosts() -> None:
    assert _host_idents({"wato.use", "wato.hosts"}) == ["edit"]


def test_offers_parameters_with_setup_and_access_to_the_hosts_and_the_rules() -> None:
    assert _host_idents({"wato.use", "wato.hosts", "wato.rulesets"}) == ["edit", "parameters"]


@pytest.mark.parametrize(
    "granted",
    [
        pytest.param({"wato.seeall", "wato.hosts", "wato.rulesets"}, id="without-setup"),
        pytest.param({"wato.use", "wato.rulesets"}, id="without-access-to-the-hosts"),
        pytest.param({"wato.rulesets"}, id="with-the-rules-alone"),
    ],
)
def test_withholds_both_without_the_needed_permissions(granted: set[str]) -> None:
    """Setup would refuse either page, so a link to it would only lead to an error."""
    assert _host_idents(granted) == []


_PARAMETERS = {"wato.use", "wato.hosts", "wato.rulesets"}


def _service_urls(granted: set[str], *, wato_enabled: bool = True) -> list[str]:
    config = Config()
    config.wato_enabled = wato_enabled
    return [link.url for link in service_setup_links(config, _StubUser(granted))]


def _service_parameters_link() -> SetupLink:
    config = Config()
    config.wato_enabled = True
    link = service_parameters_link(config, _StubUser(_PARAMETERS))
    assert link is not None
    return link


def test_links_the_parameters_of_a_service_keeping_the_host_and_service_placeholders() -> None:
    assert _service_urls(_PARAMETERS) == [
        "wato.py?mode=object_parameters&host={host}&service={service}"
    ]


def test_offers_no_service_links_where_setup_is_off() -> None:
    assert _service_urls(_PARAMETERS, wato_enabled=False) == []


@pytest.mark.parametrize(
    "granted",
    [
        pytest.param({"wato.use", "wato.hosts"}, id="without-the-rules"),
        pytest.param({"wato.hosts", "wato.rulesets"}, id="without-setup"),
    ],
)
def test_offers_no_service_links_without_the_needed_permissions(granted: set[str]) -> None:
    assert _service_urls(granted) == []


def test_fills_in_the_host_and_the_service_as_query_values() -> None:
    assert (
        _service_parameters_link().url_for(host="web 1", service="CPU load")
        == "wato.py?mode=object_parameters&host=web+1&service=CPU+load"
    )


def test_leaves_the_service_to_the_reader_when_only_the_host_is_known() -> None:
    assert (
        _service_parameters_link().url_for(host="web-1")
        == "wato.py?mode=object_parameters&host=web-1&service={service}"
    )
