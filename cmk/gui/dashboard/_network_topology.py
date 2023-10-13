#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.gui import visuals
from cmk.gui.view import View
from cmk.gui.views.store import get_permitted_views
from cmk.gui.visuals.filter import Filter


def get_topology_context_and_filters() -> tuple[Mapping[str, Mapping[str, str]], list[Filter]]:
    view_name = "topology_filters"
    view_spec = get_permitted_views()[view_name]
    view = View(view_name, view_spec, view_spec.get("context", {}))
    context = visuals.active_context_from_request(view.datasource.infos, view.spec["context"])
    filters = visuals.filters_of_visual(
        view.spec, view.datasource.infos, link_filters=view.datasource.link_filters
    )
    show_filters = visuals.visible_filters_of_visual(view.spec, filters)
    return context, show_filters
