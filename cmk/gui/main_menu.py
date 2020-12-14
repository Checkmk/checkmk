#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module defines the main_menu_registry and main menu related helper functions.

Entries of the main_menu_registry must NOT be registered in this module to keep imports
in this module as small as possible.
"""

from typing import List

from cmk.utils.plugin_registry import Registry
from cmk.utils.version import __version__, edition_title
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import MegaMenu, TopicMenuTopic, TopicMenuItem


def any_show_more_items(topics: List[TopicMenuTopic]) -> bool:
    return any(item.is_show_more for topic in topics for item in topic.items)


class MegaMenuRegistry(Registry[MegaMenu]):
    """A registry that contains the menu entries of the main navigation.

    All menu entries must be obtained via this registry to avoid cyclic
    imports. To avoid typos it's recommended to use the helper methods
    menu_* to obtain the different entries.

    Examples:

        >>> from cmk.gui.i18n import _l
        >>> from cmk.gui.type_defs import MegaMenu
        >>> from cmk.gui.main_menu import mega_menu_registry
        >>> mega_menu_registry.register(MegaMenu(
        ...     name="monitoring",
        ...     title=_l("Monitor"),
        ...     icon="main_monitoring",
        ...     sort_index=5,
        ...     topics=lambda: [],
        ...     search=None,
        ... ))
        MegaMenu(...)
        >>> assert mega_menu_registry["monitoring"].sort_index == 5

    """
    def plugin_name(self, instance: MegaMenu) -> str:
        return instance.name

    def menu_monitoring(self) -> MegaMenu:
        return self["monitoring"]

    def menu_customize(self) -> MegaMenu:
        return self["customize"]

    def menu_setup(self) -> MegaMenu:
        return self["setup"]

    def menu_help(self) -> MegaMenu:
        return self["help"]

    def menu_user(self) -> MegaMenu:
        return self["user"]


mega_menu_registry = MegaMenuRegistry()


def _help_menu_topics() -> List[TopicMenuTopic]:
    return [
        TopicMenuTopic(
            name="external_help",
            title=_("External links"),
            icon=None,  # TODO(CMK-5773): add an icon
            items=[
                TopicMenuItem(
                    name="manual",
                    title=_("Manual"),
                    url="https://checkmk.com/cms.html",
                    target="_blank",
                    sort_index=30,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
                TopicMenuItem(
                    name="forum",
                    title=_("Forum"),
                    url="https://forum.checkmk.com/",
                    target="_blank",
                    sort_index=40,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
                TopicMenuItem(
                    name="youtube_channel",
                    title=_("YouTube"),
                    url="https://www.youtube.com/checkmk-channel",
                    target="_blank",
                    sort_index=50,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
            ],
        ),
        TopicMenuTopic(
            name="local_help",
            title=_("Internal links"),
            icon=None,
            items=[
                TopicMenuItem(
                    name="rest_api_redoc",
                    title=_("REST API documentation"),
                    url="openapi/",
                    target="_blank",
                    sort_index=30,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
                TopicMenuItem(
                    name="rest_api_swagger_ui",
                    title=_("REST API interactive GUI"),
                    url="api/v0/ui/",
                    target="_blank",
                    sort_index=30,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
                TopicMenuItem(
                    name="plugin_api",
                    title=_("Plugin API documentation"),
                    url="plugin-api/",
                    target="_blank",
                    sort_index=40,
                    icon=None,  # TODO(CMK-5773): add an icon
                ),
            ]),
    ]


mega_menu_registry.register(
    MegaMenu(name="help_links",
             title=_l("Help"),
             icon="main_help",
             sort_index=18,
             topics=_help_menu_topics,
             info_line=lambda: f"{__version__} ({edition_title()})"))
