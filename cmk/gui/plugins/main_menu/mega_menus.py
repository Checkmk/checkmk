#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu - Content of the mega menus

Registers the different mega menus and builds the content for each of them.
"""

from typing import List

import cmk.gui.config as config
import cmk.gui.pagetypes as pagetypes
from cmk.gui.i18n import _, _l
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.plugins.main_menu import (
    mega_menu_registry,
    MegaMenu,
    TopicMenuTopic,
    TopicMenuItem,
)


def make_main_menu_breadcrumb(menu: MegaMenu) -> Breadcrumb:
    return Breadcrumb([BreadcrumbItem(
        title=menu.title,
        url=None,
    )])


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


def _configure_menu_topics() -> List[TopicMenuTopic]:
    monitoring_items = [
        TopicMenuItem(
            name="views",
            title=_("Views"),
            url="edit_views.py",
            sort_index=10,
            is_advanced=False,
            icon_name="view",
        ),
        TopicMenuItem(
            name="dashboards",
            title=_("Dashboards"),
            url="edit_dashboards.py",
            sort_index=20,
            is_advanced=False,
            icon_name="dashboard",
        ),
    ]

    graph_items = []

    for index, page_type in enumerate(pagetypes.all_page_types().values()):
        item = TopicMenuItem(
            name=page_type.type_name(),
            title=page_type.phrase("title_plural"),
            url="%ss.py" % page_type.type_name(),
            sort_index=30 + (index * 10),
            is_advanced=False,
            icon_name=page_type.type_name(),
        )

        if "graph" in page_type.type_name():
            graph_items.append(item)
        else:
            monitoring_items.append(item)

    return [
        TopicMenuTopic(
            name="monitoring",
            title=_("Monitoring"),
            icon_name="topic_configure",
            items=monitoring_items,
        ),
        TopicMenuTopic(
            name="graphs",
            title=_("Graphs"),
            icon_name="topic_graphs",
            items=graph_items,
        )
    ]


MegaMenuConfigure = mega_menu_registry.register(
    MegaMenu(
        name="configure",
        title=_l("Configure"),
        icon_name="main_configure",
        sort_index=15,
        topics=_configure_menu_topics,
    ))
