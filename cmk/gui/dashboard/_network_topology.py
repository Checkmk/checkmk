#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.ccc.user import UserId

from cmk.gui import visuals
from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request
from cmk.gui.view import View
from cmk.gui.views.page_show_view import get_all_active_filters
from cmk.gui.views.store import get_all_views, get_permitted_views
from cmk.gui.visuals.filter import Filter


def get_topology_context_and_filters() -> tuple[Mapping[str, Mapping[str, str]], list[Filter]]:
    view_name = "topology_filters"
    view_spec = visuals.get_permissioned_visual(
        view_name,
        request.get_validated_type_input(UserId, "owner"),
        "view",
        get_permitted_views(),
        get_all_views(),
    )

    datasource = data_source_registry[view_spec["datasource"]]()
    context = visuals.active_context_from_request(datasource.infos, view_spec["context"])
    view = View(view_name, view_spec, context)
    return context, visuals.visible_filters_of_visual(view.spec, get_all_active_filters(view))
