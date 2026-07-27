#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final, Protocol, runtime_checkable

from cmk.gui.graphing._engine_discovery import DiscoveredGraphs
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.roles import UserPermissions

from .api.model.widget_content.graph import (
    CombinedGraphContent,
    CustomGraphContent,
    PerformanceGraphContent,
    ProblemGraphContent,
    SingleTimeseriesContent,
)
from .api.model.widget_content.metric import AverageScatterplotContent
from .dashlet.registry import dashlet_registry
from .token_util import InvalidWidgetError
from .type_defs import DashletConfig

# The widget types the client-side graph rendering covers, by internal (stored) type name. Must
# stay in step with the types DashboardContent.vue routes to the client-side graph widget: a type
# missing here has no pre-discovered shell on a shared dashboard and cannot render.
GRAPH_WIDGET_TYPES: Final = frozenset(
    {
        AverageScatterplotContent.internal_type(),
        CombinedGraphContent.internal_type(),
        CustomGraphContent.internal_type(),
        PerformanceGraphContent.internal_type(),
        ProblemGraphContent.internal_type(),
        SingleTimeseriesContent.internal_type(),
    }
)


@runtime_checkable
class GraphDiscoveringDashlet(Protocol):
    """What `discover_widget_graphs` needs of a widget.

    The graph widgets do not share one base class (the average scatterplot is a figure widget),
    so the capability is expressed structurally rather than by inheritance.
    """

    def discover_graphs(
        self, *, debug: bool, user_permissions: UserPermissions
    ) -> DiscoveredGraphs: ...


def discover_widget_graphs(
    widget_config: DashletConfig,
    dashboard_context: VisualContext | None,
    *,
    debug: bool,
    user_permissions: UserPermissions,
) -> DiscoveredGraphs:
    """Discover the graph shells of one client-side rendered graph widget."""
    if widget_config["type"] not in GRAPH_WIDGET_TYPES:
        raise InvalidWidgetError

    try:
        widget_type = dashlet_registry[widget_config["type"]]
    except KeyError:
        # likely an edition downgrade where the graph type is not available anymore
        raise InvalidWidgetError(disable_token=True) from None

    widget = widget_type(widget_config, dashboard_context)
    if not isinstance(widget, GraphDiscoveringDashlet):
        raise InvalidWidgetError
    return widget.discover_graphs(debug=debug, user_permissions=user_permissions)
