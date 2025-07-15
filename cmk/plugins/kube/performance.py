#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Module which contains functions to parse and write out the performance data collected from the
Cluster Collector for the Kubernetes Monitoring solution
"""

from __future__ import annotations

import enum
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NewType, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

import cmk.utils
from cmk.plugins.kube import common
from cmk.plugins.kube.schemata import section

AGENT_TMP_PATH = (
    cmk.utils.paths.tmp_dir if os.environ.get("OMD_SITE") else Path(tempfile.gettempdir())
) / "agent_kube"

ContainerName = NewType("ContainerName", str)


class UsedMetric(str, enum.Enum):
    container_memory_working_set_bytes = "container_memory_working_set_bytes"
    container_cpu_usage_seconds_total = "container_cpu_usage_seconds_total"


class PerformanceSample(common.IdentifiableSample):
    """BaseModel for parsing data obtained from the `/container_metrics` endpoint.

    From https://prometheus.io/docs/concepts/data_model/
    > Prometheus fundamentally stores all data as time series: streams of timestamped values
    > belonging to the same metric and the same set of labeled dimensions. Every time series is
    > uniquely identified by its metric name and optional key-value pairs called labels.
    > Samples form the actual time series data. Each sample consists of:
    > - a float64 value
    > - a millisecond-precision timestamp

    Here, we additionally includes the metric labels inside a `Sample`. This is similar to the HTTP
    API of Prometheus.

    The sample matching mechanism between different timeseries objects behaves as follows:
    - Prometheus: matches the samples based on the full set of labels
    - cAdvisor: matches the samples through the `container_name` label
    agent_kube implements matching in the same manner as the cAdvisor approach.
    """

    container_name: ContainerName
    metric_name: UsedMetric
    metric_value_string: str
    timestamp: float

    def value(self) -> float:
        return float(self.metric_value_string)


class MemorySample(PerformanceSample):
    metric_name: Literal[UsedMetric.container_memory_working_set_bytes]


class CPUSample(PerformanceSample):
    metric_name: Literal[UsedMetric.container_cpu_usage_seconds_total]


class UnusedSample(BaseModel):
    pass


class CPURateSample(common.IdentifiableSample):
    rate: float


class ContainersStore(BaseModel):
    cpu: Sequence[CPUSample]


@dataclass
class Samples:
    cpu: Sequence[CPUSample]
    memory: Sequence[MemorySample]


_AllSamples = MemorySample | CPUSample | UnusedSample


def parse_performance_metrics(cluster_collector_metrics: bytes) -> Sequence[_AllSamples]:
    # This function is called once per agent_kube invocation. Moving the TypeAdapter definition to
    # import time has no impact. TypeAdapter is faster than RootModel (see CMK-19527), thus
    # remains unchanged.
    # nosemgrep: type-adapter-detected
    adapter = TypeAdapter(list[_AllSamples])
    return adapter.validate_json(cluster_collector_metrics)


def create_selectors(
    cluster_name: str, container_metrics: Sequence[_AllSamples]
) -> tuple[common.Selector[CPURateSample], common.Selector[MemorySample]]:
    """Converts parsed metrics into Selectors."""

    metrics = _group_metric_types(container_metrics)
    container_store_path = AGENT_TMP_PATH.joinpath(f"{cluster_name}_containers_counters.json")
    cpu_rate_metrics = _create_cpu_rate_metrics(container_store_path, metrics.cpu)
    return (
        common.Selector(cpu_rate_metrics, aggregator=_aggregate_cpu_metrics),
        common.Selector(metrics.memory, aggregator=_aggregate_memory_metrics),
    )


T = TypeVar("T", bound=common.IdentifiableSample)


def _aggregate_memory_metrics(metrics: Iterable[MemorySample]) -> section.PerformanceUsage:
    return section.PerformanceUsage(
        resource=section.Memory(usage=sum((m.value() for m in metrics), start=0.0))
    )


def _aggregate_cpu_metrics(metrics: Iterable[CPURateSample]) -> section.PerformanceUsage:
    return section.PerformanceUsage(
        resource=section.Cpu(usage=sum((m.rate for m in metrics), start=0.0))
    )


def _group_metric_types(metrics: Sequence[_AllSamples]) -> Samples:
    cpu_metrics = []
    memory_metrics = []
    for metric in metrics:
        if isinstance(metric, MemorySample):
            memory_metrics.append(metric)
        elif isinstance(metric, CPUSample):
            cpu_metrics.append(metric)
        elif isinstance(metric, UnusedSample):
            continue
        else:
            raise NotImplementedError()
    return Samples(memory=memory_metrics, cpu=cpu_metrics)


def _create_cpu_rate_metrics(
    container_store_path: Path, cpu_metrics: Sequence[CPUSample]
) -> Sequence[CPURateSample]:
    # We only persist the relevant counter metrics (not all metrics)
    current_cycle_store = ContainersStore(cpu=cpu_metrics)
    previous_cycle_store = _load_containers_store(container_store_path)

    # The agent will store the latest counter values returned by the collector overwriting the
    # previous ones. The collector will return the same metric values for a certain time interval
    # while the values are not updated or outdated. This will result in no rate value if the agent
    # is polled too frequently (no performance section for the checks). All cases where no
    # performance section can be generated should be handled on the check side (reusing the same
    # value, etc.)
    _persist_containers_store(container_store_path, current_cycle_store)
    return _determine_cpu_rate_metrics(current_cycle_store.cpu, previous_cycle_store.cpu)


def _load_containers_store(container_store_path: Path) -> ContainersStore:
    common.LOGGER.debug("Load previous cycle containers store from %s", container_store_path)
    try:
        with open(container_store_path, encoding="utf-8") as file:
            return ContainersStore.model_validate_json(file.read())
    except FileNotFoundError as e:
        common.LOGGER.info("Could not find metrics file. This is expected if the first run.")
        common.LOGGER.debug("Exception: %s", e)
    except (ValidationError, json.decoder.JSONDecodeError):
        common.LOGGER.exception("Found metrics file, but could not parse it.")

    return ContainersStore(cpu=[])


def _persist_containers_store(
    container_store_path: Path, containers_store: ContainersStore
) -> None:
    common.LOGGER.debug("Persisting current containers store under %s", container_store_path)
    container_store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(container_store_path, "w", encoding="utf-8") as f:
        f.write(containers_store.model_dump_json(by_alias=True))


def _determine_cpu_rate_metrics(
    cpu_metrics: Sequence[CPUSample],
    cpu_metrics_old: Sequence[CPUSample],
) -> Sequence[CPURateSample]:
    """Determine the rate metrics for each container based on the current and previous
    counter metric values"""
    common.LOGGER.debug("Determine rate metrics from the latest containers counters stores")
    cpu_metrics_old_map = {metric.container_name: metric for metric in cpu_metrics_old}
    return [
        CPURateSample(
            pod_name=metric.pod_name,
            namespace=metric.namespace,
            rate=_calculate_rate(metric, old_metric),
        )
        for metric in cpu_metrics
        if (old_metric := cpu_metrics_old_map.get(metric.container_name)) is not None
        and old_metric.timestamp != metric.timestamp
    ]


def _calculate_rate(counter_metric: CPUSample, old_counter_metric: CPUSample) -> float:
    """Calculate the rate value based on two counter metric values
    Example:
        >>> _calculate_rate(
        ...     CPUSample(
        ...         namespace="foo",
        ...         pod_name="bar",
        ...         container_name=ContainerName("baz"),
        ...         metric_name=UsedMetric.container_cpu_usage_seconds_total,
        ...         metric_value_string="40",
        ...         timestamp=60,
        ...     ),
        ...     CPUSample(
        ...         namespace="foo",
        ...         pod_name="bar",
        ...         container_name=ContainerName("baz"),
        ...         metric_name=UsedMetric.container_cpu_usage_seconds_total,
        ...         metric_value_string="10",
        ...         timestamp=30,
        ...     ),
        ... )
        1.0
    """
    time_delta = counter_metric.timestamp - old_counter_metric.timestamp
    return (counter_metric.value() - old_counter_metric.value()) / time_delta
