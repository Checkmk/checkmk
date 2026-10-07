#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.gui.config import Config
from cmk.gui.dashboard._search import register
from cmk.gui.permissions import permission_registry
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
    register(match_item_generator_registry, CategoryPermissionsHandlerRegistry())

    targets = [
        _page_target(item.url)
        for item in match_item_generator_registry["builtin_dashboards"].generate_match_items(
            UserPermissions(load_config.roles, permission_registry, {}, []),
            MatchItemConfig.from_config(load_config),
        )
    ]

    assert ("dashboard.py", "clone", "", "main") in targets
    assert {(page, mode, owner) for page, mode, owner, _name in targets} == {
        ("dashboard.py", "clone", "")
    }
