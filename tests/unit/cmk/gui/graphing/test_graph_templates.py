#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import graphs, metrics, Title
from cmk.graphing.v1 import graphs as graphs_api
from cmk.graphing.v1 import metrics as metrics_api
from cmk.gui.graphing._from_api import RegisteredMetric
from cmk.gui.graphing._graph_metric_expressions import GraphMetricRRDSource
from cmk.gui.graphing._graph_specification import (
    GraphMetric,
    GraphRecipe,
    HorizontalRule,
    MinimalVerticalRange,
)
from cmk.gui.graphing._graph_templates import (
    _compute_graph_recipes,
    TemplateGraphSpecification,
)
from cmk.gui.graphing._translated_metrics import (
    translate_metrics,
)
from cmk.gui.graphing._unit import (
    ConvertibleUnitSpecification,
    DecimalNotation,
    IECNotation,
)
from cmk.gui.type_defs import Perfdata, PerfDataTuple, Row
from cmk.gui.unit_formatter import AutoPrecision
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.utils.servicename import ServiceName

_CPU_UTIL_GRAPHS = {
    "cpu_utilization_simple": graphs_api.Graph(
        name="cpu_utilization_simple",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
        ],
        simple_lines=[
            "util_average",
            "util",
        ],
        optional=["util_average"],
        conflicting=[
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
            "io_wait",
        ],
    ),
    "util_average_1": graphs_api.Graph(
        name="util_average_1",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util"],
        simple_lines=[
            "util_average",
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        conflicting=[
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
            "io_wait",
            "user",
            "system",
        ],
    ),
    "util_average_2": graphs_api.Graph(
        name="util_average_2",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util1"],
        simple_lines=[
            "util15",
            metrics_api.WarningOf("util1"),
            metrics_api.CriticalOf("util1"),
        ],
    ),
    "cpu_utilization_3": graphs_api.Graph(
        name="cpu_utilization_3",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "idle",
            "nice",
        ],
    ),
    "cpu_utilization_4": graphs_api.Graph(
        name="cpu_utilization_4",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "idle",
            "io_wait",
        ],
    ),
    "cpu_utilization_5": graphs_api.Graph(
        name="cpu_utilization_5",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
        ],
        simple_lines=[
            "util_average",
            metrics_api.Sum(
                Title("Total"),
                metrics_api.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=[
            "util",
            "idle",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
    ),
    "cpu_utilization_5_util": graphs_api.Graph(
        name="cpu_utilization_5_util",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=[
            "cpu_util_guest",
            "cpu_util_steal",
        ],
    ),
    "cpu_utilization_6_steal": graphs_api.Graph(
        name="cpu_utilization_6_steal",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            metrics_api.Sum(
                Title("Total"),
                metrics_api.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=[
            "util",
            "cpu_util_guest",
        ],
    ),
    "cpu_utilization_6_steal_util": graphs_api.Graph(
        name="cpu_utilization_6_steal_util",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=["cpu_util_guest"],
    ),
    "cpu_utilization_6_guest": graphs_api.Graph(
        name="cpu_utilization_6_guest",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
        ],
        simple_lines=[
            "util_average",
            metrics_api.Sum(
                Title("Total"),
                metrics_api.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=["util"],
    ),
    "cpu_utilization_6_guest_util": graphs_api.Graph(
        name="cpu_utilization_6_guest_util",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        optional=["util_average"],
        conflicting=["cpu_util_steal"],
    ),
    "cpu_utilization_7": graphs_api.Graph(
        name="cpu_utilization_7",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            metrics_api.Sum(
                Title("Total"),
                metrics_api.Color.GREEN,
                [
                    "user",
                    "system",
                    "io_wait",
                    "cpu_util_guest",
                    "cpu_util_steal",
                ],
            ),
        ],
        optional=["util_average"],
        conflicting=["util"],
    ),
    "cpu_utilization_7_util": graphs_api.Graph(
        name="cpu_utilization_7_util",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "io_wait",
            "cpu_util_guest",
            "cpu_util_steal",
        ],
        simple_lines=[
            "util_average",
            "util",
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        optional=["util_average"],
    ),
    "cpu_utilization_8": graphs_api.Graph(
        name="cpu_utilization_8",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "system",
            "interrupt",
        ],
    ),
    "util_fallback": graphs_api.Graph(
        name="util_fallback",
        title=Title("CPU utilization"),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=["util"],
        simple_lines=[
            metrics_api.WarningOf("util"),
            metrics_api.CriticalOf("util"),
        ],
        conflicting=[
            "util_average",
            "system",
            "engine_cpu_util",
        ],
    ),
    "cpu_utilization": graphs_api.Graph(
        name="cpu_utilization",
        title=Title("CPU utilization"),
        simple_lines=[
            "util",
            "engine_cpu_util",
        ],
    ),
    "cpu_utilization_numcpus": graphs_api.Graph(
        name="cpu_utilization_numcpus",
        title=Title(
            'CPU utilization (_EXPRESSION:{"metric":"util_numcpu_as_max","scalar":"max"} CPU Threads)'
        ),
        minimal_range=graphs_api.MinimalRange(
            0,
            100,
        ),
        compound_lines=[
            "user",
            "privileged",
        ],
        simple_lines=[
            "util_numcpu_as_max",
            metrics_api.WarningOf("util_numcpu_as_max"),
            metrics_api.CriticalOf("util_numcpu_as_max"),
        ],
        optional=[
            "user",
            "privileged",
        ],
    ),
    "cpu_entitlement": graphs_api.Graph(
        name="cpu_entitlement",
        title=Title("CPU entitlement"),
        compound_lines=["cpu_entitlement"],
        simple_lines=["cpu_entitlement_util"],
    ),
}

_MAIL_GRAPHS = {
    "amount_of_mails_in_queues": graphs_api.Graph(
        name="amount_of_mails_in_queues",
        title=Title("Amount of mails in queues"),
        compound_lines=[
            "mail_queue_deferred_length",
            "mail_queue_active_length",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
    "size_of_mails_in_queues": graphs_api.Graph(
        name="size_of_mails_in_queues",
        title=Title("Size of mails in queues"),
        compound_lines=[
            "mail_queue_deferred_size",
            "mail_queue_active_size",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
    "amount_of_mails_in_secondary_queues": graphs_api.Graph(
        name="amount_of_mails_in_secondary_queues",
        title=Title("Amount of mails in queues"),
        compound_lines=[
            "mail_queue_hold_length",
            "mail_queue_incoming_length",
            "mail_queue_drop_length",
        ],
        conflicting=[
            "mail_queue_postfix_total",
            "mail_queue_z1_messenger",
        ],
    ),
}

_MEM_GRAPHS = {
    "ram_used": graphs_api.Graph(
        name="ram_used",
        title=Title("RAM used"),
        minimal_range=graphs_api.MinimalRange(
            0,
            metrics_api.MaximumOf(
                "mem_used",
                metrics_api.Color.GRAY,
            ),
        ),
        compound_lines=["mem_used"],
        simple_lines=[
            metrics_api.MaximumOf(
                "mem_used",
                metrics_api.Color.GRAY,
            ),
            metrics_api.WarningOf("mem_used"),
            metrics_api.CriticalOf("mem_used"),
        ],
        conflicting=[
            "swap_used",
            "mem_free",
        ],
    ),
    "ram_swap_used": graphs_api.Graph(
        name="ram_swap_used",
        title=Title("RAM + Swap used"),
        minimal_range=graphs_api.MinimalRange(
            0,
            metrics_api.Sum(
                Title(""),
                metrics_api.Color.GRAY,
                [
                    metrics_api.MaximumOf(
                        "swap_used",
                        metrics_api.Color.GRAY,
                    ),
                    metrics_api.MaximumOf(
                        "mem_used",
                        metrics_api.Color.GRAY,
                    ),
                ],
            ),
        ),
        compound_lines=[
            "mem_used",
            "swap_used",
        ],
        simple_lines=[
            metrics_api.Sum(
                Title("Total RAM + Swap installed"),
                metrics_api.Color.DARK_CYAN,
                [
                    metrics_api.MaximumOf(
                        "swap_used",
                        metrics_api.Color.GRAY,
                    ),
                    metrics_api.MaximumOf(
                        "mem_used",
                        metrics_api.Color.GRAY,
                    ),
                ],
            ),
            metrics_api.MaximumOf(
                "mem_used",
                metrics_api.Color.GRAY,
            ),
        ],
        conflicting=["swap_total"],
    ),
}

_HEAP_MEM_GRAPH = {
    "heap_and_non_heap_memory": graphs_api.Graph(
        name="heap_and_non_heap_memory",
        title=Title("Heap and non-heap memory"),
        compound_lines=[
            "mem_heap",
            "mem_nonheap",
        ],
        conflicting=[
            "mem_heap_committed",
            "mem_nonheap_committed",
        ],
    ),
    "heap_memory_usage": graphs_api.Graph(
        name="heap_memory_usage",
        title=Title("Heap memory usage"),
        simple_lines=[
            "mem_heap_committed",
            "mem_heap",
            metrics_api.WarningOf("mem_heap"),
            metrics_api.CriticalOf("mem_heap"),
        ],
    ),
    "non-heap_memory_usage": graphs_api.Graph(
        name="non-heap_memory_usage",
        title=Title("Non-heap memory usage"),
        simple_lines=[
            "mem_nonheap_committed",
            "mem_nonheap",
            metrics_api.WarningOf("mem_nonheap"),
            metrics_api.CriticalOf("mem_nonheap"),
            metrics_api.MaximumOf(
                "mem_nonheap",
                metrics_api.Color.GRAY,
            ),
        ],
    ),
}


class _FakeTemplateGraphSpecification(TemplateGraphSpecification):
    def _get_graph_data_from_livestatus(self) -> Row:
        return {
            "site": "site_id",
            "service_perf_data": "metric1=163651.992188;;;; metric2=313848.039062;;;",
            "service_metrics": ["metric1", "metric2"],
            "service_check_command": "check_mk-foo",
            "host_name": "host_name",
            "service_description": "service_name",
        }


@pytest.mark.parametrize(
    ("graph_id", "graph_index", "expected"),
    [
        pytest.param(
            None,
            None,
            [
                GraphRecipe(
                    title="Graph 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Metric1",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric1",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                    specification=_FakeTemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                        graph_index=0,
                        graph_id="graph1",
                    ),
                ),
                GraphRecipe(
                    title="Graph 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Metric2",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric2",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                    specification=_FakeTemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                        graph_index=1,
                        graph_id="graph2",
                    ),
                ),
            ],
            id="no index and no id",
        ),
        pytest.param(
            None,
            0,
            [
                GraphRecipe(
                    title="Graph 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Metric1",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric1",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                    specification=_FakeTemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                        graph_index=0,
                        graph_id="graph1",
                    ),
                ),
            ],
            id="matching index and no id",
        ),
        pytest.param(
            None,
            10,
            [],
            id="non-matching index and no id",
        ),
        pytest.param(
            "graph2",
            None,
            [
                GraphRecipe(
                    title="Graph 2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Metric2",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric2",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                    specification=_FakeTemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                        graph_index=1,
                        graph_id="graph2",
                    ),
                ),
            ],
            id="no index and matching id",
        ),
        pytest.param(
            "wrong",
            None,
            [],
            id="no index and non-matching id",
        ),
        pytest.param(
            "graph1",
            0,
            [
                GraphRecipe(
                    title="Graph 1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Metric1",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="metric1",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#0080c0",
                        )
                    ],
                    specification=_FakeTemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                        graph_id="graph1",
                        graph_index=0,
                    ),
                ),
            ],
            id="matching index and matching id",
        ),
        pytest.param(
            "2",
            0,
            [],
            id="inconsistent matching index and matching id",
        ),
    ],
)
def test_template_recipes_matching(
    graph_id: str | None,
    graph_index: int | None,
    expected: Sequence[GraphRecipe],
) -> None:
    assert (
        _FakeTemplateGraphSpecification(
            site=SiteId("site_id"),
            host_name=HostName("host_name"),
            service_description=ServiceName("service_name"),
            graph_id=graph_id,
            graph_index=graph_index,
        ).recipes(
            {
                "metric1": RegisteredMetric(
                    name="metric1",
                    title_localizer=lambda _localizer: "Metric1",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#0080c0",
                ),
                "metric2": RegisteredMetric(
                    name="metric2",
                    title_localizer=lambda _localizer: "Metric2",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#0080c0",
                ),
            },
            {
                "graph1": graphs_api.Graph(
                    name="graph1",
                    title=Title("Graph 1"),
                    simple_lines=["metric1"],
                ),
                "graph2": graphs_api.Graph(
                    name="graph2",
                    title=Title("Graph 2"),
                    simple_lines=["metric2"],
                ),
            },
            UserPermissions({}, {}, {}, []),
            debug=False,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("metric_names", "check_command", "registered_graphs", "graph_ids"),
    [
        (
            ["user", "system", "wait", "util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5_util"],
        ),
        (
            ["util1", "util15"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_average_2"],
        ),
        (
            ["util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
        ),
        (
            ["util"],
            "check_mk-lxc_container_cpu",
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
        ),
        (
            ["wait", "util", "user", "system"],
            "check_mk-lxc_container_cpu",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5_util"],
        ),
        (
            ["util", "util_average"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_average_1"],
        ),
        (
            ["user", "util_numcpu_as_max"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_numcpus"],
        ),
        (
            ["user", "util"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["util_fallback", "METRIC_user"],
        ),
        (
            ["user", "util"],
            "check_mk-winperf_processor_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_numcpus"],
        ),
        (
            ["user", "system", "idle", "nice"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_3"],
        ),
        (
            ["user", "system", "idle", "io_wait"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4"],
        ),
        (
            ["user", "system", "io_wait"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5"],
        ),
        (
            ["util_average", "util", "wait", "user", "system", "guest"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest_util"],
        ),
        (
            ["user", "system", "io_wait", "guest", "steal"],
            "check_mk-statgrab_cpu",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
        ),
        (
            ["user", "system", "interrupt"],
            "check_mk-kernel_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_8"],
        ),
        (
            ["user", "system", "wait", "util", "cpu_entitlement", "cpu_entitlement_util"],
            "check_mk-lparstat_aix_cpu_util",
            _CPU_UTIL_GRAPHS,
            ["cpu_entitlement", "cpu_utilization_5_util"],
        ),
        (
            ["ramused", "swapused", "memused"],
            "check_mk-statgrab_mem",
            {},
            ["METRIC_mem_lnx_total_used", "METRIC_mem_used", "METRIC_swap_used"],
        ),
        (
            [
                "aws_ec2_running_ondemand_instances_total",
                "aws_ec2_running_ondemand_instances_t2.micro",
                "aws_ec2_running_ondemand_instances_t2.nano",
            ],
            "check_mk-aws_ec2_limits",
            {
                "aws_ec2_running_ondemand_instances_t2": graphs_api.Graph(
                    name="aws_ec2_running_ondemand_instances_t2",
                    title=Title("Total running on-demand instances of type t2"),
                    compound_lines=[
                        "aws_ec2_running_ondemand_instances_t2.2xlarge",
                        "aws_ec2_running_ondemand_instances_t2.large",
                        "aws_ec2_running_ondemand_instances_t2.medium",
                        "aws_ec2_running_ondemand_instances_t2.micro",
                        "aws_ec2_running_ondemand_instances_t2.nano",
                        "aws_ec2_running_ondemand_instances_t2.small",
                        "aws_ec2_running_ondemand_instances_t2.xlarge",
                    ],
                    optional=[
                        "aws_ec2_running_ondemand_instances_t2.2xlarge",
                        "aws_ec2_running_ondemand_instances_t2.large",
                        "aws_ec2_running_ondemand_instances_t2.medium",
                        "aws_ec2_running_ondemand_instances_t2.micro",
                        "aws_ec2_running_ondemand_instances_t2.nano",
                        "aws_ec2_running_ondemand_instances_t2.small",
                        "aws_ec2_running_ondemand_instances_t2.xlarge",
                    ],
                ),
                "aws_ec2_running_ondemand_instances": graphs_api.Graph(
                    name="aws_ec2_running_ondemand_instances",
                    title=Title("Total running on-demand instances"),
                    simple_lines=["aws_ec2_running_ondemand_instances_total"],
                ),
            },
            ["aws_ec2_running_ondemand_instances_t2", "aws_ec2_running_ondemand_instances"],
        ),
    ],
)
def test__compute_graph_recipes_1(
    metric_names: Sequence[str],
    check_command: str,
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    graph_ids: Sequence[str],
) -> None:
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _compute_graph_recipes(
                {},
                registered_graphs,
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                TemplateGraphSpecification(
                    site=SiteId("site_id"),
                    host_name=HostName("host_name"),
                    service_description=ServiceName("service_name"),
                ),
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)


@pytest.mark.parametrize(
    ("metric_names", "warn_crit_min_max", "check_command", "registered_graphs", "graph_ids"),
    [
        pytest.param(
            ["ramused", "swapused", "memused"],
            (0, 1, 2, 3),
            "check_mk-statgrab_mem",
            _MEM_GRAPHS,
            ["METRIC_mem_lnx_total_used", "ram_swap_used"],
            id="ram_swap_used",
        ),
    ],
)
def test__compute_graph_recipes_2(
    metric_names: Sequence[str],
    warn_crit_min_max: tuple[int, int, int, int],
    check_command: str,
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    graph_ids: Sequence[str],
) -> None:
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", *warn_crit_min_max) for n in metric_names]
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _compute_graph_recipes(
                {},
                registered_graphs,
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                TemplateGraphSpecification(
                    site=SiteId("site_id"),
                    host_name=HostName("host_name"),
                    service_description=ServiceName("service_name"),
                ),
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)


@pytest.mark.parametrize(
    (
        "metric_names",
        "predict_metric_names",
        "predict_lower_metric_names",
        "check_command",
        "registered_metrics",
        "registered_graphs",
        "graph_templates",
    ),
    [
        pytest.param(
            [
                "messages_outbound",
                "messages_inbound",
            ],
            [
                "predict_messages_outbound",
                "predict_messages_inbound",
            ],
            [
                "predict_lower_messages_outbound",
                "predict_lower_messages_inbound",
            ],
            "check_mk-inbound_and_outbound_messages",
            {
                "messages_outbound": RegisteredMetric(
                    name="messages_outbound",
                    title_localizer=lambda _localizer: "Outbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                "messages_inbound": RegisteredMetric(
                    name="messages_inbound",
                    title_localizer=lambda _localizer: "Inbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                ),
            },
            {
                "inbound_and_outbound_messages": graphs_api.Graph(
                    name="inbound_and_outbound_messages",
                    title=Title("Inbound and Outbound Messages"),
                    compound_lines=[
                        "messages_outbound",
                        "messages_inbound",
                    ],
                )
            },
            [
                GraphRecipe(
                    title="Inbound and Outbound Messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Outbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1e90ff",
                        ),
                        GraphMetric(
                            title="Inbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1ee6e6",
                        ),
                        GraphMetric(
                            title="Prediction of Inbound messages (upper levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#5a5a5a",
                        ),
                        GraphMetric(
                            title="Prediction of Inbound messages (lower levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#787878",
                        ),
                        GraphMetric(
                            title="Prediction of Outbound messages (upper levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#4b4b4b",
                        ),
                        GraphMetric(
                            title="Prediction of Outbound messages (lower levels)",
                            line_type="line",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#696969",
                        ),
                    ],
                    specification=TemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                    ),
                ),
            ],
            id="matches",
        ),
        pytest.param(
            [
                "messages_outbound",
                "messages_inbound",
                "foo",
            ],
            [
                "predict_foo",
            ],
            [
                "predict_lower_foo",
            ],
            "check_mk-inbound_and_outbound_messages",
            {
                "messages_outbound": RegisteredMetric(
                    name="messages_outbound",
                    title_localizer=lambda _localizer: "Outbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                "messages_inbound": RegisteredMetric(
                    name="messages_inbound",
                    title_localizer=lambda _localizer: "Inbound messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                ),
            },
            {
                "inbound_and_outbound_messages": graphs_api.Graph(
                    name="inbound_and_outbound_messages",
                    title=Title("Inbound and Outbound Messages"),
                    compound_lines=[
                        "messages_outbound",
                        "messages_inbound",
                    ],
                )
            },
            [
                GraphRecipe(
                    title="Inbound and Outbound Messages",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol="/s"),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Outbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_outbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1e90ff",
                        ),
                        GraphMetric(
                            title="Inbound messages",
                            line_type="stack",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="messages_inbound",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol="/s"),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#1ee6e6",
                        ),
                    ],
                    specification=TemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                    ),
                ),
                GraphRecipe(
                    title="Foo",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Foo",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                type="convertible",
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#cc00ff",
                        )
                    ],
                    specification=TemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                    ),
                ),
                GraphRecipe(
                    title="Prediction of Foo (upper levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[
                        HorizontalRule(
                            value=1.0, rendered_value="1", color="#ffd000", title="Warning"
                        ),
                        HorizontalRule(
                            value=2.0, rendered_value="2", color="#ff3232", title="Critical"
                        ),
                    ],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Prediction of Foo (upper levels)",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#4b4b4b",
                        )
                    ],
                    specification=TemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                    ),
                ),
                GraphRecipe(
                    title="Prediction of Foo (lower levels)",
                    unit_spec=ConvertibleUnitSpecification(
                        notation=DecimalNotation(symbol=""),
                        precision=AutoPrecision(digits=2),
                    ),
                    explicit_vertical_range=None,
                    horizontal_rules=[
                        HorizontalRule(
                            value=3.0, rendered_value="3", color="#ffd000", title="Warning"
                        ),
                        HorizontalRule(
                            value=4.0, rendered_value="4", color="#ff3232", title="Critical"
                        ),
                    ],
                    omit_zero_metrics=False,
                    consolidation_function="max",
                    metrics=[
                        GraphMetric(
                            title="Prediction of Foo (lower levels)",
                            line_type="area",
                            operation=GraphMetricRRDSource(
                                site_id=SiteId("site_id"),
                                host_name=HostName("host_name"),
                                service_name=ServiceName("service_name"),
                                metric_name="predict_lower_foo",
                                consolidation_func_name="max",
                                scale=1.0,
                            ),
                            unit=ConvertibleUnitSpecification(
                                notation=DecimalNotation(symbol=""),
                                precision=AutoPrecision(digits=2),
                            ),
                            color="#5a5a5a",
                        )
                    ],
                    specification=TemplateGraphSpecification(
                        site=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_description=ServiceName("service_name"),
                    ),
                ),
            ],
            id="does-not-match",
        ),
    ],
)
def test__compute_graph_recipes_with_predictive_metrics(
    metric_names: Sequence[str],
    predict_metric_names: Sequence[str],
    predict_lower_metric_names: Sequence[str],
    check_command: str,
    registered_metrics: Mapping[str, RegisteredMetric],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    graph_templates: Sequence[GraphRecipe],
) -> None:
    perfdata: Perfdata = (
        [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
        + [PerfDataTuple(n, n[8:], 0, "", 1, 2, None, None) for n in predict_metric_names]
        + [PerfDataTuple(n, n[14:], 0, "", 3, 4, None, None) for n in predict_lower_metric_names]
    )
    translated_metrics = translate_metrics(
        perfdata,
        check_command,
        registered_metrics,
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert [
        graph_recipe
        for _graph_id, graph_recipe in _compute_graph_recipes(
            registered_metrics,
            registered_graphs,
            SiteId("site_id"),
            HostName("host_name"),
            ServiceName("service_name"),
            translated_metrics,
            TemplateGraphSpecification(
                site=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_description=ServiceName("service_name"),
            ),
            temperature_unit=TemperatureUnit.CELSIUS,
        )
    ] == graph_templates


@pytest.mark.parametrize(
    ("metric_names", "registered_graphs", "graph_ids"),
    [
        pytest.param(
            ["user_time", "children_user_time", "system_time", "children_system_time"],
            {
                "used_cpu_time": graphs_api.Graph(
                    name="used_cpu_time",
                    title=Title("Used CPU Time"),
                    compound_lines=[
                        "user_time",
                        "children_user_time",
                        "system_time",
                        "children_system_time",
                    ],
                    simple_lines=[
                        metrics_api.Sum(
                            Title("Total"),
                            metrics_api.Color.DARK_BLUE,
                            [
                                "user_time",
                                "children_user_time",
                                "system_time",
                                "children_system_time",
                            ],
                        )
                    ],
                    conflicting=[
                        "cmk_time_agent",
                        "cmk_time_snmp",
                        "cmk_time_ds",
                    ],
                )
            },
            ["used_cpu_time"],
            id="used_cpu_time",
        ),
        pytest.param(
            [
                "user_time",
                "children_user_time",
                "system_time",
                "children_system_time",
                "cmk_time_agent",
                "cmk_time_snmp",
                "cmk_time_ds",
            ],
            {
                "used_cpu_time": graphs_api.Graph(
                    name="used_cpu_time",
                    title=Title("Used CPU Time"),
                    compound_lines=[
                        "user_time",
                        "children_user_time",
                        "system_time",
                        "children_system_time",
                    ],
                    simple_lines=[
                        metrics_api.Sum(
                            Title("Total"),
                            metrics_api.Color.DARK_BLUE,
                            [
                                "user_time",
                                "children_user_time",
                                "system_time",
                                "children_system_time",
                            ],
                        )
                    ],
                    conflicting=[
                        "cmk_time_agent",
                        "cmk_time_snmp",
                        "cmk_time_ds",
                    ],
                )
            },
            [
                "METRIC_children_system_time",
                "METRIC_children_user_time",
                "METRIC_cmk_time_agent",
                "METRIC_cmk_time_ds",
                "METRIC_cmk_time_snmp",
                "METRIC_system_time",
                "METRIC_user_time",
            ],
            id="used_cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["user_time", "system_time"],
            {
                "cpu_time": graphs_api.Graph(
                    name="cpu_time",
                    title=Title("CPU Time"),
                    compound_lines=[
                        "user_time",
                        "system_time",
                    ],
                    simple_lines=[
                        metrics_api.Sum(
                            Title("Total"),
                            metrics_api.Color.GRAY,
                            [
                                "user_time",
                                "system_time",
                            ],
                        )
                    ],
                    conflicting=["children_user_time"],
                )
            },
            ["cpu_time"],
            id="cpu_time",
        ),
        pytest.param(
            ["user_time", "system_time", "children_user_time"],
            {
                "cpu_time": graphs_api.Graph(
                    name="cpu_time",
                    title=Title("CPU Time"),
                    compound_lines=[
                        "user_time",
                        "system_time",
                    ],
                    simple_lines=[
                        metrics_api.Sum(
                            Title("Total"),
                            metrics_api.Color.GRAY,
                            [
                                "user_time",
                                "system_time",
                            ],
                        )
                    ],
                    conflicting=["children_user_time"],
                )
            },
            ["METRIC_children_user_time", "METRIC_system_time", "METRIC_user_time"],
            id="cpu_time_conflicting_metrics",
        ),
        pytest.param(
            ["util", "util_average"],
            _CPU_UTIL_GRAPHS,
            ["util_average_1"],
            id="util_average_1",
        ),
        pytest.param(
            [
                "util",
                "util_average",
                "util_average_1",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
                "user",
                "system",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util", "METRIC_util_average_1"],
            id="util_average_1_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_simple"],
            id="cpu_utilization_simple",
        ),
        pytest.param(
            [
                "user",
                "system",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
                "io_wait",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_simple_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5"],
            id="cpu_utilization_5",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "idle",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_4", "cpu_utilization_7_util"],
            id="cpu_utilization_5_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_5_util"],
            id="cpu_utilization_5_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "util_average",
                "util",
                "cpu_util_guest",
                "cpu_util_steal",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_5_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_steal"],
            id="cpu_utilization_6_steal",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_steal", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_steal_util"],
            id="cpu_utilization_6_steal_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_steal",
                "util_average",
                "util",
                "cpu_util_guest",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_steal_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "cpu_util_steal"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_6_guest",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "cpu_util_steal",
                "util",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "util_average", "util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest_util"],
            id="cpu_utilization_6_guest_util",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "util_average",
                "util",
                "cpu_util_steal",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_6_guest_util_conflicting_metrics",
        ),
        pytest.param(
            ["user", "system", "io_wait", "cpu_util_guest", "cpu_util_steal", "util_average"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_6_guest", "cpu_utilization_7"],
            id="cpu_utilization_7",
        ),
        pytest.param(
            [
                "user",
                "system",
                "io_wait",
                "cpu_util_guest",
                "cpu_util_steal",
                "util_average",
                "util",
            ],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization_7_util"],
            id="cpu_utilization_7_conflicting_metrics",
        ),
        pytest.param(
            ["util"],
            _CPU_UTIL_GRAPHS,
            ["util_fallback"],
            id="util_fallback",
        ),
        pytest.param(
            ["util", "util_average", "system", "engine_cpu_util"],
            _CPU_UTIL_GRAPHS,
            ["cpu_utilization", "METRIC_system", "METRIC_util_average"],
            id="util_fallback_conflicting_metrics",
        ),
        pytest.param(
            ["fs_used", "fs_free", "fs_size"],
            {
                "fs_used": graphs_api.Graph(
                    name="fs_used",
                    title=Title("Size and used space"),
                    minimal_range=graphs_api.MinimalRange(
                        0,
                        metrics_api.MaximumOf(
                            "fs_used",
                            metrics_api.Color.GRAY,
                        ),
                    ),
                    compound_lines=[
                        "fs_used",
                        "fs_free",
                    ],
                    simple_lines=[
                        "fs_size",
                        metrics_api.WarningOf("fs_used"),
                        metrics_api.CriticalOf("fs_used"),
                    ],
                    conflicting=["reserved"],
                )
            },
            ["fs_used"],
            id="fs_used",
        ),
        pytest.param(
            ["fs_used", "fs_size", "reserved"],
            {
                "fs_used": graphs_api.Graph(
                    name="fs_used",
                    title=Title("Size and used space"),
                    minimal_range=graphs_api.MinimalRange(
                        0,
                        metrics_api.MaximumOf(
                            "fs_used",
                            metrics_api.Color.GRAY,
                        ),
                    ),
                    compound_lines=[
                        "fs_used",
                        "fs_free",
                    ],
                    simple_lines=[
                        "fs_size",
                        metrics_api.WarningOf("fs_used"),
                        metrics_api.CriticalOf("fs_used"),
                    ],
                    conflicting=["reserved"],
                )
            },
            ["METRIC_fs_size", "METRIC_fs_used", "METRIC_reserved"],
            id="fs_used_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_deferred_length", "mail_queue_active_length"],
            _MAIL_GRAPHS,
            ["amount_of_mails_in_queues"],
            id="amount_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_length",
                "mail_queue_active_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            _MAIL_GRAPHS,
            [
                "METRIC_mail_queue_active_length",
                "METRIC_mail_queue_deferred_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_deferred_size", "mail_queue_active_size"],
            _MAIL_GRAPHS,
            ["size_of_mails_in_queues"],
            id="size_of_mails_in_queues",
        ),
        pytest.param(
            [
                "mail_queue_deferred_size",
                "mail_queue_active_size",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            _MAIL_GRAPHS,
            [
                "METRIC_mail_queue_active_size",
                "METRIC_mail_queue_deferred_size",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="size_of_mails_in_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mail_queue_hold_length", "mail_queue_incoming_length", "mail_queue_drop_length"],
            _MAIL_GRAPHS,
            ["amount_of_mails_in_secondary_queues"],
            id="amount_of_mails_in_secondary_queues",
        ),
        pytest.param(
            [
                "mail_queue_hold_length",
                "mail_queue_incoming_length",
                "mail_queue_drop_length",
                "mail_queue_postfix_total",
                "mail_queue_z1_messenger",
            ],
            _MAIL_GRAPHS,
            [
                "METRIC_mail_queue_drop_length",
                "METRIC_mail_queue_hold_length",
                "METRIC_mail_queue_incoming_length",
                "METRIC_mail_queue_postfix_total",
                "METRIC_mail_queue_z1_messenger",
            ],
            id="amount_of_mails_in_secondary_queues_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used", "swap_used"],
            _MEM_GRAPHS,
            ["ram_swap_used"],
            id="ram_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_used", "swap_used", "swap_total"],
            _MEM_GRAPHS,
            ["METRIC_mem_used", "METRIC_swap_total", "METRIC_swap_used"],
            id="ram_swap_used_conflicting_metrics",
        ),
        pytest.param(
            ["mem_lnx_active", "mem_lnx_inactive"],
            {
                "active_and_inactive_memory": graphs_api.Graph(
                    name="active_and_inactive_memory",
                    title=Title("Active and inactive memory"),
                    compound_lines=[
                        "mem_lnx_active",
                        "mem_lnx_inactive",
                    ],
                )
            },
            ["active_and_inactive_memory"],
            id="active_and_inactive_memory",
        ),
        pytest.param(
            ["mem_used"],
            _MEM_GRAPHS,
            ["ram_used"],
            id="ram_used",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap"],
            _HEAP_MEM_GRAPH,
            ["heap_and_non_heap_memory"],
            id="heap_and_non_heap_memory",
        ),
        pytest.param(
            ["mem_heap", "mem_nonheap", "mem_heap_committed", "mem_nonheap_committed"],
            _HEAP_MEM_GRAPH,
            ["heap_memory_usage", "non-heap_memory_usage"],
            id="heap_and_non_heap_memory_conflicting_metrics",
        ),
    ],
)
def test_conflicting_metrics(
    metric_names: Sequence[str],
    registered_graphs: Mapping[str, graphs_api.Graph | graphs_api.Bidirectional],
    graph_ids: Sequence[str],
) -> None:
    # Hard to find all avail metric names of a check plug-in.
    # We test conflicting metrics as following:
    # 1. write test for expected metric names of a graph template if it has "conflicting_metrics"
    # 2. use metric names from (1) and conflicting metrics
    perfdata: Perfdata = [PerfDataTuple(n, n, 0, "", None, None, None, None) for n in metric_names]
    translated_metrics = translate_metrics(
        perfdata,
        "check_command",
        {},
        temperature_unit=TemperatureUnit.CELSIUS,
    )
    assert sorted(
        [
            graph_id
            for graph_id, _graph_recipe in _compute_graph_recipes(
                {},
                registered_graphs,
                SiteId("site_id"),
                HostName("host_name"),
                ServiceName("service_name"),
                translated_metrics,
                TemplateGraphSpecification(
                    site=SiteId("site_id"),
                    host_name=HostName("host_name"),
                    service_description=ServiceName("service_name"),
                ),
                temperature_unit=TemperatureUnit.CELSIUS,
            )
        ]
    ) == sorted(graph_ids)


