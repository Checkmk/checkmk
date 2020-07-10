#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main menu - Content of the mega menus

Registers the different mega menus and builds the content for each of them.
"""

from typing import List

from cmk.gui.i18n import _
from cmk.gui.plugins.main_menu import (
    mega_menu_registry,
    MegaMenu,
    TopicMenuTopic,
)


def _view_menu_topics() -> List[TopicMenuTopic]:
    from cmk.gui.plugins.sidebar.views import get_view_menu_items
    return get_view_menu_items()


MegaMenuMonitoring = mega_menu_registry.register(
    MegaMenu(
        name="monitoring",
        title=_("Monitor"),
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
        title=_("Setup"),
        icon_name="main_setup",
        sort_index=5,
        topics=_setup_menu_topics,
    ))
