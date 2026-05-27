#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
from collections.abc import Iterator, Sequence

import pytest

from cmk.graphing.v1 import metrics, perfometers, Title
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.graphing import metrics_from_api, perfometers_from_api
from cmk.gui.graphing._from_api import parse_metric_from_api
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
from cmk.gui.views.perfometer.sorter import _SorterPerfometer

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


@pytest.mark.parametrize(
    "sort_values",
    [
        [-1, 1, 0, None],
        [None, 0, 1, -1],
        [1, None, 0, -1],
    ],
)
def test_cmp_of_missing_values(sort_values: Sequence[float | None], request_context: None) -> None:
    """If perfometer values are missing, sort_value() of Perfometer will return (None, None).
    The sorting chosen below is consistent with how _data_sort from cmk.gui.views.__init__.py
    treats missing values."""
    data = [
        {
            "service_check_command": "check_mk-kube_memory",
            "service_perf_data": (
                "kube_memory_request=209715200;;;0;"
                if v is None
                else f"kube_memory_usage={v};;;0; kube_memory_request=209715200;;;;"
            ),
        }
        for v in sort_values
    ]

    def wrapped(r1: Row, r2: Row) -> int:
        return _SorterPerfometer({}, _REGISTERED_PERFOMETERS).cmp(
            r1, r2, parameters=None, config=active_config, request=request
        )

    data.sort(key=functools.cmp_to_key(wrapped))
    assert [Perfometer(r, {}, _REGISTERED_PERFOMETERS).sort_value()[1] for r in data] == [
        None,
        -1.0,
        0.0,
        1.0,
    ]


@pytest.fixture(name="registered_perfometer")
def fixture_registered_perfometer() -> Iterator[None]:
    """Register a metric + perfometer so the painter produces a label."""
    metric = parse_metric_from_api(
        metrics.Metric(
            name="export_metric",
            title=Title("Export metric"),
            unit=metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(0)),
            color=metrics.Color.BLUE,
        )
    )
    perfometer = perfometers.Perfometer(
        name="export_perfometer",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["export_metric"],
    )
    metrics_from_api.register(metric)
    perfometers_from_api.register(perfometer)
    try:
        yield
    finally:
        metrics_from_api.unregister("export_metric")
        perfometers_from_api.unregister("export_perfometer")


def _perfometer_row() -> Row:
    return {
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


@pytest.mark.usefixtures("request_context", "patch_theme", "registered_perfometer")
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
