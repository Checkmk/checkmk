#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu facilities"""

from typing import List

from cmk.utils.plugin_registry import InstanceRegistry

import cmk.gui.config as config
from cmk.gui.i18n import _, _l
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.type_defs import (
    MegaMenu,
    TopicMenuTopic,
    TopicMenuItem,
)


def any_advanced_items(topics: List[TopicMenuTopic]) -> bool:
    return any(item.is_advanced for topic in topics for item in topic.items)


class MegaMenuRegistry(InstanceRegistry):
    def plugin_base_class(self):
        return MegaMenu


mega_menu_registry = MegaMenuRegistry()


def _view_menu_topics() -> List[TopicMenuTopic]:
    from cmk.gui.plugins.sidebar.views import get_view_menu_items
    return get_view_menu_items()


MegaMenuMonitoring = mega_menu_registry.register(
    MegaMenu(
        name="monitoring",
        title=_l("Monitor"),
        icon_name="main_monitoring",
        sort_index=5,
        topics=_view_menu_topics,
    ))


def _setup_menu_topics() -> List[TopicMenuTopic]:
    from cmk.gui.plugins.sidebar.wato import get_wato_menu_items
    return get_wato_menu_items()


MegaMenuSetup = mega_menu_registry.register(
    MegaMenu(
        name="setup",
        title=_l("Setup"),
        icon_name="main_setup",
        sort_index=15,
        topics=_setup_menu_topics,
    ))


def _user_menu_topics() -> List[TopicMenuTopic]:
    items = [
        TopicMenuItem(
            name="change_password",
            title=_("Change password"),
            url="user_change_pw.py",
            sort_index=10,
            is_advanced=False,
            icon_name="topic_change_password",
        ),
        TopicMenuItem(
            name="user_profile",
            title=_("Edit profile"),
            url="user_profile.py",
            sort_index=20,
            is_advanced=False,
            icon_name="topic_profile",
        ),
        TopicMenuItem(
            name="logout",
            title=_("Logout"),
            url="logout.py",
            sort_index=30,
            is_advanced=False,
            icon_name="sidebar_logout",
        ),
    ]

    if rulebased_notifications_enabled() and config.user.may('general.edit_notifications'):
        items.insert(
            1,
            TopicMenuItem(
                name="notification_rules",
                title=_("Notification rules"),
                url="wato.py?mode=user_notifications_p",
                sort_index=30,
                is_advanced=False,
                icon_name="topic_events",
            ))

    return [TopicMenuTopic(
        name="user",
        title=_("User"),
        icon_name="topic_profile",
        items=items,
    )]


MegaMenuUser = mega_menu_registry.register(
    MegaMenu(
        name="user",
        title=_l("User"),
        icon_name="main_user",
        sort_index=20,
        topics=_user_menu_topics,
    ))
