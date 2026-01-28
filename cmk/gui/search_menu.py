#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass

from cmk.ccc.version import edition
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import (
    MainMenu,
    MainMenuData,
    MainMenuVueApp,
    UnifiedSearch,
)
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.shared_typing.unified_search import (
    Edition,
    Provider,
    Providers,
    UnifiedSearchProps,
)
from cmk.utils import paths


@dataclass(frozen=True, kw_only=True)
class UnifiedSearchMainMenuData(UnifiedSearchProps, MainMenuData): ...


def get_unified_search_config(request: Request) -> UnifiedSearchMainMenuData:
    return UnifiedSearchMainMenuData(
        providers=Providers(
            monitoring=Provider(active=True, sort=0),
            customize=Provider(active=False, sort=1),
            setup=Provider(active=False, sort=2),
        ),
        user_id=str(user.id),
        edition=Edition(edition(paths.omd_root).short),
        icons_per_item=bool(user.get_attribute("icons_per_item")),
    )


def register(mega_menu_registry: MainMenuRegistry) -> None:
    mega_menu_registry.register(
        MainMenu(
            name="search",
            title=_l("Search"),
            icon=StaticIcon(IconNames.main_search),
            sort_index=1,
            topics=None,
            search=UnifiedSearch("unified_search", "unified-search-input"),
            vue_app=MainMenuVueApp(
                name="cmk-unified-search",
                data=get_unified_search_config,
            ),
        )
    )