class _FakeTemplateGraphSpecificationFS(TemplateGraphSpecification):
    def _get_graph_data_from_livestatus(self) -> Row:
        return {
            "site": "site_id",
            "service_perf_data": "fs_used=163651.992188;;;; fs_free=313848.039062;;; fs_size=477500.03125;;;; growth=-1280.489081;;;;",
            "service_metrics": ["fs_used", "fs_free", "fs_size", "growth"],
            "service_check_command": "check_mk-df",
            "host_name": "host_name",
            "service_description": "service_name",
        }


def test_template_recipes_fs() -> None:
    assert _FakeTemplateGraphSpecificationFS(
        site=SiteId("site_id"),
        host_name=HostName("host_name"),
        service_description="service_name",
    ).recipes(
        {
            "fs_growth": RegisteredMetric(
                name="fs_growth",
                title_localizer=lambda _localizer: "Growth",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B/d"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#1ee6e6",
            ),
            "fs_used": RegisteredMetric(
                name="fs_used",
                title_localizer=lambda _localizer: "Used space",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#1e90ff",
            ),
            "fs_free": RegisteredMetric(
                name="fs_free",
                title_localizer=lambda _localizer: "Free space",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#d28df6",
            ),
            "fs_size": RegisteredMetric(
                name="fs_size",
                title_localizer=lambda _localizer: "Total size",
                unit_spec=ConvertibleUnitSpecification(
                    notation=IECNotation(symbol="B"),
                    precision=AutoPrecision(digits=2),
                ),
                color="#37fa37",
            ),
        },
        {
            "fs_used": graphs.Graph(
                name="fs_used",
                title=Title("Size and used space"),
                minimal_range=graphs.MinimalRange(
                    0,
                    metrics.MaximumOf(
                        "fs_used",
                        metrics.Color.GRAY,
                    ),
                ),
                compound_lines=[
                    "fs_used",
                    "fs_free",
                ],
                simple_lines=[
                    "fs_size",
                    metrics.WarningOf("fs_used"),
                    metrics.CriticalOf("fs_used"),
                ],
                conflicting=["reserved"],
            ),
        },
        UserPermissions({}, {}, {}, []),
        debug=False,
        temperature_unit=TemperatureUnit.CELSIUS,
    ) == [
        GraphRecipe(
            title="Size and used space",
            unit_spec=ConvertibleUnitSpecification(
                notation=IECNotation(symbol="B"),
                precision=AutoPrecision(digits=2),
            ),
            explicit_vertical_range=MinimalVerticalRange(min=0.0, max=None),
            horizontal_rules=[],
            omit_zero_metrics=False,
            consolidation_function="max",
            metrics=[
                GraphMetric(
                    title="Used space",
                    line_type="stack",
                    operation=GraphMetricRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name=ServiceName("service_name"),
                        metric_name="fs_used",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1e90ff",
                ),
                GraphMetric(
                    title="Free space",
                    line_type="stack",
                    operation=GraphMetricRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name=ServiceName("service_name"),
                        metric_name="fs_free",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#d28df6",
                ),
                GraphMetric(
                    title="Total size",
                    line_type="line",
                    operation=GraphMetricRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name=ServiceName("service_name"),
                        metric_name="fs_size",
                        consolidation_func_name="max",
                        scale=1048576.0,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#37fa37",
                ),
            ],
            additional_html=None,
            data_range=None,
            mark_requested_end_time=False,
            specification=_FakeTemplateGraphSpecificationFS(
                site=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_description=ServiceName("service_name"),
                graph_index=0,
                graph_id="fs_used",
                destination=None,
            ),
        ),
        GraphRecipe(
            title="Growth",
            unit_spec=ConvertibleUnitSpecification(
                notation=IECNotation(symbol="B/d"),
                precision=AutoPrecision(digits=2),
            ),
            explicit_vertical_range=None,
            horizontal_rules=[],
            omit_zero_metrics=False,
            consolidation_function="max",
            metrics=[
                GraphMetric(
                    title="Growth",
                    line_type="area",
                    operation=GraphMetricRRDSource(
                        site_id=SiteId("site_id"),
                        host_name=HostName("host_name"),
                        service_name=ServiceName("service_name"),
                        metric_name="growth",
                        consolidation_func_name="max",
                        scale=12.136296296296296,
                    ),
                    unit=ConvertibleUnitSpecification(
                        notation=IECNotation(symbol="B/d"),
                        precision=AutoPrecision(digits=2),
                    ),
                    color="#1ee6e6",
                )
            ],
            additional_html=None,
            data_range=None,
            mark_requested_end_time=False,
            specification=_FakeTemplateGraphSpecificationFS(
                site=SiteId("site_id"),
                host_name=HostName("host_name"),
                service_description=ServiceName("service_name"),
                graph_index=1,
                graph_id="METRIC_fs_growth",
                destination=None,
            ),
        ),
    ]
