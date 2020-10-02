#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
from typing import Optional, NamedTuple, List, Type

from cmk.gui.i18n import _l
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.utils.plugin_registry
from cmk.gui.globals import html


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


class MenuItem:
    def __init__(self, mode_or_url, title, icon, permission, description, sort_index=20):
        self._mode_or_url = mode_or_url
        self._title = title
        self._icon = icon
        self._permission = permission
        self._description = description
        self._sort_index = sort_index

    @property
    def mode_or_url(self):
        return self._mode_or_url

    @property
    def title(self):
        return self._title

    @property
    def icon(self):
        return self._icon

    @property
    def permission(self):
        return self._permission

    @property
    def description(self):
        return self._description

    @property
    def sort_index(self):
        return self._sort_index

    @property
    def enabled(self) -> bool:
        return True

    def may_see(self):
        """Whether or not the currently logged in user is allowed to see this module"""
        if not self.enabled:
            return False

        if self.permission is None:
            return True

        if "." not in self.permission:
            permission = "wato." + self.permission
        else:
            permission = self.permission

        return config.user.may(permission) or config.user.may("wato.seeall")

    def get_url(self):
        mode_or_url = self.mode_or_url
        if '?' in mode_or_url or '/' in mode_or_url or mode_or_url.endswith(".py"):
            return mode_or_url
        return watolib.folder_preserving_link([("mode", mode_or_url)])

    def __repr__(self):
        return "%s(mode_or_url=%r, title=%r, icon=%r, permission=%r, description=%r, sort_index=%r)" % \
            (self.__class__.__name__, self.mode_or_url, self.title, self.icon, self.permission, self.description, self.sort_index)


MainModuleTopic = NamedTuple("MainModuleTopic", [
    ("name", str),
    ("title", str),
    ("icon_name", str),
    ("sort_index", int),
])


class MainModuleTopicRegistry(cmk.utils.plugin_registry.Registry[MainModuleTopic]):
    def plugin_name(self, instance: MainModuleTopic) -> str:
        return instance.name


main_module_topic_registry = MainModuleTopicRegistry()


# TODO: Rename to ABCMainModule
class MainModule(MenuItem, metaclass=abc.ABCMeta):
    def __init__(self):
        # TODO: Cleanup hierarchy
        super(MainModule, self).__init__(mode_or_url=None,
                                         title=None,
                                         icon=None,
                                         permission=None,
                                         description=None,
                                         sort_index=None)

    @abc.abstractproperty
    def topic(self) -> MainModuleTopic:
        raise NotImplementedError()

    @abc.abstractproperty
    def mode_or_url(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def icon(self) -> str:
        raise NotImplementedError()

    @property
    def emblem(self) -> Optional[str]:
        return None

    @abc.abstractproperty
    def permission(self) -> Optional[str]:
        raise NotImplementedError()

    @abc.abstractproperty
    def description(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def sort_index(self) -> int:
        raise NotImplementedError()

    @abc.abstractproperty
    def is_advanced(self) -> bool:
        raise NotImplementedError()


class ModuleRegistry(cmk.utils.plugin_registry.Registry[Type[MainModule]]):
    def plugin_name(self, instance):
        return instance().mode_or_url


main_module_registry = ModuleRegistry()


class WatoModule(MenuItem):
    """Used with register_modules() in pre 1.6 versions to register main modules"""


def register_modules(*args):
    """Register one or more top level modules to Check_MK WATO.
    The registered modules are displayed in the navigation of WATO."""
    for wato_module in args:
        assert isinstance(wato_module, WatoModule)

        internal_name = re.sub("[^a-zA-Z]", "", wato_module.mode_or_url)

        cls = type(
            "LegacyMainModule%s" % internal_name.title(), (MainModule,), {
                "mode_or_url": wato_module.mode_or_url,
                "topic": MainModuleTopicCustom,
                "title": wato_module.title,
                "icon": wato_module.icon,
                "permission": wato_module.permission,
                "description": wato_module.description,
                "sort_index": wato_module.sort_index,
                "is_advanced": False,
            })
        main_module_registry.register(cls)


def get_modules() -> List[MainModule]:
    return sorted([m() for m in main_module_registry.values()],
                  key=lambda m: (m.sort_index, m.title))


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
#.

MainModuleTopicHosts = main_module_topic_registry.register(
    MainModuleTopic(
        name="hosts",
        title=_l("Hosts"),
        icon_name="topic_hosts",
        sort_index=10,
    ))

MainModuleTopicServices = main_module_topic_registry.register(
    MainModuleTopic(
        name="services",
        title=_l("Services"),
        icon_name="topic_services",
        sort_index=20,
    ))

MainModuleTopicBI = main_module_topic_registry.register(
    MainModuleTopic(
        name="bi",
        title=_l("Business Intelligence"),
        icon_name="topic_bi",
        sort_index=30,
    ))

MainModuleTopicAgents = main_module_topic_registry.register(
    MainModuleTopic(
        name="agents",
        title=_l("Agents"),
        icon_name="topic_agents",
        sort_index=40,
    ))

MainModuleTopicEvents = main_module_topic_registry.register(
    MainModuleTopic(
        name="events",
        title=_l("Events"),
        icon_name="topic_events",
        sort_index=50,
    ))

MainModuleTopicUsers = main_module_topic_registry.register(
    MainModuleTopic(
        name="users",
        title=_l("Users"),
        icon_name="topic_users",
        sort_index=60,
    ))

MainModuleTopicGeneral = main_module_topic_registry.register(
    MainModuleTopic(
        name="general",
        title=_l("General"),
        icon_name="topic_general",
        sort_index=70,
    ))

MainModuleTopicMaintenance = main_module_topic_registry.register(
    MainModuleTopic(
        name="maintenance",
        title=_l("Maintenance"),
        icon_name="topic_maintenance",
        sort_index=80,
    ))

MainModuleTopicCustom = main_module_topic_registry.register(
    MainModuleTopic(
        name="custom",
        title=_l("Custom"),
        icon_name="topic_custom",
        sort_index=150,
    ))
