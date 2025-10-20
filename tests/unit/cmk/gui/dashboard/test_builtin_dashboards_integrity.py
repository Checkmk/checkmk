#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

from cmk.gui.dashboard import builtin_dashboards
from cmk.gui.dashboard.dashlet.dashlets.graph import (
    TemplateGraphDashlet,
    TemplateGraphDashletConfig,
)
from cmk.gui.graphing._from_api import graphs_from_api
from cmk.gui.graphing._graph_templates import get_graph_plugin_from_id


def test_all_template_graph_dashlets_reference_known_graph_templates() -> None:
    for dashboard_config in builtin_dashboards.values():
        for dashlet_config in dashboard_config["dashlets"]:
            if dashlet_config["type"] == TemplateGraphDashlet.type_name():
                source = cast(TemplateGraphDashletConfig, dashlet_config)["source"]
                assert isinstance(source, str), "Graph source must be string identifier"
                get_graph_plugin_from_id(graphs_from_api, source)
