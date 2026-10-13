#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.permissions import permission_registry
from cmk.gui.search import index
from cmk.gui.search.matchers import MatchItemConfig, MatchItemGeneratorRegistry
from cmk.gui.search.permissions import CategoryPermissionsHandlerRegistry
from cmk.gui.type_defs import ViewSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views import _search as views_search
from cmk.gui.views.store import ViewStore


def _page_target(url: str) -> tuple[str, str, str, str]:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    return parts.path, query["mode"], query["owner"], query["load_name"]


def _target_pages(category: str, load_config: Config) -> list[tuple[str, str, str, str]]:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    views_search.register(match_item_generator_registry, CategoryPermissionsHandlerRegistry())
    return [
        _page_target(item.url)
        for item in match_item_generator_registry[category].generate_match_items(
            UserPermissions(load_config.roles, permission_registry, {}, []),
            MatchItemConfig.from_config(load_config),
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_builtin_views_link_to_the_view_clone_page(load_config: Config) -> None:
    targets = _target_pages("builtin_views", load_config)

    assert ("edit_view.py", "clone", "", "allhosts") in targets
    assert {(page, mode, owner) for page, mode, owner, _name in targets} == {
        ("edit_view.py", "clone", "")
    }


@pytest.fixture(name="update_requests_path")
def fixture_update_requests_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "search_index_updates.json"
    monkeypatch.setattr(index, "_PATH_UPDATE_REQUESTS", path)
    return path


def _save_custom_view(owner: UserId) -> None:
    all_views = ViewStore.load_all_views()
    custom: ViewSpec = {
        **all_views[(UserId.builtin(), "allhosts")],
        "owner": owner,
        "name": "mine",
        "title": "Mine",
        "packaged": False,
    }
    visuals.save("views", {(owner, "mine"): custom}, owner)


@pytest.mark.usefixtures("update_requests_path")
def test_custom_view_links_to_its_edit_page(with_user_login: UserId, load_config: Config) -> None:
    _save_custom_view(with_user_login)

    assert _target_pages("custom_views", load_config) == [
        ("edit_view.py", "edit", str(with_user_login), "mine")
    ]
