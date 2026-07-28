#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.user import UserId
from cmk.gui.main_menu_types import MainMenuItem
from cmk.gui.sidebar._snapin._helpers import make_main_menu, VisualItem, VisualMenuItem
from cmk.gui.type_defs import Visual
from cmk.gui.utils.roles import UserPermissions


def _visual_without_search_terms() -> Visual:
    spec: dict[str, Any] = {
        "owner": UserId.builtin(),
        "name": "some_view",
        "context": {},
        "single_infos": [],
        "add_context_to_title": False,
        "title": "Some view",
        "description": "",
        "topic": "overview",
        "sort_index": 10,
        "is_show_more": False,
        "icon": None,
        "hidden": False,
        "hidebutton": False,
        "public": True,
        "packaged": False,
        "link_from": {},
    }
    return spec  # type: ignore[return-value]


def test_make_main_menu_visual_without_search_terms(request_context: None) -> None:
    """A visual lacking main_menu_search_terms must not crash the main menu.

    Built-in visuals bypass the per-visual-type runtime transformer that defaults the
    key, so a plugin registering one without it used to take down the whole sidebar."""
    topics = make_main_menu(
        [VisualMenuItem("views", VisualItem("some_view", _visual_without_search_terms()))],
        UserPermissions({}, {}, {}, []),
    )

    entries = [entry for topic in topics for entry in topic.entries]
    assert [entry.name for entry in entries] == ["some_view"]
    entry = entries[0]
    assert isinstance(entry, MainMenuItem)
    assert entry.main_menu_search_terms == []
