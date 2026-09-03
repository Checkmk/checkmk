#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

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
    derive_y_axis,
    global_time_picker_props,
    global_time_picker_refresh,
    resolve_default_time_range_seconds,
    stored_time_range_seconds,
    to_cmk_time_series_graph,
    user_first_day_of_week,
)
from cmk.gui.type_defs import GraphTimerange, PainterParameters
from cmk.gui.userdb.user_attributes import StartOfWeekUserAttribute
from cmk.gui.valuespec import DropdownChoice
from cmk.shared_typing.cmk_time_series_graph import (
    GraphHeader,
    GraphOptions,
    Interaction,
    Precision,
    Size,
    UnitFormat,
    YAxis,
)
from cmk.shared_typing.global_time_picker import (
    CustomGraphTimeRange,
    FirstDayOfWeek,
    GlobalTimePickerRefresh,
)

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
        y_axis=YAxis(
            unit=UnitFormat(
                notation="decimal", symbol="X", precision=Precision(type="auto", digits=2)
            ),
        ),
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


def test_stored_time_range_seconds_is_the_views_own_setting() -> None:
    assert (
        stored_time_range_seconds(
            painter_parameters=PainterParameters(set_default_time_range=14400),
            stored_by_the_view=True,
        )
        == 14400
    )


def test_stored_time_range_seconds_ignores_the_valuespec_default() -> None:
    # What a painter with nothing stored reports: the valuespec default carries the key.
    assert (
        stored_time_range_seconds(
            painter_parameters=PainterParameters(set_default_time_range=14400),
            stored_by_the_view=False,
        )
        is None
    )


def test_stored_time_range_seconds_without_the_setting() -> None:
    assert (
        stored_time_range_seconds(
            painter_parameters=PainterParameters(graph_render_options={}),
            stored_by_the_view=True,
        )
        is None
    )


def test_stored_time_range_seconds_for_a_painter_without_parameters() -> None:
    assert stored_time_range_seconds(painter_parameters=None, stored_by_the_view=True) is None


def test_global_time_picker_props() -> None:
    refresh = GlobalTimePickerRefresh(
        interval_seconds=60, starts_live=True, reloads_page_content=True
    )

    props = global_time_picker_props(
        _GRAPH_TIMERANGES,
        14400,
        first_day_of_week=FirstDayOfWeek.monday,
        refresh=refresh,
    )

    assert props.custom_time_ranges == [
        CustomGraphTimeRange(title="Last 1 h", total_seconds=3600),
        CustomGraphTimeRange(title="Last 4 h", total_seconds=14400),
    ]
    assert props.default_time_range == 14400
    assert props.first_day_of_week is FirstDayOfWeek.monday
    assert props.refresh is refresh


def test_global_time_picker_props_without_preferences() -> None:
    props = global_time_picker_props(
        _GRAPH_TIMERANGES,
        3600,
        first_day_of_week=None,
        refresh=GlobalTimePickerRefresh(
            interval_seconds=None, starts_live=False, reloads_page_content=False
        ),
    )

    assert props.first_day_of_week is None


def test_global_time_picker_refresh_leaves_a_page_paused_and_self_contained(
    request_context: None,
) -> None:
    refresh = global_time_picker_refresh()

    assert refresh.starts_live is False
    assert refresh.reloads_page_content is False


def test_global_time_picker_refresh_falls_back_to_the_user_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferred_interval = 90
    monkeypatch.setattr(
        "cmk.gui.graphing._frontend.user_default_refresh_time", lambda: preferred_interval
    )

    refresh = global_time_picker_refresh()

    assert refresh.interval_seconds == preferred_interval


def test_global_time_picker_refresh_prefers_the_interval_of_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cmk.gui.graphing._frontend.user_default_refresh_time", lambda: 90)
    interval_of_the_page = 60

    refresh = global_time_picker_refresh(interval_seconds=interval_of_the_page)

    assert refresh.interval_seconds == interval_of_the_page


class _UserStub:
    """Stands in for the `user` proxy, which resolves only inside a session."""

    def __init__(self, attribute: object) -> None:
        self._attribute = attribute

    def get_attribute(self, key: str, deflt: object = None) -> object:
        return self._attribute


@pytest.mark.parametrize(
    "stored, expected",
    [
        (None, FirstDayOfWeek.monday),
        ("browser_locale", None),
        ("sunday", FirstDayOfWeek.sunday),
        ("funday", FirstDayOfWeek.monday),
    ],
)
def test_user_first_day_of_week(
    monkeypatch: pytest.MonkeyPatch, stored: str | None, expected: FirstDayOfWeek | None
) -> None:
    monkeypatch.setattr("cmk.gui.graphing._frontend.user", _UserStub(stored))
    assert user_first_day_of_week() is expected


def test_start_of_week_choices_are_all_honored(monkeypatch: pytest.MonkeyPatch) -> None:
    # Drift between the choices and the wire enum would silently ignore a preference.
    valuespec = StartOfWeekUserAttribute().valuespec()
    assert isinstance(valuespec, DropdownChoice)
    resolved = set()
    for value, _title in valuespec.choices():
        monkeypatch.setattr("cmk.gui.graphing._frontend.user", _UserStub(value))
        resolved.add(user_first_day_of_week())
    assert resolved == {None, *FirstDayOfWeek}


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


def test_derive_y_axis_takes_the_unit_of_the_first_stack_member() -> None:
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
    assert derive_y_axis(graph) == YAxis(
        unit=UnitFormat(notation="decimal", symbol="X", precision=Precision(type="auto", digits=2)),
    )


def test_derive_y_axis_falls_back_to_a_line_when_there_are_no_stacks() -> None:
    graph = Graph(
        name="mygraph",
        title="My Graph",
        kind="template",
        lines=[
            Line(
                curve=Curve(
                    quantity=_RRD, attributes=CurveAttributes(title="l", unit=_UNIT, color="#l")
                ),
                inverse=False,
            )
        ],
    )
    y_axis = derive_y_axis(graph)
    assert y_axis is not None
    assert y_axis.unit is not None
    assert y_axis.unit.symbol == "X"


def test_derive_y_axis_is_none_for_a_graph_with_no_curves() -> None:
    graph = Graph(name="mygraph", title="Empty", kind="template")
    assert derive_y_axis(graph) is None
