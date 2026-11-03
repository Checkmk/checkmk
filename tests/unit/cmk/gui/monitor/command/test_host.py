#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.command import host_setup_links


class _StubUser:
    def __init__(self, granted: set[str]) -> None:
        self._granted = granted

    def may(self, permission_name: str) -> bool:
        return permission_name in self._granted


def _idents(granted: set[str], *, wato_enabled: bool = True) -> list[str]:
    config = Config()
    config.wato_enabled = wato_enabled
    return [link.ident for link in host_setup_links(config, cast(LoggedInUser, _StubUser(granted)))]


_ALL = {"wato.use", "wato.seeall", "wato.hosts", "wato.rulesets"}


def test_offers_editing_and_parameters_to_a_user_granted_all() -> None:
    assert _idents(_ALL) == ["edit", "parameters"]


def test_links_keep_the_host_placeholder() -> None:
    config = Config()
    config.wato_enabled = True

    assert [link.url for link in host_setup_links(config, cast(LoggedInUser, _StubUser(_ALL)))] == [
        "wato.py?mode=edit_host&host={host}",
        "wato.py?mode=object_parameters&host={host}",
    ]


def test_offers_nothing_where_setup_is_off() -> None:
    assert _idents(_ALL, wato_enabled=False) == []


@pytest.mark.parametrize(
    "granted",
    [
        pytest.param({"wato.use", "wato.seeall"}, id="see-all"),
        pytest.param({"wato.use", "wato.hosts"}, id="hosts"),
    ],
)
def test_offers_editing_with_setup_and_access_to_the_hosts(granted: set[str]) -> None:
    assert _idents(granted) == ["edit"]


@pytest.mark.parametrize(
    "granted",
    [
        pytest.param({"wato.seeall", "wato.hosts"}, id="without-setup"),
        pytest.param({"wato.use"}, id="without-access-to-the-hosts"),
    ],
)
def test_withholds_editing_without_the_needed_permissions(granted: set[str]) -> None:
    assert _idents(granted) == []


def test_offers_parameters_with_the_rulesets_permission_alone() -> None:
    assert _idents({"wato.rulesets"}) == ["parameters"]
