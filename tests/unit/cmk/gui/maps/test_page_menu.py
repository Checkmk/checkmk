#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

import pytest

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.page_menu import PageMenu, PageMenuLink
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui._page_menu import (
    images_breadcrumb,
    images_page_menu,
    map_list_page_menu,
    maps_breadcrumb,
    PAGE_MENU_EVENT,
)
from cmk.maps.gui._settings import MapListView


def _menu(layout: MapListView = "cards") -> PageMenu:
    return map_list_page_menu(
        user, maps_breadcrumb(), settings_url="maps_settings.py", layout=layout
    )


def _entry_names(menu: PageMenu, dropdown: str) -> list[str | None]:
    return [entry.name for topic in menu[dropdown].topics for entry in topic.entries]


def test_admin_gets_all_list_actions(request_context: None, with_admin_login: UserId) -> None:
    assert _entry_names(_menu(), "maps") == [
        "maps_create",
        "maps_import",
        "maps_images",
        "maps_settings",
    ]


def test_add_map_is_the_quick_button(request_context: None, with_admin_login: UserId) -> None:
    assert "maps_create" in [entry.name for entry in _menu().shortcuts]


def test_actions_dispatch_the_event_the_app_listens_for(
    request_context: None, with_admin_login: UserId
) -> None:
    create = next(entry for entry in _menu().shortcuts if entry.name == "maps_create")
    assert isinstance(create.item, PageMenuLink)
    assert create.item.link.onclick is not None
    assert f"'{PAGE_MENU_EVENT}'" in create.item.link.onclick
    assert "detail: 'create'" in create.item.link.onclick


@pytest.mark.parametrize(
    "shown, offered",
    [
        pytest.param("cards", "maps_show_table", id="cards"),
        pytest.param("table", "maps_show_cards", id="table"),
    ],
)
def test_display_offers_the_layout_not_shown(
    request_context: None, with_admin_login: UserId, shown: MapListView, offered: str
) -> None:
    assert _entry_names(_menu(shown), "display")[-1:] == [offered]


def test_layout_switch_is_suggested(request_context: None, with_admin_login: UserId) -> None:
    assert "maps_show_table" in {entry.name for entry in _menu().suggestions}


def test_layout_switch_keeps_what_the_list_put_in_the_url(
    request_context: None, with_admin_login: UserId
) -> None:
    switch = next(entry for entry in _menu().suggestions if entry.name == "maps_show_table")
    assert isinstance(switch.item, PageMenuLink)
    assert switch.item.link.onclick is not None
    assert "location.href = cmk.utils.makeuri({layout: 'table'})" in switch.item.link.onclick


def test_user_without_permissions_gets_no_list_actions(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    with UserContext(with_user[0], UserPermissions({}, {}, {}, [])):
        assert _entry_names(_menu(), "maps") == []


def test_upload_is_the_quick_button_of_the_image_library(
    request_context: None, with_admin_login: UserId
) -> None:
    menu = images_page_menu(images_breadcrumb())
    assert "maps_upload_image" in [entry.name for entry in menu.shortcuts]
