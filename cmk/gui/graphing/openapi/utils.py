#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import get_args

from cmk.gui.graphing.openapi.models import (
    BurgerMenuAction,
    BurgerMenuActionType,
    BurgerMenuGroup,
    BurgerMenuItem,
)
from cmk.gui.page_menu import PageMenuDropdown, PageMenuEntry, PageMenuLink
from cmk.gui.type_defs import StaticIcon

BURGER_MENU_ACTIONS: frozenset[BurgerMenuActionType] = frozenset(get_args(BurgerMenuActionType))


def serialize_menu_item(entry: PageMenuEntry) -> BurgerMenuItem | None:
    if not isinstance(entry.item, PageMenuLink):
        return None

    if not isinstance(entry.icon_name, StaticIcon):
        return None

    link = entry.item.link
    if link.action_id is None or link.action_parameters is None:
        return None

    if link.action_id not in BURGER_MENU_ACTIONS:
        return None

    return BurgerMenuItem(
        label=entry.title,
        ariaLabel=entry.title,
        icon=entry.icon_name.icon,
        action=BurgerMenuAction(id=link.action_id, parameters=link.action_parameters),
    )


def serialize_menu_dropdown(menu_dropdown: PageMenuDropdown) -> list[BurgerMenuGroup]:
    groups = []
    for topic in menu_dropdown.topics:
        items = [
            action for entry in topic.entries if (action := serialize_menu_item(entry)) is not None
        ]
        if not items:
            continue
        groups.append(BurgerMenuGroup(heading=topic.title, items=items))

    return groups
