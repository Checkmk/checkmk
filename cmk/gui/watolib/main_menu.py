#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
from collections.abc import Iterable, Sequence
from typing import NamedTuple, override

import cmk.ccc.plugin_registry

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Icon
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.urls import makeuri_contextless


class MenuItem:
    def __init__(
        self,
        mode_or_url: str,
        title: str,
        icon: Icon,
        permission: str | None,
        description: str,
        sort_index: int = 20,
    ) -> None:
        self._mode_or_url = mode_or_url
        self._title = title
        self._icon = icon
        self._permission = permission
        self._description = description
        self._sort_index = sort_index

    @property
    def mode_or_url(self) -> str:
        return self._mode_or_url

    @property
    def title(self) -> str:
        return self._title

    @property
    def icon(self) -> Icon:
        return self._icon

    @property
    def permission(self) -> None | str:
        return self._permission

    @property
    def description(self) -> str:
        return self._description

    @property
    def sort_index(self) -> int:
        return self._sort_index

    @property
    def enabled(self) -> bool:
        return True

    def may_see(self) -> bool:
        """Whether or not the currently logged in user is allowed to see this module"""
        if not self.enabled:
            return False

        if self.permission is None:
            return True

        if "." not in self.permission:
            permission = "wato." + self.permission
        else:
            permission = self.permission

        return user.may(permission) or user.may("wato.seeall")

    def get_url(self) -> str:
        mode_or_url = self.mode_or_url
        if "?" in mode_or_url or "/" in mode_or_url or mode_or_url.endswith(".py"):
            return mode_or_url
        return makeuri_contextless(request, [("mode", mode_or_url)], filename="wato.py")

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mode_or_url={self.mode_or_url!r}, title={self.title!r}, icon={self.icon!r}, permission={self.permission!r}, description={self.description!r}, sort_index={self.sort_index!r})"


class MainModuleTopic(NamedTuple):
    name: str
    title: str | LazyString
    icon_name: str
    sort_index: int


class MainModuleTopicRegistry(cmk.ccc.plugin_registry.Registry[MainModuleTopic]):
    @override
    def plugin_name(self, instance: MainModuleTopic) -> str:
        return instance.name


main_module_topic_registry = MainModuleTopicRegistry()


class ABCMainModule(MenuItem, abc.ABC):
    def __init__(self) -> None:
        # TODO: Cleanup hierarchy
        super().__init__(
            mode_or_url="",
            title="",
            icon="menu",
            permission=None,
            description="",
        )

    @property
    @abc.abstractmethod
    def topic(self) -> MainModuleTopic:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def mode_or_url(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def icon(self) -> Icon:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def permission(self) -> None | str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def description(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    @override
    def sort_index(self) -> int:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_show_more(self) -> bool:
        raise NotImplementedError()

    @classmethod
    def additional_breadcrumb_items(cls) -> Iterable[BreadcrumbItem]:
        """This class method allows for adding additional items to the breadcrumb navigation"""
        return
        yield

    @classmethod
    def main_menu_search_terms(cls) -> Sequence[str]:
        """This class method allows adding additional match texts for the search"""
        return []


class MainModuleRegistry(cmk.ccc.plugin_registry.Registry[type[ABCMainModule]]):
    @override
    def plugin_name(self, instance: type[ABCMainModule]) -> str:
        return instance().mode_or_url


main_module_registry = MainModuleRegistry()


class WatoModule(MenuItem):
    """Used with register_modules() in pre 1.6 versions to register main modules"""


def register_modules(*args: WatoModule) -> None:
    """Register one or more top level modules to Checkmk Setup.
    The registered modules are displayed in the navigation of Setup."""
    for wato_module in args:
        assert isinstance(wato_module, WatoModule)

        internal_name = re.sub("[^a-zA-Z]", "", wato_module.mode_or_url)

        cls = type(
            "LegacyMainModule%s" % internal_name.title(),
            (ABCMainModule,),
            {
                "mode_or_url": wato_module.mode_or_url,
                "topic": main_module_topic_registry["exporter"],
                "title": wato_module.title,
                "icon": wato_module.icon,
                "permission": wato_module.permission,
                "description": wato_module.description,
                "sort_index": wato_module.sort_index,
                "is_show_more": False,
            },
        )
        main_module_registry.register(cls)
