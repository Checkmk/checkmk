#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.version import edition
from cmk.gui.http import Request
from cmk.gui.i18n import _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import MainMenuItem
from cmk.shared_typing.main_menu import (
    NavItemIdEnum,
    NavItemShortcut,
    NavItemVueApp,
    NavVueAppIdEnum,
)
from cmk.shared_typing.unified_search import Edition, Provider, Providers, UnifiedSearchProps
from cmk.utils import paths


def get_unified_search_props(request: Request) -> UnifiedSearchProps:
    return UnifiedSearchProps(
        providers=Providers(
            monitoring=Provider(active=True, sort=0),
            customize=Provider(active=False, sort=1),
            setup=Provider(active=False, sort=2),
        ),
        user_id=str(user.id),
        edition=Edition(edition(paths.omd_root).short),
        icons_per_item=bool(user.get_attribute("icons_per_item")),
    )


def _get_unified_search_app(request: Request) -> NavItemVueApp:
    return NavItemVueApp(id=NavVueAppIdEnum.cmk_unified_search)


def register(mega_menu_registry: MainMenuRegistry) -> None:
    mega_menu_registry.register(
        MainMenuItem(
            id=NavItemIdEnum.search,
            title=_l("Search"),
            sort_index=1,
            topics=None,
            set_focus_on_element_by_id="unified-search-input",
            shortcut=NavItemShortcut(key="k", ctrl=True),
            get_vue_app=_get_unified_search_app,
            hint=_l("Search across Checkmk"),
        )
    )
