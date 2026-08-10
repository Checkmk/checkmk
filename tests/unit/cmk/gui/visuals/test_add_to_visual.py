#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from cmk.gui.page_menu import make_simple_link, PageMenuDropdown, PageMenuEntry
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.visuals import page_menu_dropdown_add_to_visual


def _user_permissions() -> UserPermissions:
    return UserPermissions(roles={}, permissions={}, user_roles={}, default_user_profile_roles=[])


def _fake_visual_type(title: str, entry_title: str | None) -> MagicMock:
    visual_type = MagicMock()
    visual_type.title = title
    entries = (
        []
        if entry_title is None
        else [
            PageMenuEntry(
                title=entry_title,
                icon_name=StaticIcon(IconNames.trans),
                item=make_simple_link("dummy.py"),
            )
        ]
    )
    visual_type.page_menu_add_to_entries.return_value = iter(entries)
    return visual_type


def _flatten(dropdowns: list[PageMenuDropdown]) -> list[str]:
    titles = []
    for dropdown in dropdowns:
        for topic in dropdown.topics:
            titles.append(topic.title)
            titles.extend(entry.title for entry in topic.entries)
    return titles


def test_add_to_visual_topics_for_pnpgraph_with_community_edition(
    mocker: MockerFixture, request_context: None
) -> None:
    mocker.patch(
        "cmk.gui.visuals._add_to_visual.visual_type_registry",
        {"dashboards": lambda: _fake_visual_type("dashboard", "My Dashboard")},
    )

    topics = _flatten(
        page_menu_dropdown_add_to_visual(
            add_type="pnpgraph",
            name="",
            user_permissions=_user_permissions(),
        )
    )

    assert topics == [
        "Add to dashboard",
        "My Dashboard",
    ]
