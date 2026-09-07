#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module defines the main_menu_registry and main menu related helper functions.

Entries of the main_menu_registry must NOT be registered in this module to keep imports
in this module as small as possible.
"""

import copy
import dataclasses
from typing import override

from cmk.ccc.plugin_registry import Registry
from cmk.gui.main_menu_types import ConfigurableMainMenuItem, MainMenuItem, MainMenuLinkItem
from cmk.shared_typing.main_menu import (
    NavItemIdEnum,
    NavItemTopic,
    NavItemTopicEntry,
    TopicItemMode,
)


def any_show_more_items(topics: list[NavItemTopic]) -> bool:
    return any(item.is_show_more for topic in topics for item in topic.entries)


def get_main_menu_items_prefixed_by_segment(
    entry_holder: NavItemTopic | NavItemTopicEntry,
    prefix: str | None = None,
) -> list[NavItemTopicEntry]:
    collected_items: list[NavItemTopicEntry] = []
    if entry_holder.entries:
        for entry in entry_holder.entries:
            if entry.mode in [TopicItemMode.indented, TopicItemMode.multilevel]:
                collected_items.extend(
                    get_main_menu_items_prefixed_by_segment(entry, prefix=entry.title)
                )
            else:
                if prefix is not None:
                    entry = copy.deepcopy(entry)
                    entry = dataclasses.replace(entry, title=f"{prefix} | {entry.title}")
                collected_items.append(entry)
    return collected_items


class MainMenuRegistry(Registry[MainMenuItem | MainMenuLinkItem | ConfigurableMainMenuItem]):
    """A registry that contains the menu entries of the main navigation."""

    @override
    def plugin_name(
        self, instance: MainMenuItem | MainMenuLinkItem | ConfigurableMainMenuItem
    ) -> str:
        return instance.id

    def menu_search(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.search)

    def menu_monitoring(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.monitoring)

    def menu_customize(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.customize)

    def menu_setup(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.setup)

    def menu_help(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.help)

    def menu_activate(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.changes)

    def menu_user(self) -> MainMenuItem:
        return self._get_item_by_id(NavItemIdEnum.user)

    def _get_item_by_id(self, id: str) -> MainMenuItem:  # noqa: A002
        item = self[id]
        assert isinstance(item, MainMenuItem)
        return item


main_menu_registry = MainMenuRegistry()
