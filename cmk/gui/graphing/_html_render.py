#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import traceback

from pydantic import BaseModel, field_validator, SerializeAsAny

from cmk import trace
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.shared_typing.cmk_time_series_graph import Interaction, Size
from cmk.utils.servicename import ServiceName
from cmk.web.utils.html import HTML

from ._frontend import render_engine_graph_group
from ._graph_metric_expressions import GraphConsolidationFunction
from ._graph_specification import (
    GraphSpecification,
    parse_graph_specification,
)
from ._graph_templates import (
    get_template_graph_specification,
)

tracer = trace.get_tracer()


class GraphExportRequest(BaseModel, frozen=True):
    """Typed model for the request sent to graph_export.py and graph_image.py.

    Also stored as popup_data[2] for the graph 'Add to' and export actions.
    The browser forwards the whole object as the ?request= parameter when the
    user picks "Export as JSON" or "Export as PNG"; add-to backends (dashboard,
    report, graph collection, custom graph) only consume specification.
    """

    # Identifies which graph to render; consumed by every backend.
    specification: SerializeAsAny[GraphSpecification]
    # Forwarded to graph_export/graph_image; unused by add-to backends.
    consolidation_function: GraphConsolidationFunction = "max"
    # Forwarded to graph_export/graph_image; defaults to 25 h ago when None.
    time_start: int | None = None
    # Forwarded to graph_export/graph_image; defaults to now when None.
    time_end: int | None = None

    @field_validator("specification", mode="before")
    @classmethod
    def _parse_specification(cls, value: object) -> GraphSpecification:
        if isinstance(value, GraphSpecification):
            return value
        return parse_graph_specification(value)


def render_graph_error_html(*, title: str, msg_or_exc: Exception | str, debug: bool) -> HTML:
    if isinstance(msg_or_exc, MKGeneralException) and not debug:
        msg = "%s" % msg_or_exc

    elif isinstance(msg_or_exc, Exception):
        if debug:
            raise msg_or_exc
        msg = traceback.format_exc()
    else:
        msg = msg_or_exc

    return HTMLWriter.render_div(
        HTMLWriter.render_div(title, class_="title") + HTMLWriter.render_pre(msg),
        class_=["graph", "brokengraph"],
    )


# The hover graphs (on hovering a service graph icon) are all static - no interaction.
_HOVER_INTERACTION = Interaction(
    burger="disabled",
    zoom="disabled",
    panning="disabled",
    hover="disabled",
    brush="disabled",
    pin="disabled",
)


@tracer.instrument("graphing.host_service_graph_popup_cmk")
def host_service_graph_popup_cmk(
    site: SiteId | None,
    host_name: HostName,
    service_description: ServiceName,
    *,
    debug: bool,
) -> None:
    end_time = int(time.time())
    start_time = end_time - 8 * 3600
    popup_size = (30.0, 10.0)

    html.open_div(class_="cmk_graph_hover")
    html.write_html(
        render_engine_graph_group(
            get_template_graph_specification(
                site_id=site,
                host_name=host_name,
                service_name=service_description,
            ),
            host_name=host_name,
            service_name=service_description,
            size=Size(width=popup_size[0], height=popup_size[1], mode="fixed"),
            time_range=(start_time, end_time),
            interaction=_HOVER_INTERACTION,
            show_graph_time=True,
            show_consolidation=False,
            show_legend=False,
            multi_column=True,
            debug=debug,
        )
    )
    html.close_div()


class GraphDestinations:
    dashlet = "dashlet"
    view = "view"
    report = "report"
    notification = "notification"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [
            (GraphDestinations.dashlet, _("Dashboard element")),
            (GraphDestinations.view, _("View")),
            (GraphDestinations.report, _("Report")),
            (GraphDestinations.notification, _("Notification")),
        ]
