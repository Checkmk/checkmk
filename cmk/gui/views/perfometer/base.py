#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.graphing import get_first_matching_perfometer
from cmk.gui.graphing._from_api import metrics_from_api
from cmk.gui.graphing._translated_metrics import (
    parse_perf_data,
    translate_metrics,
    TranslatedMetric,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.type_defs import Perfdata, Row
from cmk.gui.utils.html import HTML

from ...config import active_config


class Perfometer:
    def __init__(self, row: Row) -> None:
        self._row = row

        self._perf_data: Perfdata = []
        self._check_command: str = self._row["service_check_command"]
        self._translated_metrics: Mapping[str, TranslatedMetric] = {}

        self._parse_perf_data()

    def _parse_perf_data(self) -> None:
        perf_data_string = self._row["service_perf_data"].strip()
        if not perf_data_string:
            return

        self._perf_data, self._check_command = parse_perf_data(
            perf_data_string, self._row["service_check_command"], config=active_config
        )

        self._translated_metrics = translate_metrics(
            self._perf_data,
            self._check_command,
            metrics_from_api,
        )

    def render(self) -> tuple[str | None, HTML | None]:
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

        return None, None

    def _render_metrics_perfometer(self) -> tuple[str | None, HTML | None]:
        if not (renderer := get_first_matching_perfometer(self._translated_metrics)):
            return None, None
        return renderer.get_label(), _render_metricometer(renderer.get_stack())

    def sort_value(self) -> tuple[int | None, float | None]:
        """Calculates a value that is used for sorting perfometers

        - First sort by the perfometer group / id
        - Second by the sort value calculated based on the perfometer type and
          the actual data
        """
        return self._get_metrics_sort_group(), self._get_metrics_sort_value()

    def _get_metrics_sort_group(self) -> int | None:
        if not (renderer := get_first_matching_perfometer(self._translated_metrics)):
            return None
        # The perfometer definitions had no ID until implementation of this sorting. We need to
        # care about this here. Since it is only for grouping perfometers of the same type, we
        # can use the id() of the perfometer_definition here.
        return id(renderer.perfometer)

    def _get_metrics_sort_value(self) -> float | None:
        if not (renderer := get_first_matching_perfometer(self._translated_metrics)):
            return None
        return renderer.get_sort_value()


def render_perfometer(data: Sequence[tuple[float, str]]) -> HTML:
    tds = HTML.empty().join(_render_perfometer_td(percentage, color) for percentage, color in data)
    return HTMLWriter.render_table(HTMLWriter.render_tr(tds))


def _render_perfometer_td(perc: float, color: str) -> HTML:
    # the hex color can have additional information about opacity
    # internet explorer has problems with the format of rgba, e.g.: #aaaaaa4d
    # the solution is to set the background-color value to rgb ('#aaaaaa')
    # and use the css opacity for the opacity hex value in float '4d' -> 0.3
    opacity = None
    if len(color) == 9:
        opacity = int(color[7:], 16) / 255.0
        color = color[:7]

    style = ["width: %d%%;" % int(float(perc)), "background-color: %s" % color]
    if opacity is not None:
        style += ["opacity: %s" % opacity]
    return HTMLWriter.render_td("", class_="inner", style=style)


def _render_metricometer(stack: Sequence[Sequence[tuple[int | float, str]]]) -> HTML:
    """Create HTML representation of Perf-O-Meter"""
    if len(stack) not in (1, 2):
        raise MKGeneralException(
            _("Invalid Perf-O-Meter definition %r: only one or two entries are allowed") % stack
        )
    h = HTML.empty().join(map(render_perfometer, stack))
    if len(stack) == 2:
        h = HTMLWriter.render_div(h, class_="stacked")
    return h
