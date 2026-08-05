#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import override

import pytest

from cmk.gui.config import Config
from cmk.gui.groups import GroupType
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._groups import GroupSnapin, HostGroups, ServiceGroups
from cmk.gui.utils.output_funnel import output_funnel


class BogusGroups(GroupSnapin):
    """A snap-in whose group type the URL builder cannot map to a livestatus table."""

    @override
    def _group_type_ident(self) -> str:
        return "junk"

    @staticmethod
    @override
    def type_name() -> str:
        return "bogusgroups"

    @classmethod
    @override
    def title(cls) -> str:
        return "Bogus groups"

    @classmethod
    @override
    def description(cls) -> str:
        return ""


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _show(
    monkeypatch: pytest.MonkeyPatch,
    snapin: GroupSnapin,
    config: Config,
    groups: list[tuple[str, str]],
) -> tuple[str, list[GroupType]]:
    requested: list[GroupType] = []

    def _all_groups(group_type: GroupType) -> list[tuple[str, str]]:
        requested.append(group_type)
        return groups

    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._groups.all_groups", _all_groups)
        with output_funnel.plugged():
            snapin.show(config)
            return output_funnel.drain(), requested


def test_host_groups_metadata() -> None:
    assert HostGroups.type_name() == "hostgroups"
    assert HostGroups.title() == "Host groups"
    assert HostGroups.refresh_on_restart() is True


def test_service_groups_metadata() -> None:
    assert ServiceGroups.type_name() == "servicegroups"
    assert ServiceGroups.title() == "Service groups"
    assert ServiceGroups.refresh_on_restart() is True


def test_host_groups_query_the_host_groups(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered, requested = _show(
        monkeypatch, HostGroups(), load_config, [("linux", "Linux servers")]
    )

    assert requested == ["host"]
    assert "Linux servers" in rendered
    assert "view.py?view_name=hostgroup&hostgroup=linux" in rendered


def test_service_groups_query_the_service_groups(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered, requested = _show(
        monkeypatch, ServiceGroups(), load_config, [("filesystems", "Filesystems")]
    )

    assert requested == ["service"]
    assert "view.py?view_name=servicegroup&servicegroup=filesystems" in rendered


def test_group_names_are_url_encoded(monkeypatch: pytest.MonkeyPatch, load_config: Config) -> None:
    """Group names may contain spaces and slashes; unencoded they would break the link."""
    rendered, _requested = _show(
        monkeypatch, HostGroups(), load_config, [("my group/1", "My group")]
    )

    assert "hostgroup=my+group%2F1" in rendered


def test_a_group_without_an_alias_falls_back_to_its_name(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered, _requested = _show(monkeypatch, HostGroups(), load_config, [("linux", "")])

    assert "linux" in rendered


def test_no_groups_renders_no_list(monkeypatch: pytest.MonkeyPatch, load_config: Config) -> None:
    rendered, _requested = _show(monkeypatch, HostGroups(), load_config, [])

    assert rendered == ""


def test_an_unmappable_group_type_is_rejected(load_config: Config) -> None:
    with pytest.raises(ValueError, match="Unknown group type: junk"):
        BogusGroups().show(load_config)
