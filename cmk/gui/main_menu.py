#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module defines the main_menu_registry and main menu related helper functions.

Entries of the main_menu_registry must NOT be registered in this module to keep imports
in this module as small as possible.
"""

import copy
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.main_menu_types import MainMenu, MainMenuItem, MainMenuTopic, MainMenuTopicSegment


def any_show_more_items(topics: list[MainMenuTopic]) -> bool:
    return any(item.is_show_more for topic in topics for item in topic.entries)


def get_main_menu_items_prefixed_by_segment(
    entry_holder: MainMenuTopic | MainMenuTopicSegment,
    prefix: str | None = None,
) -> list[MainMenuItem]:
    collected_items: list[MainMenuItem] = []
    for entry in entry_holder.entries:
        if isinstance(entry, MainMenuTopicSegment):
            collected_items.extend(
                get_main_menu_items_prefixed_by_segment(entry, prefix=entry.title)
            )
        elif isinstance(entry, MainMenuItem):
            if prefix is not None:
                entry = copy.deepcopy(entry)
                entry.title = f"{prefix} | {entry.title}"
            collected_items.append(entry)
    return collected_items


class MainMenuRegistry(Registry[MainMenu]):
    """A registry that contains the menu entries of the main navigation.

    All menu entries must be obtained via this registry to avoid cyclic
    imports. To avoid typos it's recommended to use the helper methods
    menu_* to obtain the different entries.

    Examples:

        >>> from cmk.gui.i18n import _l
        >>> main_menu_registry.register(MainMenu(
        ...     name="monitoring",
        ...     title=_l("Monitor"),
        ...     icon="main_monitoring",
        ...     sort_index=5,
        ...     topics=lambda: [],
        ...     search=None,
        ... ))
        MainMenu(...)
        >>> assert main_menu_registry["monitoring"].sort_index == 5

    """

    @override
    def plugin_name(self, instance: MainMenu) -> str:
        return instance.name

    def menu_monitoring(self) -> MainMenu:
        return self["monitoring"]

    def menu_customize(self) -> MainMenu:
        return self["customize"]

    def menu_setup(self) -> MainMenu:
        return self["setup"]

    def menu_help(self) -> MainMenu:
        return self["help"]

    def menu_activate(self) -> MainMenu:
        return self["activate"]

    def menu_user(self) -> MainMenu:
        return self["user"]


main_menu_registry = MainMenuRegistry()
