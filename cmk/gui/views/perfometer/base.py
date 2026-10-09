#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.gui.graphing import (
    drawn_segments,
    DrawnSegment,
    evaluated_perfometer,
    perfometer_label,
    perfometer_sort_value,
    PerfometerFromAPI,
    registered_translations,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.type_defs import Row
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.web.utils.html import HTML


class Perfometer:
    def __init__(
        self,
        row: Row,
        registered_metrics: Mapping[str, metrics_v1.Metric],
        registered_perfometers: Mapping[str, PerfometerFromAPI],
        *,
        debug: bool,
    ) -> None:
        self._evaluated = evaluated_perfometer(
            row["service_perf_data"],
            row["service_check_command"],
            host_name=row["host_name"],
            service_name=row["service_description"],
            registered_perfometers=registered_perfometers,
            registered_metrics=registered_metrics,
            registered_translations=registered_translations(),
            debug=debug,
        )

    def render(
        self, temperature_unit: TemperatureUnit, background_color: str
    ) -> tuple[str | None, HTML | None]:
        if self._evaluated is None:
            return None, None
        return (
            perfometer_label(self._evaluated, temperature_unit),
            _render_metricometer(drawn_segments(self._evaluated), background_color),
        )

    def sort_value(self) -> tuple[str, float]:
        if self._evaluated is None:
            return "", -float("inf")
        return self._evaluated.name, perfometer_sort_value(self._evaluated)


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


def _render_row(segments: Sequence[DrawnSegment], background_color: str) -> HTML:
    return render_perfometer(
        [
            (segment.share, background_color if segment.color is None else segment.color)
            for segment in segments
        ]
    )


def _render_metricometer(rows: Sequence[Sequence[DrawnSegment]], background_color: str) -> HTML:
    if len(rows) not in (1, 2):
        raise MKGeneralException(
            _("Invalid Perf-O-Meter definition %(stack)r: only one or two entries are allowed")
            % {"stack": rows}
        )
    h = HTML.empty().join(_render_row(row, background_color) for row in rows)
    if len(rows) == 2:
        h = HTMLWriter.render_div(h, class_="stacked")
    return h
