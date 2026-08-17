#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EngineeringScientificNotation,
    Graph,
    HostName,
    IECNotation,
    Line,
    MetricName,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceName,
    SINotation,
    Stack,
    StandardScientificNotation,
    TimeNotation,
    Unit,
)
from cmk.gui.graphing._engine_codec import community_graph_codec
from cmk.gui.graphing._engine_dispatch import serialize_graphs
from cmk.gui.graphing._frontend import (
    global_time_picker_props,
    resolve_default_time_range_seconds,
    to_cmk_time_series_graph,
)
from cmk.gui.type_defs import GraphTimerange
from cmk.gui.userdb.user_attributes import StartOfWeekUserAttribute
from cmk.gui.valuespec import DropdownChoice
from cmk.shared_typing.cmk_time_series_graph import GraphHeader, GraphOptions, Interaction, Size
from cmk.shared_typing.global_time_picker import CustomGraphTimeRange, FirstDayOfWeek

_Notation = (
    DecimalNotation
    | SINotation
    | IECNotation
    | StandardScientificNotation
    | EngineeringScientificNotation
    | TimeNotation
)

_UNIT = Unit(notation=DecimalNotation("X"), precision=AutoPrecision(2))
_RRD = RRDMetric(
    host_name=HostName("h"), service_name=ServiceName("s"), metric_name=MetricName("m")
)
_SIZE = Size(width=800.0, height=200.0, mode="resizable")


def test_to_cmk_time_series_graph_shell() -> None:
    # The shell carries only what is derivable from the (unevaluated) definition plus the render
    # options. The header title/name come from the engine ``Graph`` itself, not from an evaluation.
    graph = Graph(
        name="mygraph",
        title="My Graph",
        kind="template",
        stacks=[
            Stack(
                members=[
                    Curve(
                        quantity=_RRD, attributes=CurveAttributes(title="m", unit=_UNIT, color="#m")
                    )
                ],
                inverse=False,
            )
        ],
    )
    result = to_cmk_time_series_graph(graph, size=_SIZE)

    assert result.size == _SIZE
    assert result.options == GraphOptions(
        header=GraphHeader(title="My Graph", show_graph_time=True),
        name="mygraph",
        x_axis=None,
        y_axis=None,
        font_size_pt=8.0,
    )
    assert result.interaction == Interaction(
        burger="enabled",
        zoom="enabled",
        panning="enabled",
        hover="enabled",
        brush="enabled",
        pin="enabled",
    )
    # No evaluation happens here: the data (metrics/horizontal_lines) and the resampled range are
    # fetched separately, so the shell has a null time range.
    assert result.time_range is None
    # The internal field is the opaque JSON serialization of the graph definition envelope.
    assert result.internal == json.dumps(serialize_graphs([graph]))
    # A shell built without a specification offers no add-to action at all.
    assert result.add_to is None


_GRAPH_TIMERANGES: list[GraphTimerange] = [
    {"title": "Last 1 h", "duration": 3600},
    {"title": "Last 4 h", "duration": 14400},
]


def test_resolve_default_time_range_seconds_no_preference() -> None:
    assert resolve_default_time_range_seconds(_GRAPH_TIMERANGES, None) == 3600


def test_resolve_default_time_range_seconds_preference_honored() -> None:
    assert resolve_default_time_range_seconds(_GRAPH_TIMERANGES, 14400) == 14400


def test_resolve_default_time_range_seconds_stale_preference_falls_back() -> None:
    # e.g. an admin removed that time range from the global setting.
    assert resolve_default_time_range_seconds(_GRAPH_TIMERANGES, 90000) == 3600


def test_global_time_picker_props() -> None:
    props = global_time_picker_props(
        _GRAPH_TIMERANGES,
        14400,
        first_day_of_week=FirstDayOfWeek.monday,
        default_refresh_time=60,
    )
    assert props.custom_time_ranges == [
        CustomGraphTimeRange(title="Last 1 h", total_seconds=3600),
        CustomGraphTimeRange(title="Last 4 h", total_seconds=14400),
    ]
    assert props.default_time_range == 14400
    assert props.first_day_of_week is FirstDayOfWeek.monday
    assert props.default_refresh_time == 60


def test_global_time_picker_props_without_preferences() -> None:
    props = global_time_picker_props(
        _GRAPH_TIMERANGES, 3600, first_day_of_week=None, default_refresh_time=None
    )
    assert props.first_day_of_week is None
    assert props.default_refresh_time is None


def test_start_of_week_choices_match_first_day_of_week() -> None:
    # user_first_day_of_week falls back to the browser locale for values it does not know, so
    # drift between the two lists would silently disable the preference rather than fail.
    valuespec = StartOfWeekUserAttribute().valuespec()
    assert isinstance(valuespec, DropdownChoice)
    configurable_days = {value for value, _title in valuespec.choices() if value is not None}
    assert configurable_days == {day.value for day in FirstDayOfWeek}


def test_data_attribute_internal_round_trips_to_the_same_graph() -> None:
    graph = Graph(
        name="mygraph",
        title="My Graph",
        kind="template",
        stacks=[
            Stack(
                members=[
                    Curve(
                        quantity=_RRD, attributes=CurveAttributes(title="m", unit=_UNIT, color="#m")
                    )
                ],
                inverse=False,
            )
        ],
        lines=[
            Line(
                curve=Curve(
                    quantity=_RRD, attributes=CurveAttributes(title="l", unit=_UNIT, color="#l")
                ),
                inverse=False,
            )
        ],
        rules=[
            Rule(
                curve=Curve(
                    quantity=ScalarOf(metric=_RRD, scalar_kind=ScalarKind.WARNING),
                    attributes=CurveAttributes(title="warn", unit=_UNIT, color="#w"),
                ),
                inverse=False,
            )
        ],
    )
    result = to_cmk_time_series_graph(graph, size=_SIZE)

    assert result.options.header.title == "My Graph"
    [restored] = community_graph_codec().deserialize_graphs(json.loads(result.internal))
    assert restored == graph
