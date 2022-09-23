#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Sequence, Type, TypeVar

from cmk.special_agents.utils_kubernetes import common, prometheus_api
from cmk.special_agents.utils_kubernetes.schemata import section

Self = TypeVar("Self", bound="Measurement")


class Measurement(common.IdentifiableSample):
    value: float

    @classmethod
    def from_sample(cls: Type[Self], sample: prometheus_api.Sample) -> Self:
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


def create_selectors(
    cpu_samples: Sequence[prometheus_api.Sample],
    memory_samples: Sequence[prometheus_api.Sample],
) -> tuple[common.Selector[CPUMeasurement], common.Selector[MemoryMeasurement]]:
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
