#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import pytest

from cmk.utils.paths import omd_root

from cmk.gui.config import active_config
from cmk.gui.graphing import perfometer_info
from cmk.gui.graphing._loader import (
    _compute_unit_info,
    _TemperatureUnitConverter,
    load_graphing_plugins,
)
from cmk.gui.graphing._unit_info import unit_info, UnitInfo
from cmk.gui.graphing._utils import graph_info, metric_info
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.temperate_unit import TemperatureUnit

from cmk.ccc.version import Edition, edition
from cmk.discover_plugins import PluginLocation
from cmk.graphing.v1 import graphs, metrics, perfometers, translations


def test_load_graphing_plugins() -> None:
    discovered_graphing_plugins = load_graphing_plugins()
    assert not discovered_graphing_plugins.errors
    assert discovered_graphing_plugins.plugins


def test_metric_duplicates() -> None:
    assert metric_info == {
        "temp": {
            "title": "Temperature",
            "unit": "c",
            "color": "16/a",
        }
    }
    assert "c" in list(unit_info.keys())
    metric_names = {
        p.name for p in load_graphing_plugins().plugins.values() if isinstance(p, metrics.Metric)
    }
    assert not set(metric_info).intersection(metric_names)


def test_perfometers() -> None:
    assert perfometer_info == [
        {"type": "logarithmic", "metric": "temp", "half_value": 40.0, "exponent": 1.2}
    ]


def test_graph_duplicates() -> None:
    assert graph_info == {
        "temperature": {
            "title": "Temperature",
            "metrics": [("temp", "area")],
            "scalars": ["temp:warn", "temp:crit"],
        }
    }
    graph_names = {
        p.name
        for p in load_graphing_plugins().plugins.values()
        if isinstance(p, (graphs.Graph, graphs.Bidirectional))
    }
    assert not set(graph_info).intersection(graph_names)


def test_translations_to_be_standalone() -> None:
    by_module: dict[str, Counter] = {}
    for plugin_location, plugin in load_graphing_plugins().plugins.items():
        counter = by_module.setdefault(plugin_location.module, Counter())
        match plugin:
            case translations.Translation():
                counter.update(["translations"])
            case _:
                counter.update(["others"])
    for module, counter in by_module.items():
        if counter["translations"]:
            assert not counter["rest"], (
                f"The module {module!r} contains translations and other graphing plugins. Our"
                " graphing modules are allowed to contain either translations or other plugins."
            )
        if counter["rest"]:
            assert not counter["translations"], (
                f"The module {module!r} contains translations and other graphing plugins. Our"
                " graphing modules are allowed to contain either translations or other plugins."
            )


def _collect_metric_names_from_quantity(
    quantity: (
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ),
) -> Iterator[str]:
    match quantity:
        case str():
            yield quantity
        case metrics.WarningOf() | metrics.CriticalOf() | metrics.MinimumOf() | metrics.MaximumOf():
            yield quantity.metric_name
        case metrics.Sum():
            for summand in quantity.summands:
                yield from _collect_metric_names_from_quantity(summand)
        case metrics.Product():
            for factor in quantity.factors:
                yield from _collect_metric_names_from_quantity(factor)
        case metrics.Difference():
            yield from _collect_metric_names_from_quantity(quantity.minuend)
            yield from _collect_metric_names_from_quantity(quantity.subtrahend)
        case metrics.Fraction():
            yield from _collect_metric_names_from_quantity(quantity.dividend)
            yield from _collect_metric_names_from_quantity(quantity.divisor)


def _collect_metric_names_from_perfometer(
    perfometer: perfometers.Perfometer,
) -> Iterator[str]:
    if not isinstance(perfometer.focus_range.lower.value, (int, float)):
        yield from _collect_metric_names_from_quantity(perfometer.focus_range.lower.value)
    if not isinstance(perfometer.focus_range.upper.value, (int, float)):
        yield from _collect_metric_names_from_quantity(perfometer.focus_range.upper.value)
    for segment in perfometer.segments:
        yield from _collect_metric_names_from_quantity(segment)


def _collect_metric_names_from_graph(graph: graphs.Graph) -> Iterator[str]:
    if graph.minimal_range:
        if not isinstance(graph.minimal_range.lower, (int, float)):
            yield from _collect_metric_names_from_quantity(graph.minimal_range.lower)
        if not isinstance(graph.minimal_range.lower, (int, float)):
            yield from _collect_metric_names_from_quantity(graph.minimal_range.lower)
    for compound_line in graph.compound_lines:
        yield from _collect_metric_names_from_quantity(compound_line)
    for simple_line in graph.simple_lines:
        yield from _collect_metric_names_from_quantity(simple_line)
    yield from graph.optional
    yield from graph.conflicting


