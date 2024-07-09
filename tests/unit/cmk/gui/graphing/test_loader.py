#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, Literal

import pytest

from cmk.gui.graphing._loader import load_graphing_plugins
from cmk.gui.graphing._utils import graph_info, metric_info

from cmk.discover_plugins import PluginLocation
from cmk.graphing.v1 import graphs, metrics, perfometers, translations


def test_load_graphing_plugins() -> None:
    discovered_graphing_plugins = load_graphing_plugins()
    assert not discovered_graphing_plugins.errors
    assert discovered_graphing_plugins.plugins


def test_metric_duplicates() -> None:
    assert metric_info
    metric_names = {
        p.name for p in load_graphing_plugins().plugins.values() if isinstance(p, metrics.Metric)
    }
    assert not set(metric_info).intersection(metric_names)


def test_graph_duplicates() -> None:
    assert graph_info
    graph_names = {
        p.name
        for p in load_graphing_plugins().plugins.values()
        if isinstance(p, (graphs.Graph, graphs.Bidirectional))
    }
    assert not set(graph_info).intersection(graph_names)


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


_SKIP_MODULES: Final[Sequence[str]] = [
    # Case 1: len(metric_names.bundles) > 1
    "cmk.plugins.aws.graphing.graphs",
    "cmk.plugins.aws.graphing.perfometers",
    "cmk.plugins.checkmk.graphing.cmk_site_statistics",
    "cmk.plugins.checkmk.graphing.livestatus_status",
    "cmk.plugins.checkmk.graphing.mkeventd_status",
    "cmk.plugins.collection.graphing.cpu_threads",
    "cmk.plugins.collection.graphing.diskstat",
    "cmk.plugins.collection.graphing.docker",
    "cmk.plugins.collection.graphing.emcvnx",
    "cmk.plugins.collection.graphing.environment",
    "cmk.plugins.collection.graphing.fc",
    "cmk.plugins.collection.graphing.fireeye",
    "cmk.plugins.collection.graphing.gpu",
    "cmk.plugins.collection.graphing.hop",
    "cmk.plugins.collection.graphing.ibm_mq",
    "cmk.plugins.collection.graphing.interfaces",
    "cmk.plugins.collection.graphing.kernel",
    "cmk.plugins.collection.graphing.kube",
    "cmk.plugins.collection.graphing.licenses",
    "cmk.plugins.collection.graphing.mail",
    "cmk.plugins.collection.graphing.mqtt",
    "cmk.plugins.collection.graphing.network",
    "cmk.plugins.collection.graphing.nimble",
    "cmk.plugins.collection.graphing.notifications_and_messages",
    "cmk.plugins.collection.graphing.printer",
    "cmk.plugins.collection.graphing.processes",
    "cmk.plugins.collection.graphing.varnish",
    "cmk.plugins.elasticsearch.graphing.elasticsearch",
    "cmk.plugins.gcp.graphing.gcp",
    "cmk.plugins.jenkins.graphing.jenkins",
    "cmk.plugins.memory.graphing.memory",
    "cmk.plugins.omd.graphing.omd_apache",
    "cmk.plugins.oracle.graphing.oracle",
    "cmk.plugins.robotmk.graphing.cee",
]


def test_bundles() -> None:
    for module, metric_names in _metric_names_by_module(load_graphing_plugins().plugins).items():
        if module in _SKIP_MODULES:
            continue
        assert len(metric_names.bundles) <= 1, (
            f"The module {module!r} defines multiple bundles. Our graphing modules are allowed to"
            " contain either standalone metric definitions or exactly one cohesive bundle of"
            " metric, perfometer or graph template definitions."
        )
        if metric_names.bundles:
            assert set(metric_names.from_metrics) == set(metric_names.bundles[0]), (
                f"The module {module!r} contains metric definitions which do not belong to a"
                " bundle. Our graphing modules are allowed to contain either standalone metric"
                " definitions or exactly one cohesive bundle of metric, perfometer or graph"
                " template definitions."
            )
