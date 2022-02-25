#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import List

from cmk.gui.globals import html
from cmk.gui.i18n import _l
from cmk.gui.watolib.main_menu import (
    ABCMainModule,
    main_module_registry,
    main_module_topic_registry,
    MainModuleTopic,
    MenuItem,
)


class MainMenu:
    def __init__(self, items=None, columns=2):
        self._items = items or []
        self._columns = columns

    def add_item(self, item):
        self._items.append(item)

    def show(self):
        html.open_div(class_="mainmenu")
        for item in self._items:
            if not item.may_see():
                continue

            html.open_a(href=item.get_url(), onfocus="if (this.blur) this.blur();")
            html.icon(item.icon, item.title)
            html.div(item.title, class_="title")
            html.div(item.description, class_="subtitle")
            html.close_a()

        html.close_div()


class WatoModule(MenuItem):
    """Used with register_modules() in pre 1.6 versions to register main modules"""


def register_modules(*args):
    """Register one or more top level modules to Check_MK WATO.
    The registered modules are displayed in the navigation of WATO."""
    for wato_module in args:
        assert isinstance(wato_module, WatoModule)

        internal_name = re.sub("[^a-zA-Z]", "", wato_module.mode_or_url)

        cls = type(
            "LegacyMainModule%s" % internal_name.title(),
            (ABCMainModule,),
            {
                "mode_or_url": wato_module.mode_or_url,
                "topic": MainModuleTopicExporter,
                "title": wato_module.title,
                "icon": wato_module.icon,
                "permission": wato_module.permission,
                "description": wato_module.description,
                "sort_index": wato_module.sort_index,
                "is_show_more": False,
            },
        )
        main_module_registry.register(cls)


def get_modules() -> List[ABCMainModule]:
    return sorted(
        [m() for m in main_module_registry.values()], key=lambda m: (m.sort_index, m.title)
    )


#   .--Topics--------------------------------------------------------------.
#   |                     _____           _                                |
#   |                    |_   _|__  _ __ (_) ___ ___                       |
#   |                      | |/ _ \| '_ \| |/ __/ __|                      |
#   |                      | | (_) | |_) | | (__\__ \                      |
#   |                      |_|\___/| .__/|_|\___|___/                      |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Register the builtin topics. These are the ones that may be          |
#   | referenced by different WATO plugins. Additional individual plugins  |
#   | are allowed to create their own topics.                              |
#   '----------------------------------------------------------------------'
# .

MainModuleTopicHosts = main_module_topic_registry.register(
    MainModuleTopic(
        name="hosts",
        title=_l("Hosts"),
        icon_name="topic_hosts",
        sort_index=10,
    )
)

MainModuleTopicServices = main_module_topic_registry.register(
    MainModuleTopic(
        name="services",
        title=_l("Services"),
        icon_name="topic_services",
        sort_index=20,
    )
)

MainModuleTopicBI = main_module_topic_registry.register(
    MainModuleTopic(
        name="bi",
        title=_l("Business Intelligence"),
        icon_name="topic_bi",
        sort_index=30,
    )
)

MainModuleTopicAgents = main_module_topic_registry.register(
    MainModuleTopic(
        name="agents",
        title=_l("Agents"),
        icon_name="topic_agents",
        sort_index=40,
    )
)

MainModuleTopicEvents = main_module_topic_registry.register(
    MainModuleTopic(
        name="events",
        title=_l("Events"),
        icon_name="topic_events",
        sort_index=50,
    )
)

MainModuleTopicUsers = main_module_topic_registry.register(
    MainModuleTopic(
        name="users",
        title=_l("Users"),
        icon_name="topic_users",
        sort_index=60,
    )
)

MainModuleTopicGeneral = main_module_topic_registry.register(
    MainModuleTopic(
        name="general",
        title=_l("General"),
        icon_name="topic_general",
        sort_index=70,
    )
)

MainModuleTopicMaintenance = main_module_topic_registry.register(
    MainModuleTopic(
        name="maintenance",
        title=_l("Maintenance"),
        icon_name="topic_maintenance",
        sort_index=80,
    )
)

MainModuleTopicExporter = main_module_topic_registry.register(
    MainModuleTopic(
        name="exporter",
        title=_l("Exporter"),
        icon_name="topic_exporter",
        sort_index=150,
    )
)