@dataclass(frozen=True)
class _MetricNamesInModule:
    _from_metrics: set[str] = field(default_factory=set)
    _from_perfometer_or_graph: dict[tuple[Literal["perfometer", "graph"], str], set[str]] = field(
        default_factory=dict
    )

    @property
    def from_metrics(self) -> Sequence[str]:
        return list(self._from_metrics)

    @property
    def bundles(self) -> Sequence[tuple[str, ...]]:
        bundles: set[tuple[str, ...]] = set()
        for left_ident, left_metric_names in self._from_perfometer_or_graph.items():
            bundle_ = left_metric_names
            for right_ident, right_metric_names in self._from_perfometer_or_graph.items():
                if left_ident == right_ident:
                    continue
                if left_metric_names.intersection(right_metric_names):
                    bundle_.update(right_metric_names)
            bundles.add(tuple(sorted(bundle_)))
        # remove subsets
        result: set[tuple[str, ...]] = set()
        for bundle in sorted(bundles, key=len, reverse=True):
            if any(set(bundle).issubset(r) for r in result):
                continue
            result.add(bundle)
        return list(result)

    def add_from_plugin(
        self,
        plugin: (
            metrics.Metric
            | translations.Translation
            | perfometers.Perfometer
            | perfometers.Bidirectional
            | perfometers.Stacked
            | graphs.Graph
            | graphs.Bidirectional
        ),
    ) -> None:
        match plugin:
            case metrics.Metric():
                self._from_metrics.add(plugin.name)
            case perfometers.Perfometer():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin)),
                )
            case perfometers.Bidirectional():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin.left)).union(
                        _collect_metric_names_from_perfometer(plugin.right)
                    ),
                )
            case perfometers.Stacked():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin.lower)).union(
                        _collect_metric_names_from_perfometer(plugin.upper)
                    ),
                )
            case graphs.Graph():
                self._from_perfometer_or_graph.setdefault(
                    ("graph", plugin.name),
                    set(_collect_metric_names_from_graph(plugin)),
                )
            case graphs.Bidirectional():
                self._from_perfometer_or_graph.setdefault(
                    ("graph", plugin.name),
                    set(_collect_metric_names_from_graph(plugin.lower)).union(
                        _collect_metric_names_from_graph(plugin.upper)
                    ),
                )


@pytest.mark.parametrize(
    "from_plugins, expected_bundles",
    [
        pytest.param({}, [], id="empty"),
        pytest.param(
            {(0, "perfometer", "name"): ["b", "a"]},
            [("a", "b")],
            id="one-perfometer",
        ),
        pytest.param(
            {("graph", "name"): ["b", "a"]},
            [("a", "b")],
            id="one-graph",
        ),
        pytest.param(
            {
                ("perfometer", "name"): ["b", "a"],
                ("graph", "name"): ["d", "c"],
            },
            [("a", "b"), ("c", "d")],
            id="no-intersection",
        ),
        pytest.param(
            {
                ("perfometer", "name"): ["b", "a"],
                ("graph", "name"): ["c", "b"],
            },
            [("a", "b", "c")],
            id="intersection-1",
        ),
        pytest.param(
            {
                ("perfometer", "name"): ["b", "a"],
                ("graph", "name1"): ["d", "c"],
                ("graph", "name2"): ["b", "d"],
            },
            [("a", "b", "c", "d")],
            id="intersection-via-third",
        ),
        pytest.param(
            {
                ("perfometer", "name1"): ["b", "a"],
                ("graph", "name1"): ["c", "b"],
                ("perfometer", "name2"): ["e", "d"],
                ("graph", "name2"): ["f", "e"],
            },
            [("a", "b", "c"), ("d", "e", "f")],
            id="two-bundles",
        ),
        pytest.param(
            {
                ("perfometer", "name1"): ["b", "a"],
                ("graph", "name1"): ["c", "b"],
                ("perfometer", "name2"): ["e", "d"],
                ("graph", "name2"): ["f", "e"],
                ("graph", "name3"): ["f", "c"],
            },
            [("a", "b", "c", "d", "e", "f")],
            id="two-bundles-intersection-via-third",
        ),
    ],
)
def test__MetricNamesInModule_bundles(
    from_plugins: Mapping[tuple[Literal["perfometer", "graph"], str], Sequence[str]],
    expected_bundles: Sequence[tuple[str, ...]],
) -> None:
    metric_names = _MetricNamesInModule(set(), {i: set(m) for i, m in from_plugins.items()})
    assert sorted(metric_names.bundles) == expected_bundles


