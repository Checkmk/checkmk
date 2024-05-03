#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import TypeVar

from cmk.plugins.kube import common, prometheus_api, query
from cmk.plugins.kube.schemata import section
from cmk.plugins.lib.node_exporter import NodeExporter, PromQLMetric, SectionStr

Self = TypeVar("Self", bound="Measurement")


class Measurement(common.IdentifiableSample):
    value: float

    @classmethod
    def from_sample(cls: type[Self], sample: prometheus_api.Sample) -> Self:
        return cls(
            pod_name=sample.metric["pod"],
            namespace=sample.metric["namespace"],
            value=sample.value[1],
        )


class CPUMeasurement(Measurement):
    pass


class MemoryMeasurement(Measurement):
    pass


def _filter_fully_labeled(samples: Sequence[prometheus_api.Sample]) -> list[prometheus_api.Sample]:
    # A Prometheus operator (here the sum operator) removes all labels, which are not listed
    # behind the `by` keyword. This means the query `sum(up) by (job, container)` will result in
    # samples with both labels 'job', 'container', one label 'job' or one label 'container' or none.
    # The exact set of samples depends on the collectors present in the cluster and the Prometheus
    # configuration.
    # We can only use samples with the full set of labels.
    return [sample for sample in samples if {"pod", "namespace"} == set(sample.metric)]


def _substitute_if_error(response: query.HTTPResult) -> Sequence[prometheus_api.Sample]:
    return (
        response.data.result
        if isinstance(response, prometheus_api.ResponseSuccess)
        and isinstance(response.data, prometheus_api.Vector)
        else []
    )


def create_selectors(
    cpu_response: query.HTTPResult,
    memory_response: query.HTTPResult,
) -> tuple[common.Selector[CPUMeasurement], common.Selector[MemoryMeasurement]]:
    cpu_samples = _substitute_if_error(cpu_response)
    memory_samples = _substitute_if_error(memory_response)
    return (
        common.Selector(
            [CPUMeasurement.from_sample(s) for s in _filter_fully_labeled(cpu_samples)],
            _aggregate_cpu_metrics,
        ),
        common.Selector(
            [MemoryMeasurement.from_sample(s) for s in _filter_fully_labeled(memory_samples)],
            _aggregate_memory_metrics,
        ),
    )


def _aggregate_cpu_metrics(metrics: Iterable[CPUMeasurement]) -> section.PerformanceUsage:
    return section.PerformanceUsage(
        resource=section.Cpu(usage=sum((m.value for m in metrics), start=0.0))
    )


def _aggregate_memory_metrics(metrics: Iterable[MemoryMeasurement]) -> section.PerformanceUsage:
    return section.PerformanceUsage(
        resource=section.Memory(usage=sum((m.value for m in metrics), start=0.0))
    )


def debug_section(base_url: str, *responses: query.HTTPResponse) -> common.WriteableSection:
    return common.WriteableSection(
        piggyback_name="",
        section_name=common.SectionName("prometheus_debug_v1"),
        section=section.OpenShiftEndpoint(
            url=base_url,
            results=[section.PrometheusResult.from_response(response) for response in responses],
        ),
    )


def machine_sections(
    config: query.PrometheusSessionConfig,
) -> dict[str, str]:
    def promql_getter(promql_expression: str) -> list[PromQLMetric]:
        return query.node_exporter_getter(config, common.LOGGER, promql_expression)

    node_exporter = NodeExporter(promql_getter)
    result_list: dict[str, list[SectionStr]] = {}
    for node_to_section in [
        node_exporter.df_summary(),
        node_exporter.diskstat_summary(),
        node_exporter.kernel_summary(),
        node_exporter.memory_summary(),
        node_exporter.uptime_summary(),
        node_exporter.cpu_summary(),
    ]:
        for node, section_str in node_to_section.items():
            result_list.setdefault(node, []).append(section_str)
    return {node: "\n".join([*node_list, ""]) for node, node_list in result_list.items()}
