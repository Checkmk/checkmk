#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import cmk.gui.utils.escaping as escaping
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.utils.html import HTML
from cmk.gui.views.graph import cmk_graph_url

from ..painter.v0.base import Cell, CellSpec, Painter
from ..painter.v1.helpers import is_stale
from .base import Perfometer


class PainterPerfometer(Painter):
    @property
    def ident(self) -> str:
        return "perfometer"

    def title(self, cell):
        return _("Service Perf-O-Meter")

    def short_title(self, cell):
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
    def printable(self):
        return "perfometer"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        classes = ["perfometer"]
        if is_stale(row):
            classes.append("stale")

        try:
            title, h = Perfometer(row).render()
            if title is None and h is None:
                return "", ""
        except Exception as e:
            logger.exception("error rendering performeter")
            if active_config.debug:
                raise
            return " ".join(classes), _("Exception: %s") % e

        assert h is not None
        content = (
            HTMLWriter.render_div(HTML(h), class_=["content"])
            + HTMLWriter.render_div(title, class_=["title"])
            + HTMLWriter.render_div("", class_=["glass"])
        )

        # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
        if display_options.enabled(display_options.X) and row["service_pnpgraph_present"] != 0:
            url = cmk_graph_url(row, "service")
            disabled = False
        else:
            url = "javascript:void(0)"
            disabled = True

        return " ".join(classes), HTMLWriter.render_a(
            content=content,
            href=url,
            title=escaping.strip_tags(title),
            class_=["disabled"] if disabled else [],
        )
