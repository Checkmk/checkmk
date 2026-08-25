#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cmk.gui.http import Request
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.speaklater import LazyString
from cmk.shared_typing.main_menu import (
    NavBaseItem,
    NavItem,
    NavItemTopic,
    NavItemVueApp,
    NavLinkItem,
)


@dataclass(frozen=True, kw_only=True)
class MainMenuItemBase:
    title: LazyString
    hint: LazyString | None = None


@dataclass(frozen=True, kw_only=True)
class MainMenuItem(MainMenuItemBase, NavItem):
    hide: Callable[[], bool] | None = None
    info_line: Callable[[], str] | None = None
    get_topics: Callable[[UserPermissions], Iterable[NavItemTopic]] | None = None
    get_vue_app: Callable[[Request], NavItemVueApp] | None = None


@dataclass(frozen=True, kw_only=True)
class MainMenuLinkItem(MainMenuItemBase, NavLinkItem):
    hide: Callable[[], bool] | None = None
    get_url: Callable[[Request], str] | None = None


@dataclass(frozen=True, kw_only=True)
class ConfigurableMainMenuItem(MainMenuItemBase, NavBaseItem):
    hide: Callable[[], bool] | None = None
    get_item_instance: Callable[
        [ConfigurableMainMenuItem, LoggedInUser], MainMenuLinkItem | MainMenuItem
    ]