def _metric_names_by_module(
    plugins: Mapping[
        PluginLocation,
        metrics.Metric
        | translations.Translation
        | perfometers.Perfometer
        | perfometers.Bidirectional
        | perfometers.Stacked
        | graphs.Graph
        | graphs.Bidirectional,
    ]
) -> Mapping[str, _MetricNamesInModule]:
    metric_names_by_module: dict[str, _MetricNamesInModule] = {}
    for plugin_location, plugin in plugins.items():
        metric_names_by_module.setdefault(
            plugin_location.module, _MetricNamesInModule()
        ).add_from_plugin(plugin)
    return metric_names_by_module


def test_bundles() -> None:
    offenders = [
        (module, metric_names)
        for module, metric_names in _metric_names_by_module(load_graphing_plugins().plugins).items()
        if (bundles := metric_names.bundles)
        and (len(bundles) > 1 or set(metric_names.from_metrics) != set(bundles[0]))
    ]

    for module, metric_names in (
        (module, metric_names)
        for module, metric_names in offenders
        if module not in _ALLOWED_BUNDLE_VIOLATIONS
    ):
        assert len(bundles) <= 1, (
            f"The module {module} defines multiple bundles. Our graphing modules are allowed to"
            " contain either standalone metric definitions or exactly one cohesive bundle of"
            " metric, perfometer or graph template definitions."
        )
        raise AssertionError(
            f"The module {module} contains metric definitions which do not belong to a"
            " bundle. Our graphing modules are allowed to contain either standalone metric"
            " definitions or exactly one cohesive bundle of metric, perfometer or graph"
            " template definitions."
        )

    allowed_but_not_offending_modules = _ALLOWED_BUNDLE_VIOLATIONS - {
        module for module, _ in offenders
    }
    assert not allowed_but_not_offending_modules, (
        "The followin modules are allowed to violate our graphing module but they don't so so:\n"
        f"{', '.join(sorted(allowed_but_not_offending_modules))}\n"
        "Please remove them from the list of allowed violations."
    )


_ALLOWED_BUNDLE_VIOLATIONS = (
    set()
    if edition(omd_root) is Edition.CRE
    else {
        # we cannot have sub-modules below the cee folder, so we have to allow the following violations
        # in cmk.cee.robotmk, the module layout of the metric etc. defintions is correct
        "cmk.plugins.robotmk.graphing.cee",
    }
)


@pytest.mark.parametrize(
    "unit_info_, unit, expected_value",
    [
        pytest.param(
            UnitInfo(
                id="DecimalNotation_foo_AutoPrecision_2",
                title="Title",
                symbol="foo",
                render=lambda v: f"{v} foo",
                js_render="v => v",
                conversion=lambda v: v,
            ),
            TemperatureUnit.CELSIUS,
            "123.456 foo",
            id="no-converter",
        ),
        pytest.param(
            UnitInfo(
                id="DecimalNotation_°C_AutoPrecision_2",
                title="Title",
                symbol="°C",
                render=lambda v: f"{v} °C",
                js_render="v => v",
                conversion=lambda v: v,
            ),
            TemperatureUnit.CELSIUS,
            "123.456 °C",
            id="temp-celsius-celius",
        ),
        pytest.param(
            UnitInfo(
                id="DecimalNotation_°C_AutoPrecision_2",
                title="Title",
                symbol="°C",
                render=lambda v: f"{v} °C",
                js_render="v => v",
                conversion=lambda v: v,
            ),
            TemperatureUnit.FAHRENHEIT,
            "254.22 °F",
            id="temp-celsius-fahrenheit",
        ),
        pytest.param(
            UnitInfo(
                id="DecimalNotation_°F_AutoPrecision_2",
                title="Title",
                symbol="°F",
                render=lambda v: f"{v} °F",
                js_render="v => v",
                conversion=lambda v: v,
            ),
            TemperatureUnit.CELSIUS,
            "50.81 °C",
            id="temp-fahrenheit-celius",
        ),
        pytest.param(
            UnitInfo(
                id="DecimalNotation_°F_AutoPrecision_2",
                title="Title",
                symbol="°F",
                render=lambda v: f"{v} °F",
                js_render="v => v",
                conversion=lambda v: v,
            ),
            TemperatureUnit.FAHRENHEIT,
            "123.456 °F",
            id="temp-fahrenheit-fahrenheit",
        ),
    ],
)
def test__compute_unit_info(
    unit_info_: UnitInfo,
    unit: TemperatureUnit,
    expected_value: str,
    request_context: None,
) -> None:
    active_config.default_temperature_unit = unit.value
    unit_info_ = _compute_unit_info(
        unit_info_.id,
        unit_info_,
        active_config,
        LoggedInUser(None),
        [_TemperatureUnitConverter],
    )
    assert unit_info_.render(unit_info_.conversion(123.456)) == expected_value
