#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.user import UserId
from cmk.gui.i18n import _l
from cmk.gui.search.matchers import MatchItemGeneratorRegistry
from cmk.gui.search.permissions import CategoryPermissionsHandlerRegistry
from cmk.gui.visuals import BuiltinVisualsSearch, CustomVisualsSearch
from cmk.web.utils.urls import urlencode_vars

from .store import DashboardStore, get_all_dashboards
from .type_defs import DashboardName


def register(
    match_item_generator_registry: MatchItemGeneratorRegistry,
    category_permissions_handler_registry: CategoryPermissionsHandlerRegistry,
) -> None:
    BuiltinVisualsSearch(
        what="dashboards",
        topic=_l("Built-in dashboards"),
        load_all=get_all_dashboards,
        url=_clone_url,
    ).register(match_item_generator_registry, category_permissions_handler_registry)
    CustomVisualsSearch(
        what="dashboards",
        topic=_l("Custom dashboards"),
        load_all=DashboardStore.load_all,
        url=_edit_url,
    ).register(match_item_generator_registry, category_permissions_handler_registry)


def _clone_url(name: DashboardName) -> str:
    return "dashboard.py?" + urlencode_vars(
        [("mode", "clone"), ("owner", UserId.builtin()), ("name", name)]
    )


def _edit_url(name: DashboardName, owner: UserId) -> str:
    return "dashboard.py?" + urlencode_vars(
        [("mode", "edit_settings"), ("owner", owner), ("name", name)]
    )
