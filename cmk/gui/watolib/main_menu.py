#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Iterable, NamedTuple, Optional, Type, Union

import cmk.utils.plugin_registry

from cmk.gui.breadcrumb import BreadcrumbItem
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Icon
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.urls import makeuri_contextless


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
    def title(self) -> str:
        return self._title

    @property
    def icon(self):
        return self._icon

    @property
    def permission(self) -> None | str:
        return self._permission

    @property
    def description(self):
        return self._description

    @property
    def sort_index(self) -> int:
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

        return user.may(permission) or user.may("wato.seeall")

    def get_url(self):
        mode_or_url = self.mode_or_url
        if "?" in mode_or_url or "/" in mode_or_url or mode_or_url.endswith(".py"):
            return mode_or_url
        return makeuri_contextless(request, [("mode", mode_or_url)], filename="wato.py")

    def __repr__(self):
        return (
            "%s(mode_or_url=%r, title=%r, icon=%r, permission=%r, description=%r, sort_index=%r)"
            % (
                self.__class__.__name__,
                self.mode_or_url,
                self.title,
                self.icon,
                self.permission,
                self.description,
                self.sort_index,
            )
        )


class MainModuleTopic(NamedTuple):
    name: str
    title: Union[str, LazyString]
    icon_name: str
    sort_index: int


class MainModuleTopicRegistry(cmk.utils.plugin_registry.Registry[MainModuleTopic]):
    def plugin_name(self, instance: MainModuleTopic) -> str:
        return instance.name


main_module_topic_registry = MainModuleTopicRegistry()


class ABCMainModule(MenuItem, abc.ABC):
    def __init__(self) -> None:
        # TODO: Cleanup hierarchy
        super().__init__(
            mode_or_url=None,
            title=None,
            icon=None,
            permission=None,
            description=None,
            sort_index=None,
        )

    @property
    @abc.abstractmethod
    def topic(self) -> MainModuleTopic:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def mode_or_url(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def icon(self) -> Icon:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def permission(self) -> None | str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def description(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
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
        yield  # pylint: disable=unreachable


class ModuleRegistry(cmk.utils.plugin_registry.Registry[Type[ABCMainModule]]):
    def plugin_name(self, instance):
        return instance().mode_or_url


main_module_registry = ModuleRegistry()
