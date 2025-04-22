#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import pytest

from cmk.ccc.version import Edition, edition

from cmk.utils.paths import omd_root

from cmk.gui.graphing_main import _load_graphing_plugins

from cmk.discover_plugins import PluginLocation
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api
from cmk.graphing.v1 import translations as translations_api


def test_load_graphing_plugins() -> None:
    discovered_graphing_plugins = _load_graphing_plugins()
    assert not discovered_graphing_plugins.errors
    assert discovered_graphing_plugins.plugins


def test_translations_to_be_standalone() -> None:
    by_module: dict[str, Counter] = {}
    for plugin_location, plugin in _load_graphing_plugins().plugins.items():
        counter = by_module.setdefault(plugin_location.module, Counter())
        match plugin:
            case translations_api.Translation():
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
        | metrics_api.Constant
        | metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
        | metrics_api.Sum
        | metrics_api.Product
        | metrics_api.Difference
        | metrics_api.Fraction
    ),
) -> Iterator[str]:
    match quantity:
        case str():
            yield quantity
        case (
            metrics_api.WarningOf()
            | metrics_api.CriticalOf()
            | metrics_api.MinimumOf()
            | metrics_api.MaximumOf()
        ):
            yield quantity.metric_name
        case metrics_api.Sum():
            for summand in quantity.summands:
                yield from _collect_metric_names_from_quantity(summand)
        case metrics_api.Product():
            for factor in quantity.factors:
                yield from _collect_metric_names_from_quantity(factor)
        case metrics_api.Difference():
            yield from _collect_metric_names_from_quantity(quantity.minuend)
            yield from _collect_metric_names_from_quantity(quantity.subtrahend)
        case metrics_api.Fraction():
            yield from _collect_metric_names_from_quantity(quantity.dividend)
            yield from _collect_metric_names_from_quantity(quantity.divisor)


def _collect_metric_names_from_perfometer(
    perfometer: perfometers_api.Perfometer,
) -> Iterator[str]:
    if not isinstance(perfometer.focus_range.lower.value, int | float):
        yield from _collect_metric_names_from_quantity(perfometer.focus_range.lower.value)
    if not isinstance(perfometer.focus_range.upper.value, int | float):
        yield from _collect_metric_names_from_quantity(perfometer.focus_range.upper.value)
    for segment in perfometer.segments:
        yield from _collect_metric_names_from_quantity(segment)


def _collect_metric_names_from_graph(graph: graphs_api.Graph) -> Iterator[str]:
    if graph.minimal_range:
        if not isinstance(graph.minimal_range.lower, int | float):
            yield from _collect_metric_names_from_quantity(graph.minimal_range.lower)
        if not isinstance(graph.minimal_range.lower, int | float):
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
            metrics_api.Metric
            | perfometers_api.Perfometer
            | perfometers_api.Bidirectional
            | perfometers_api.Stacked
            | graphs_api.Graph
            | graphs_api.Bidirectional
            | translations_api.Translation
        ),
    ) -> None:
        match plugin:
            case metrics_api.Metric():
                self._from_metrics.add(plugin.name)
            case perfometers_api.Perfometer():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin)),
                )
            case perfometers_api.Bidirectional():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin.left)).union(
                        _collect_metric_names_from_perfometer(plugin.right)
                    ),
                )
            case perfometers_api.Stacked():
                self._from_perfometer_or_graph.setdefault(
                    ("perfometer", plugin.name),
                    set(_collect_metric_names_from_perfometer(plugin.lower)).union(
                        _collect_metric_names_from_perfometer(plugin.upper)
                    ),
                )
            case graphs_api.Graph():
                self._from_perfometer_or_graph.setdefault(
                    ("graph", plugin.name),
                    set(_collect_metric_names_from_graph(plugin)),
                )
            case graphs_api.Bidirectional():
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
        metrics_api.Metric
        | perfometers_api.Perfometer
        | perfometers_api.Bidirectional
        | perfometers_api.Stacked
        | graphs_api.Graph
        | graphs_api.Bidirectional
        | translations_api.Translation,
    ],
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
        for module, metric_names in _metric_names_by_module(
            _load_graphing_plugins().plugins
        ).items()
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


