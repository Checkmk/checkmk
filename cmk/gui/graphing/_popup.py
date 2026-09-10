#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import override

import cmk.gui.pages
from cmk import trace
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.htmllib.html import html
from cmk.gui.pages import PageContext, PageResult
from cmk.shared_typing.cmk_time_series_graph import Interaction, Size
from cmk.utils.servicename import ServiceName

from ._frontend import EngineDisplayOptions, render_engine_graph_group
from ._graph_templates import get_template_graph_specification

tracer = trace.get_tracer()

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
            size=Size(width=popup_size[0], height=popup_size[1], mode="fixed"),
            time_range=(start_time, end_time),
            interaction=_HOVER_INTERACTION,
            show_graph_time=True,
            display=EngineDisplayOptions(show_consolidation=False, show_legend=False),
            multi_column=True,
            debug=debug,
        )
    )
    html.close_div()


class PageHostServiceGraphPopup(cmk.gui.pages.Page):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        host_service_graph_popup_cmk(
            SiteId(raw_site_id) if (raw_site_id := ctx.request.var("site")) else None,
            ctx.request.get_validated_type_input_mandatory(HostName, "host_name"),
            ServiceName(ctx.request.get_str_input_mandatory("service")),
            debug=ctx.config.debug,
        )
        return None
