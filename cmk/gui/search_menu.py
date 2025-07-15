#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from typing import override

from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.type_defs import ABCMainMenuSearch, MainMenu, MainMenuData, MainMenuVueApp
from cmk.gui.wato._snapins import _hide_menu
from cmk.shared_typing.unified_search import Provider, Providers, UnifiedSearchConfig


@dataclass
class UnifiedSearchMainMenuData(UnifiedSearchConfig, MainMenuData): ...


def get_unified_search_config(request: Request) -> UnifiedSearchMainMenuData:
    return UnifiedSearchMainMenuData(
        providers=Providers(
            monitoring=Provider(active=True, sort=-1),
            customize=Provider(active=True, sort=-1),
            setup=Provider(active=not _hide_menu(), sort=-1),
        )
    )


def register(mega_menu_registry: MainMenuRegistry) -> None:
    mega_menu_registry.register(
        MainMenu(
            name="search",
            title=_("Search"),
            icon="main_search",
            sort_index=1,
            topics=None,
            search=UnifiedSearch("unified_search"),
            vue_app=MainMenuVueApp(
                name="cmk-unified-search",
                data=get_unified_search_config,
            ),
            hide=lambda: True,  # remove to activate unified search in main menu
        )
    )


class UnifiedSearch(ABCMainMenuSearch):
    """Search wrapper for proper menu handling of the unified search"""

    @override
    @property
    def onopen(self) -> str:
        return 'cmk.popup_menu.focus_search_field("unified-search-input");'

    @override
    def show_search_field(self) -> None: ...
