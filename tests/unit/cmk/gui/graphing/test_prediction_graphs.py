#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.graphing_engine import (
    ConsolidationFunction,
    Curve,
    Graph,
    HostName,
    MetricName,
    PredictionCurveKind,
    PredictionMetric,
    RRDMetric,
    ServiceName,
    SiteID,
)
from cmk.gui.graphing._drawn_curves import drawn_curves
from cmk.gui.graphing._graph_codec import community_graph_codec
from cmk.gui.graphing._prediction_graphs import (
    build_prediction_graph,
    PREDICTION_KIND,
    prediction_window_of,
    PredictionGraphContext,
)
from cmk.gui.graphing._prediction_source import Direction

_VALID_FROM = 1700000000
_VALID_UNTIL = _VALID_FROM + 86400


def _context(*directions: Direction) -> PredictionGraphContext:
    return PredictionGraphContext(
        site_id=SiteID("heute"),
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=MetricName("util"),
        period="wday",
        valid_from=_VALID_FROM,
        valid_until=_VALID_UNTIL,
        directions=directions,
    )


def _graph(*directions: Direction) -> Graph:
    return build_prediction_graph(_context(*directions), title="Prediction", metrics={})


def _region_bounds(
    graph: Graph,
) -> Sequence[tuple[PredictionCurveKind | None, PredictionCurveKind | None]]:
    bounds = []
    for region in graph.regions:
        bounds.append((_kind_of(region.lower), _kind_of(region.upper)))
    return bounds


def _kind_of(bound: Curve | None) -> PredictionCurveKind | None:
    if bound is None:
        return None
    assert isinstance(bound.quantity, PredictionMetric)
    return bound.quantity.curve_kind


def test_both_directions_shade_the_ok_zone_between_the_two_warning_levels() -> None:
    assert (
        PredictionCurveKind.LOWER_WARNING,
        PredictionCurveKind.UPPER_WARNING,
    ) in _region_bounds(_graph("upper", "lower"))


def test_the_critical_zone_above_is_open_at_the_top() -> None:
    assert (PredictionCurveKind.UPPER_CRITICAL, None) in _region_bounds(_graph("upper"))


def test_the_critical_zone_below_is_open_at_the_bottom() -> None:
    assert (None, PredictionCurveKind.LOWER_CRITICAL) in _region_bounds(_graph("lower"))


def test_without_lower_levels_the_ok_zone_is_open_at_the_bottom() -> None:
    assert (None, PredictionCurveKind.UPPER_WARNING) in _region_bounds(_graph("upper"))


def test_without_upper_levels_the_ok_zone_is_open_at_the_top() -> None:
    assert (PredictionCurveKind.LOWER_WARNING, None) in _region_bounds(_graph("lower"))


def test_a_single_direction_shades_the_ok_zone_and_one_warning_and_critical_zone() -> None:
    assert len(_graph("upper").regions) == 3


def test_the_prediction_is_drawn_once_even_when_both_directions_are_stored() -> None:
    references = [
        line
        for line in _graph("upper", "lower").lines
        if isinstance(line.curve.quantity, PredictionMetric)
        and line.curve.quantity.curve_kind
        in (PredictionCurveKind.UPPER_REFERENCE, PredictionCurveKind.LOWER_REFERENCE)
    ]

    assert len(references) == 1


def test_the_measurement_is_read_from_the_rrd_at_its_maximum() -> None:
    [observed] = [
        line.curve.quantity
        for line in _graph("upper").lines
        if isinstance(line.curve.quantity, RRDMetric)
    ]

    assert observed.consolidation_function is ConsolidationFunction.MAX


def test_every_drawn_curve_carries_the_unit_of_the_predicted_metric() -> None:
    graph = _graph("upper", "lower")

    units = {drawn.curve.attributes.unit for drawn in drawn_curves(graph.stacks, graph.lines)}

    assert len(units) == 1


def test_the_graph_is_drawn_over_the_interval_its_prediction_is_valid_for() -> None:
    window = prediction_window_of(_graph("upper"))

    assert window is not None
    assert (window.start, window.end) == (_VALID_FROM, _VALID_UNTIL)


def test_the_window_survives_the_trip_through_the_browser() -> None:
    codec = community_graph_codec()

    restored = codec.deserialize_graph(codec.serialize_graph(_graph("upper", "lower")))

    assert prediction_window_of(restored) == prediction_window_of(_graph("upper", "lower"))


def test_a_graph_without_a_prediction_has_no_window_of_its_own() -> None:
    assert prediction_window_of(Graph(name="n", title="t", kind=PREDICTION_KIND)) is None


@pytest.mark.parametrize("directions", [("upper",), ("lower",), ("upper", "lower")])
def test_a_zone_shades_the_graph_without_adding_a_curve_to_it(
    directions: Sequence[Direction],
) -> None:
    assert _graph(*directions).stacks == ()


def _line_titles(graph: Graph) -> Sequence[str]:
    return [line.curve.attributes.title for line in graph.lines]


def test_only_the_prediction_and_the_measurement_are_drawn_as_curves() -> None:
    assert _line_titles(_graph("upper", "lower")) == ["Prediction", "util"]


def test_no_level_is_drawn_even_when_both_directions_are_stored() -> None:
    drawn = [
        line.curve.quantity.curve_kind
        for line in _graph("upper", "lower").lines
        if isinstance(line.curve.quantity, PredictionMetric)
    ]

    assert drawn == [PredictionCurveKind.UPPER_REFERENCE]


def test_a_zone_is_named_so_the_legend_can_key_its_colour() -> None:
    titles = {region.attributes.title for region in _graph("upper", "lower").regions}

    assert titles == {
        "Critical area (upper)",
        "Warning area (upper)",
        "OK area",
        "Warning area (lower)",
        "Critical area (lower)",
    }


def test_a_single_direction_needs_no_upper_lower_qualifier() -> None:
    titles = {region.attributes.title for region in _graph("upper").regions}

    assert titles == {"Critical area", "Warning area", "OK area"}
