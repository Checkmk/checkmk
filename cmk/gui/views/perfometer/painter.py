#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.display_options import display_options
from cmk.gui.graphing import metrics_from_api, perfometers_from_api
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter.v1.helpers import is_stale
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils import escaping
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.graph import cmk_graph_url

from .base import Perfometer


class PainterPerfometer(Painter):
    @property
    def ident(self) -> str:
        return "perfometer"

    def title(self, cell: Cell) -> str:
        return _("Service Perf-O-Meter")

    def short_title(self, cell: Cell) -> str:
        return _("Perf-O-Meter")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return [
            "service_staleness",
            "service_perf_data",
            "service_state",
            "service_check_command",
            "service_pnpgraph_present",
            "service_plugin_output",
        ]

    @property
    def printable(self) -> bool | str:
        return "perfometer"

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        classes = ["perfometer"]
        if is_stale(row, self.config.staleness_threshold):
            classes.append("stale")

        try:
            title, h = Perfometer(
                row,
                metrics_from_api,
                perfometers_from_api,
            ).render()
            if title is None and h is None:
                return "", ""
        except Exception as e:
            logger.exception("error rendering performeter")
            if self.config.debug:
                raise
            return " ".join(classes), _("Exception: %s") % e

        assert h is not None
        content = (
            HTMLWriter.render_div(h, class_=["content"])
            + HTMLWriter.render_div(title, class_=["title"])
            + HTMLWriter.render_div("", class_=["glass"])
        )

        # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
        if display_options.enabled(display_options.X) and row["service_pnpgraph_present"] != 0:
            url = cmk_graph_url(row, "service", request=self.request)
            disabled = False
        else:
            url = "javascript:void(0)"
            disabled = True

        renderer = RenderLink(self.request, response, display_options)
        return " ".join(classes), renderer.link_direct(
            url,
            html_text=content,
            title=escaping.strip_tags(title),
            class_=["disabled"] if disabled else [],
        )