_ALLOWED_DUPLICATES = {
    "Active": {"docker_active", "mem_lnx_active"},
    "Active connections": {
        "active",
        "active_connections",
        "aws_active_connections",
        "fw_connections_active",
    },
    "Allocatable": {"kube_memory_allocatable", "kube_pod_allocatable", "kube_cpu_allocatable"},
    "Allocated space": {"mem_lnx_vmalloc_used", "allocated_size"},
    "Available capacity": {"emcvnx_avail_capacity", "capacity_perc"},
    "Average consumption": {"aws_dynamodb_consumed_wcu", "aws_dynamodb_consumed_rcu"},
    "Average usage": {"aws_dynamodb_consumed_rcu_perc", "aws_dynamodb_consumed_wcu_perc"},
    "Cluster utilization": {
        "kube_cpu_cluster_allocatable_utilization",
        "kube_memory_cluster_allocatable_utilization",
    },
    "Connection time": {"aws_route53_connection_time", "connection_time"},
    "Failed connections": {"connections_failed_rate", "failed_connections"},
    "Fan speed": {"fan_perc", "fan", "fan_speed"},
    "HTTP 500 errors": {"http_5xx", "aws_http_500_rate"},
    "Harddrive uncorrectable errors": {
        "harddrive_uncorrectable_erros",
        "harddrive_uncorrectable_errors",
    },
    "Limits": {"kube_cpu_limit", "kube_memory_limit"},
    "Limits utilization": {"kube_cpu_limit_utilization", "kube_memory_limit_utilization"},
    "Maximum single-request consumption": {
        "aws_dynamodb_maximum_consumed_wcu",
        "aws_dynamodb_maximum_consumed_rcu",
    },
    "Memory used": {"memused_couchbase_bucket", "memory_used"},
    "Minimum single-request consumption": {
        "aws_dynamodb_minimum_consumed_rcu",
        "aws_dynamodb_minimum_consumed_wcu",
    },
    "New connections": {"new_connections", "aws_new_connections"},
    "Node utilization": {
        "kube_cpu_node_allocatable_utilization",
        "kube_memory_node_allocatable_utilization",
    },
    "Nodes": {"number_of_nodes", "aws_elasticache_nodes"},
    "Non-compliant devices": {"mobileiron_non_compliant", "mobileiron_non_compliant_summary"},
    "Power Usage": {"power_usage", "power_usage_percentage"},
    "Pressure": {"pressure_pa", "pressure"},
    "Queue length": {"queue", "queue_length"},
    "Read latency": {"db_read_latency_s", "read_latency"},
    "Read operations": {"disk_read_ios", "read_ops"},
    "Requests": {"kube_memory_request", "kube_cpu_request", "aws_cloudfront_requests"},
    "Requests per second": {"requests", "requests_per_sec", "requests_per_second"},
    "Requests utilization": {"kube_memory_request_utilization", "kube_cpu_request_utilization"},
    "Reserved space": {"reserved_size", "reserved"},
    "Running containers": {"docker_running_containers", "kube_node_container_count_running"},
    "Shared memory": {"mem_esx_shared", "mem_lnx_shmem"},
    "Smoke": {"smoke_perc", "smoke_ppm"},
    "Storage space used": {"storage_used", "storage_percent"},
    "Streams": {"streams", "num_streams"},
    "Swap used": {"swap_used", "swap_used_percent"},
    "System": {"system", "system_size"},
    "Total devices": {"ap_devices_total", "mobileiron_devices_total"},
    "Total size": {"fs_size", "elasticsearch_size"},
    "Total virtual memory": {"mem_lnx_total_total", "mem_total_virtual_in_bytes"},
    "Usage": {"kube_cpu_usage", "pd_exclusivesnapshot", "kube_memory_usage"},
    "Used licenses": {"licenses", "license_percentage"},
    "Used virtual memory": {"pagefile_used_percent", "pagefile_used"},
    "Used virtual memory (averaged)": {"pagefile_used_percent_avg", "pagefile_used_avg"},
    "User": {"user", "num_user"},
    "Utilization": {"cisco_sma_queue_utilization", "generic_util"},
    "Write latency": {"write_latency", "db_write_latency_s"},
    "Write operations": {"write_ops_s", "disk_write_ios"},
}


def test_duplicate_metric_titles() -> None:
    metric_names_by_title: dict[str, set[str]] = {}
    for plugin in _load_graphing_plugins().plugins.values():
        if isinstance(plugin, metrics_api.Metric):
            metric_names_by_title.setdefault(plugin.title.localize(str), set()).add(plugin.name)

    duplicates = {t: mns for t, mns in metric_names_by_title.items() if len(mns) > 1}

    new = {t: mns for t, mns in duplicates.items() if t not in _ALLOWED_DUPLICATES}
    assert not new, "Found new duplicates:\n" + "\n".join(
        [f"- {t}: {', '.join(mns)}" for t, mns in new.items()]
    )

    already_fixed = {t: mns for t, mns in _ALLOWED_DUPLICATES.items() if t not in duplicates}
    assert not already_fixed, "Found already fixed duplicates:\n" + "\n".join(
        [f"- {t}: {', '.join(mns)}" for t, mns in already_fixed.items()]
    )
