#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Tuple

import cmk.gui.metrics as metrics
import cmk.gui.utils.escaping as escaping
from cmk.gui.globals import active_config, html
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.views.graphs import cmk_graph_url
from cmk.gui.plugins.views.perfometers.utils import perfometers, render_metricometer
from cmk.gui.plugins.views.utils import (
    Cell,
    CellSpec,
    display_options,
    is_stale,
    Painter,
    painter_registry,
    Row,
    Sorter,
    sorter_registry,
)
from cmk.gui.type_defs import Perfdata, PerfometerSpec, TranslatedMetrics


class Perfometer:
    def __init__(self, row: Row) -> None:
        self._row = row

        self._perf_data: Perfdata = []
        self._check_command: str = self._row["service_check_command"]
        self._translated_metrics: TranslatedMetrics = {}

        self._parse_perf_data()

    def _parse_perf_data(self) -> None:
        perf_data_string = self._row["service_perf_data"].strip()
        if not perf_data_string:
            return

        self._perf_data, self._check_command = metrics.parse_perf_data(
            perf_data_string, self._row["service_check_command"]
        )

        self._translated_metrics = metrics.translate_metrics(self._perf_data, self._check_command)

    def render(self) -> Tuple[Optional[str], Optional[HTML]]:
        """Renders the HTML code of a perfometer

        It returns a 2-tuple of either the title to show and the HTML of
        the perfometer or both elements set to None in case nothing shal
        be shown.
        """
        if not self._perf_data:
            return None, None

        # Try new metrics module
        title, h = self._render_metrics_perfometer()
        if title is not None:
            return title, h

        if not self._has_legacy_perfometer():
            return None, None

        # Legacy Perf-O-Meters: find matching Perf-O-Meter function
        logger.info(
            "Legacy perfometer rendered for %s / %s / %s",
            self._row["host_name"],
            self._row["service_description"],
            self._row["service_check_command"],
        )
        return self._render_legacy_perfometer()

    def _render_metrics_perfometer(self) -> Tuple[Optional[str], Optional[HTML]]:
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None, None

        renderer = metrics.renderer_registry.get_renderer(
            perfometer_definition, self._translated_metrics
        )
        return renderer.get_label(), render_metricometer(renderer.get_stack())

    def _render_legacy_perfometer(self) -> Tuple[Optional[str], Optional[HTML]]:
        perf_painter = perfometers[self._check_command]
        result = perf_painter(self._row, self._check_command, self._perf_data)
        if result is None:
            return None, None

        title, h = result
        if not h:
            return None, None

        return title, h

    def sort_value(self) -> Tuple[Optional[int], Optional[float]]:
        """Calculates a value that is used for sorting perfometers

        - First sort by the perfometer group / id
        - Second by the sort value calculated based on the perfometer type and
          the actual data
        """
        return self._get_sort_group(), self._get_sort_value()

    def _get_sort_group(self) -> Optional[int]:
        """First sort by the optional performeter group or the perfometer id. The perfometer
        group is used to group different perfometers in a single sort domain
        """
        sort_group = self._get_metrics_sort_group()

        if sort_group:
            return sort_group

        # TODO: Remove this legacy handling one day
        if not self._has_legacy_perfometer():
            return None

        # Fallback to legacy perfometer sorting. sort by the id() of the render function.
        # This should automatically group similar perfometers together.
        perf_painter_func = perfometers[self._check_command]
        return id(perf_painter_func)

    def _get_metrics_sort_group(self) -> Optional[int]:
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None

        # The perfometer definitions had no ID until implementation of this sorting. We need to
        # care about this here. Since it is only for grouping perfometers of the same type, we
        # can use the id() of the perfometer_definition here.
        return perfometer_definition.get("sort_group", id(perfometer_definition))

    def _get_sort_value(self) -> Optional[float]:
        """Calculate the sort value for this perfometer
        - The second sort criteria is a number that is calculated for each perfometer. The
          calculation of this number depends on the perfometer type:
          - Dual: sort by max(left, right). e.g. for traffic graphs it seems to be useful to
            make it sort by the maximum traffic independent of the direction.
          - Stacked: Use the number of the first stack element.
          - TODO: Make it possible to define a custom "sort_by" formula like it's done in other
            places of the metric system. Something like this: "sort_by": "user,system,+,idle,+,nice,+"
        """
        sort_value = self._get_metrics_sort_value()

        if sort_value is not None:
            return sort_value

        # TODO: Remove this legacy handling one day
        if not self._has_legacy_perfometer():
            return None

        # TODO: Fallback to legacy perfometer number calculation
        return None

    def _get_metrics_sort_value(self) -> Optional[float]:
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None

        renderer = metrics.renderer_registry.get_renderer(
            perfometer_definition, self._translated_metrics
        )
        return renderer.get_sort_value()

    def _get_perfometer_definition(
        self, translated_metrics: TranslatedMetrics
    ) -> Optional[PerfometerSpec]:
        """Returns the matching perfometer definition

        Uses the metrics of the current row to gather perfometers that can be
        rendered using these metrics. The first found perfometer definition
        is used.

        Returns None in case there is no matching definition found.
        """
        perfometer_definition = metrics.Perfometers().get_first_matching_perfometer(
            translated_metrics
        )
        if not perfometer_definition:
            return None

        return perfometer_definition

    def _has_legacy_perfometer(self) -> bool:
        return self._check_command in perfometers


# .
#   .--Painter-------------------------------------------------------------.
#   |                   ____       _       _                               |
#   |                  |  _ \ __ _(_)_ __ | |_ ___ _ __                    |
#   |                  | |_) / _` | | '_ \| __/ _ \ '__|                   |
#   |                  |  __/ (_| | | | | | ||  __/ |                      |
#   |                  |_|   \__,_|_|_| |_|\__\___|_|                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The perfometers are registered through a painter and sorter          |
#   '----------------------------------------------------------------------'


@painter_registry.register
class PainterPerfometer(Painter):
    @property
    def ident(self):
        return "perfometer"

    def title(self, cell):
        return _("Service Perf-O-Meter")

    def short_title(self, cell):
        return _("Perf-O-Meter")

    @property
    def columns(self):
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
            html.render_div(HTML(h), class_=["content"])
            + html.render_div(title, class_=["title"])
            + html.render_div("", class_=["glass"])
        )

        # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
        if display_options.enabled(display_options.X) and row["service_pnpgraph_present"] != 0:
            url = cmk_graph_url(row, "service")
            disabled = False
        else:
            url = "javascript:void(0)"
            disabled = True

        return " ".join(classes), html.render_a(
            content=content,
            href=url,
            title=escaping.strip_tags(title),
            class_=["disabled" if disabled else None],
        )


@sorter_registry.register
class SorterPerfometer(Sorter):
    @property
    def ident(self):
        return "perfometer"

    @property
    def title(self):
        return _("Perf-O-Meter")

    @property
    def columns(self):
        return [
            "service_perf_data",
            "service_state",
            "service_check_command",
            "service_pnpgraph_present",
            "service_plugin_output",
        ]

    def cmp(self, r1, r2):
        try:
            v1 = tuple(-float("inf") if s is None else s for s in Perfometer(r1).sort_value())
            v2 = tuple(-float("inf") if s is None else s for s in Perfometer(r2).sort_value())
            return (v1 > v2) - (v1 < v2)
        except Exception:
            logger.exception("error sorting perfometer values")
            if active_config.debug:
                raise
            return 0
