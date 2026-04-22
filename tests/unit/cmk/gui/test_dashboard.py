#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from collections.abc import Iterator

import pytest

from cmk.ccc.plugin_registry import Registry
from cmk.gui.dashboard import dashlet_registry, DashletConfig
from cmk.gui.dashboard.dashlet.base import Dashlet
from tests.testlib.common.utils import reset_registries


class DummyDashletConfig(DashletConfig): ...


class DummyDashlet(Dashlet[DummyDashletConfig]):
    @classmethod
    def type_name(cls):
        return "dummy"

    @classmethod
    def title(cls):
        return "DUMMy"

    @classmethod
    def description(cls):
        return "duMMy"

    @classmethod
    def sort_index(cls) -> int:
        return 123


@pytest.fixture(name="reset_dashlet_registry")
def fixture_reset_dashlet_registry() -> Iterator[None]:
    with reset_registries([dashlet_registry]):
        yield


@pytest.fixture(name="registry_list", scope="module")
def fixture_registry_list() -> list[Registry]:
    """Returns 'dashlet_registry' to be reset after test-case execution."""
    return [dashlet_registry]


@pytest.fixture(name="dummy_config")
def fixture_dummy_config() -> DummyDashletConfig:
    return DummyDashletConfig(
        {
            "type": "dummy",
        }
    )


@pytest.mark.usefixtures("reset_dashlet_registry")
def test_dashlet_registry_plugins() -> None:
    expected_plugins = [
        "hoststats",
        "servicestats",
        "eventstats",
        "notify_failed_notifications",
        "url",
        "pnpgraph",
        "view",
        "embedded_view",
        "linked_view",
        "user_messages",
        "nodata",
        "snapin",
    ]

    assert sorted(dashlet_registry.keys()) == sorted(expected_plugins)


@pytest.mark.usefixtures("request_context")
def test_dashlet_type_defaults() -> None:
    assert not Dashlet.single_infos()
    assert Dashlet.is_selectable() is True


def test_dashlet_defaults(dummy_config: DummyDashletConfig) -> None:
    dashlet = DummyDashlet(dashlet=dummy_config)
    assert not dashlet.infos()
    assert dashlet.dashlet_spec == {"type": "dummy"}


@pytest.mark.usefixtures("reset_dashlet_registry")
def test_dashlet_context_inheritance() -> None:
    dashlet_spec = {
        "type": "hoststats",
        "context": {"wato_folder": {"wato_folder": ""}},
        "single_infos": [],
        "show_title": True,
        "title": "Host Statistics",
        "add_context_to_title": True,
        "link_from": {},
        "position": (61, 1),
        "size": (30, 18),
    }

    HostStats = dashlet_registry["hoststats"]
    dashlet = HostStats(
        dashlet=dashlet_spec,
        base_context={
            "wato_folder": {"wato_folder": "/aaa/eee"},
            "host": {"host": "bla", "neg_host": ""},
        },
    )

    assert dashlet.context == {
        "host": {"host": "bla", "neg_host": ""},
        "wato_folder": {"wato_folder": ""},
    }
