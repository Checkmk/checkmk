#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, NamedTuple, override

from cmk.gui.http import Request
from cmk.gui.type_defs import DynamicIcon, StaticIcon
from cmk.gui.utils.loading_transition import LoadingTransition
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.speaklater import LazyString


@dataclass(kw_only=True, slots=True)
class _MainMenuEntry:
    name: str
    title: str
    sort_index: int
    is_show_more: bool = False
    icon: StaticIcon | DynamicIcon | None = None


@dataclass(kw_only=True, slots=True)
class MainMenuItem(_MainMenuEntry):
    url: str
    target: str = "main"
    button_title: str | None = None
    main_menu_search_terms: Sequence[str] = ()
    loading_transition: LoadingTransition | None = None


@dataclass(kw_only=True, slots=True)
class MainMenuTopicSegment(_MainMenuEntry):
    mode: Literal["multilevel", "indented"]
    entries: list[MainMenuItem | MainMenuTopicSegment]
    max_entries: int = 10
    hide: bool = False


MainMenuTopicEntries = list[MainMenuItem | MainMenuTopicSegment]


class MainMenuTopic(NamedTuple):
    name: str
    title: str
    entries: MainMenuTopicEntries
    max_entries: int = 10
    icon: StaticIcon | DynamicIcon | None = None
    hide: bool = False


@dataclass(frozen=True, kw_only=True)
class MainMenuData: ...


@dataclass
class MainMenuVueApp:
    name: str
    data: Callable[[Request], MainMenuData] | MainMenuData


class MainMenu(NamedTuple):
    name: str
    title: str | LazyString
    icon: StaticIcon | DynamicIcon
    sort_index: int
    topics: Callable[[UserPermissions], list[MainMenuTopic]] | None
    search: ABCMainMenuSearch | None = None
    info_line: Callable[[], str] | None = None
    hide: Callable[[], bool] = lambda: False
    vue_app: MainMenuVueApp | None = None
    onopen: str | None = None
    hint: str | None = None


class ABCMainMenuSearch(ABC):
    """Abstract base class for search fields in main menus"""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def onopen(self) -> str:
        return 'cmk.popup_menu.focus_search_field("mk_side_search_field_%s");' % self.name

    @abstractmethod
    def show_search_field(self) -> None: ...


class UnifiedSearch(ABCMainMenuSearch):
    """Search wrapper for proper menu handling of the unified search"""

    def __init__(self, name: str, focus_id: str) -> None:
        self._name = name
        self._focus_id = focus_id

    @override
    @property
    def onopen(self) -> str:
        return f'cmk.popup_menu.focus_search_field("{self._focus_id}");'

    @override
    def show_search_field(self) -> None: ...
