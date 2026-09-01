#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence

import pytest

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import perfometers, Title
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.graphing import perfometers_from_api
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import Cell
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.perfometer.base import Perfometer
from cmk.gui.views.perfometer.painter import PainterPerfometer

_REGISTERED_PERFOMETERS = {
    "kube_memory_usage": perfometers.Perfometer(
        name="kube_memory_usage",
        focus_range=perfometers.FocusRange(
            perfometers.Closed(0),
            perfometers.Open(1000000000),
        ),
        segments=["kube_memory_usage"],
    )
}


def _row(perf_data: str, check_command: str = "check_mk-kube_memory") -> Row:
    return {
        "host_name": "myhost",
        "service_description": "mysvc",
        "service_check_command": check_command,
        "service_perf_data": perf_data,
    }


@pytest.mark.parametrize(
    "sort_values",
    [
        [-1, 1, 0, None],
        [None, 0, 1, -1],
        [1, None, 0, -1],
    ],
)
def test_rows_sort_by_their_perfometer_with_the_undrawn_ones_first(
    sort_values: Sequence[float | None], request_context: None
) -> None:
    data = [
        _row(
            "kube_memory_request=209715200;;;0;"
            if v is None
            else f"kube_memory_usage={v};;;0; kube_memory_request=209715200;;;;"
        )
        for v in sort_values
    ]

    def _key(row: Row) -> tuple[str, float]:
        return Perfometer(row, {}, _REGISTERED_PERFOMETERS).sort_value()

    assert [_key(row)[1] for row in sorted(data, key=_key)] == [
        -float("inf"),
        -1.0,
        0.0,
        1.0,
    ]


def test_sort_value_groups_by_the_drawing_plugin(request_context: None) -> None:
    drawn = Perfometer(_row("kube_memory_usage=42;;;0;"), {}, _REGISTERED_PERFOMETERS)
    undrawn = Perfometer(_row("kube_memory_request=42;;;0;"), {}, _REGISTERED_PERFOMETERS)
    assert drawn.sort_value() == ("kube_memory_usage", 42.0)
    assert undrawn.sort_value() == ("", -float("inf"))


def test_a_segment_takes_the_attributes_of_its_registered_metric(request_context: None) -> None:
    metrics = {
        "kube_memory_usage": metrics_v1.Metric(
            name="kube_memory_usage",
            title=Title("Memory usage"),
            unit=metrics_v1.Unit(metrics_v1.IECNotation("B")),
            color=metrics_v1.Color.BLUE,
        )
    }
    title, html = Perfometer(
        _row("kube_memory_usage=209715200;;;0;"), metrics, _REGISTERED_PERFOMETERS
    ).render()
    assert title == "200 MiB"
    assert html is not None
    assert "background-color: #28a2f3" in str(html)


@pytest.fixture(name="registered_perfometer")
def fixture_registered_perfometer() -> Iterator[None]:
    perfometer = perfometers.Perfometer(
        name="export_perfometer",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["export_metric"],
    )
    perfometers_from_api.register(perfometer)
    try:
        yield
    finally:
        perfometers_from_api.unregister("export_perfometer")


def _perfometer_row() -> Row:
    return {
        "host_name": "myhost",
        "service_description": "mysvc",
        "service_staleness": 0.0,
        "service_perf_data": "export_metric=42;;;0;100",
        "service_state": 0,
        "service_check_command": "check_mk-export",
        "service_pnpgraph_present": 0,
        "service_plugin_output": "OK",
    }


def _make_painter() -> PainterPerfometer:
    return PainterPerfometer(
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
        user_permissions=UserPermissions({}, {}, {}, []),
    )


@pytest.mark.usefixtures("request_context", "registered_perfometer")
def test_perfometer_export_contains_label() -> None:
    """The Perf-O-Meter label must be present in CSV/JSON exports.

    During exports all display options are turned off, which suppresses the
    link wrapper produced by render(). The export methods must therefore fall
    back to the plain label instead of returning empty content (SUP-28751)."""
    painter = _make_painter()
    cell = Cell(None, None, None, UserPermissions({}, {}, {}, []))
    row = _perfometer_row()

    assert painter.export_for_csv(row, cell, user) == "42"
    assert painter.export_for_json(row, cell, user) == "42"
