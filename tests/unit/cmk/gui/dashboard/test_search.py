#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard import _search as dashboard_search
from cmk.gui.dashboard.store import get_all_dashboards, save_all_dashboards
from cmk.gui.dashboard.type_defs import DashboardConfig
from cmk.gui.permissions import all_permissions
from cmk.gui.search import index
from cmk.gui.search.matchers import MatchItemConfig, MatchItemGeneratorRegistry
from cmk.gui.search.permissions import CategoryPermissionsHandlerRegistry
from cmk.gui.utils.roles import UserPermissions


def _page_target(url: str) -> tuple[str, str, str, str]:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    return parts.path, query["mode"], query["owner"], query["name"]


@pytest.mark.usefixtures("request_context")
def test_builtin_dashboards_link_to_the_dashboard_clone_page(load_config: Config) -> None:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    dashboard_search.register(match_item_generator_registry, CategoryPermissionsHandlerRegistry())

    targets = [
        _page_target(item.url)
        for item in match_item_generator_registry["builtin_dashboards"].generate_match_items(
            UserPermissions(
                load_config.roles,
                all_permissions(),
                {},
                [],
            ),
            MatchItemConfig.from_config(load_config),
        )
    ]

    assert ("dashboard.py", "clone", "", "main") in targets
    assert {(page, mode, owner) for page, mode, owner, _name in targets} == {
        ("dashboard.py", "clone", "")
    }


@pytest.fixture(name="update_requests_path")
def fixture_update_requests_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "search_index_updates.json"
    monkeypatch.setattr(index, "_PATH_UPDATE_REQUESTS", path)
    return path


def _save_custom_dashboard(owner: UserId) -> None:
    all_dashboards = get_all_dashboards()
    builtin = next(
        board
        for (board_owner, _name), board in all_dashboards.items()
        if board_owner == UserId.builtin()
    )
    custom: DashboardConfig = {
        **builtin,
        "owner": owner,
        "name": "mine",
        "title": "Mine",
        "packaged": False,
    }
    all_dashboards[(owner, "mine")] = custom
    save_all_dashboards(owner)


def _registries() -> tuple[MatchItemGeneratorRegistry, CategoryPermissionsHandlerRegistry]:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    category_permissions_handler_registry = CategoryPermissionsHandlerRegistry()
    dashboard_search.register(match_item_generator_registry, category_permissions_handler_registry)
    return match_item_generator_registry, category_permissions_handler_registry


def test_custom_dashboards_are_registered_under_customize() -> None:
    match_item_generator_registry, category_permissions_handler_registry = _registries()

    assert match_item_generator_registry.provider_for("custom_dashboards") == "customize"
    assert "custom_dashboards" in category_permissions_handler_registry


@pytest.mark.usefixtures("update_requests_path")
def test_custom_dashboard_links_to_its_settings_page(
    with_user_login: UserId, load_config: Config
) -> None:
    _save_custom_dashboard(with_user_login)
    match_item_generator_registry, _permissions = _registries()

    match_items = match_item_generator_registry["custom_dashboards"].generate_match_items(
        UserPermissions(
            load_config.roles,
            all_permissions(),
            {},
            [],
        ),
        MatchItemConfig.from_config(load_config),
    )

    assert [(item.title, item.topic, item.url) for item in match_items] == [
        (
            "Mine",
            "Custom dashboards",
            f"dashboard.py?mode=edit_settings&name=mine&owner={with_user_login}",
        )
    ]


@pytest.mark.usefixtures("update_requests_path")
def test_saving_dashboards_requests_a_search_index_update(with_user_login: UserId) -> None:
    _save_custom_dashboard(with_user_login)

    assert index._read_and_remove_update_requests()["change_actions"] == ["save-dashboards"]  # noqa: SLF001
