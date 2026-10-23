#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui.i18n import _l
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.search.permissions import CategoryPermissionsHandlerRegistry
from cmk.gui.type_defs import ViewName
from cmk.gui.visuals import BuiltinVisualsSearch, CustomVisualsSearch
from cmk.web.utils.urls import urlencode_vars

from .store import get_all_views, ViewStore


def register(
    match_item_generator_registry: MatchItemGeneratorRegistry,
    category_permissions_handler_registry: CategoryPermissionsHandlerRegistry,
) -> None:
    BuiltinVisualsSearch(
        what="views",
        topic=_l("Built-in views"),
        load_all=get_all_views,
        url=_clone_url,
    ).register(match_item_generator_registry, category_permissions_handler_registry)
    CustomVisualsSearch(
        what="views",
        topic=_l("Custom views"),
        load_all=ViewStore.load_all_views,
        url=_edit_url,
    ).register(match_item_generator_registry, category_permissions_handler_registry)


def _clone_url(name: ViewName) -> str:
    return "edit_view.py?" + urlencode_vars(
        [("mode", "clone"), ("owner", UserId.builtin()), ("load_name", name)]
    )


def _edit_url(name: ViewName, owner: UserId) -> str:
    return "edit_view.py?" + urlencode_vars(
        [("mode", "edit"), ("owner", owner), ("load_name", name)]
    )
