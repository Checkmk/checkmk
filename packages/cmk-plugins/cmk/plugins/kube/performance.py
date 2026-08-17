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
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, NewType, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from cmk.plugins.kube import common
from cmk.plugins.kube.schemata import section
from cmk.server_side_programs.v1_unstable import Storage

AGENT_NAME: Final = "agent_kube"

# How long, in seconds, a previously-computed rate may be reused when the
# collector returns a sample we have already seen and with which we cannot
# calculate a new rate.
PREVIOUS_RATE_VALIDITY_SECS: Final[int] = 300

ContainerName = NewType("ContainerName", str)


class UsedMetric(enum.StrEnum):
    container_memory_working_set_bytes = "container_memory_working_set_bytes"
    container_cpu_usage_seconds_total = "container_cpu_usage_seconds_total"
    container_memory_swap = "container_memory_swap"


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
    metric_name: Literal[UsedMetric.container_memory_working_set_bytes]  # type: ignore[mutable-override]


class CPUSample(PerformanceSample):
    metric_name: Literal[UsedMetric.container_cpu_usage_seconds_total]  # type: ignore[mutable-override]


class SwapSample(PerformanceSample):
    metric_name: Literal[UsedMetric.container_memory_swap]  # type: ignore[mutable-override]


class UnusedSample(BaseModel):
    pass


class CPURateSample(common.IdentifiableSample):
    rate: float


class TimestampedRate(BaseModel):
    sample: CPURateSample
    emitted_at: float


class ContainersStore(BaseModel):
    cpu: Sequence[CPUSample]
    # Rates computed in the previous cycles, so they can be reused while the
    # collector keeps returning unchanged samples.
    rates: Mapping[ContainerName, TimestampedRate] = {}


@dataclass
class Samples:
    cpu: Sequence[CPUSample]
    memory: Sequence[MemorySample]
    swap: Sequence[SwapSample]


_AllSamples = MemorySample | CPUSample | SwapSample | UnusedSample


def parse_performance_metrics(cluster_collector_metrics: bytes) -> Sequence[_AllSamples]:
    # This function is called once per agent_kube invocation. Moving the TypeAdapter definition to
    # import time has no impact. TypeAdapter is faster than RootModel (see CMK-19527), thus
    # remains unchanged.
    # astrein: disable=pydantic-type-adapter
    adapter = TypeAdapter(list[_AllSamples])
    return adapter.validate_json(cluster_collector_metrics)


def create_selectors(
    cluster_name: str, container_metrics: Sequence[_AllSamples]
) -> tuple[
    common.Selector[CPURateSample], common.Selector[MemorySample], common.Selector[SwapSample]
]:
    """Converts parsed metrics into Selectors."""

    metrics = _group_metric_types(container_metrics)
    container_store_key = "containers_counters.json"
    cpu_rate_metrics = create_cpu_rate_samples(
        Storage(AGENT_NAME, cluster_name), container_store_key, metrics.cpu, time.time()
    )
    return (
        common.Selector(cpu_rate_metrics, aggregator=_aggregate_cpu_metrics),
        common.Selector(metrics.memory, aggregator=_aggregate_memory_metrics),
        common.Selector(metrics.swap, aggregator=_aggregate_memory_metrics),
    )


T = TypeVar("T", bound=common.IdentifiableSample)


def _aggregate_memory_metrics(
    metrics: Iterable[MemorySample | SwapSample],
) -> section.PerformanceUsage:
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
    swap_metrics = []
    for metric in metrics:
        if isinstance(metric, MemorySample):
            memory_metrics.append(metric)
        elif isinstance(metric, CPUSample):
            cpu_metrics.append(metric)
        elif isinstance(metric, SwapSample):
            swap_metrics.append(metric)
        elif isinstance(metric, UnusedSample):
            continue
        else:
            raise NotImplementedError
    return Samples(memory=memory_metrics, cpu=cpu_metrics, swap=swap_metrics)


def create_cpu_rate_samples(
    storage: Storage,
    container_store_key: str,
    cpu_samples: Sequence[CPUSample],
    now: float,
) -> Sequence[CPURateSample]:
    previous_cycle_store = _load_containers_store(storage, container_store_key)

    # The collector returns identical samples with the same timestamp for a container
    # if its own data hasn't been updated yet (i.e. the node collector hasn't pushed a
    # new sample to it between two of our polls). No new rate can be computed from an
    # unchanged sample, so the previously computed rate is reused for some time defined
    # by PREVIOUS_RATE_VALIDITY_SECS.
    #
    # Without this, polling the collector twice and getting the same sample would drop the
    # container from the performance sections entirely (missing "CPU usage" on the affected
    # piggyback hosts).
    rate_samples, rates = _determine_cpu_rate_samples(cpu_samples, previous_cycle_store, now)
    current_cycle_store = ContainersStore(cpu=cpu_samples, rates=rates)

    _persist_containers_store(storage, container_store_key, current_cycle_store)
    return rate_samples


def _load_containers_store(storage: Storage, container_store_key: str) -> ContainersStore:
    common.LOGGER.debug(
        "Load previous cycle containers store from %(container_store_key)s",
        {"container_store_key": container_store_key},
    )
    if (content := storage.read(container_store_key, None)) is None:
        common.LOGGER.info("Could not find stored metrics. This is expected if the first run.")
        return ContainersStore(cpu=[])

    try:
        return ContainersStore.model_validate_json(content)
    except (ValidationError, json.decoder.JSONDecodeError):
        common.LOGGER.exception("Found metrics file, but could not parse it.")
        return ContainersStore(cpu=[])


def _persist_containers_store(
    storage: Storage, container_store_key: str, containers_store: ContainersStore
) -> None:
    common.LOGGER.debug(
        "Persisting current containers store under %(container_store_key)s",
        {"container_store_key": container_store_key},
    )
    storage.write(
        container_store_key,
        containers_store.model_dump_json(by_alias=True),
    )


def _determine_cpu_rate_samples(
    cpu_metrics: Sequence[CPUSample],
    previous: ContainersStore,
    now: float,
) -> tuple[Sequence[CPURateSample], Mapping[ContainerName, TimestampedRate]]:
    """Determine the rate metrics for each container based on the current and previous
    counter metric values. If the previous sample and new sample share the same timestamp,
    we cannot calculate a new rate and return the previous one if it exists, unless the
    previous one is older than PREVIOUS_RATE_VALIDITY_SECS."""
    common.LOGGER.debug("Determine rate metrics from the latest containers counters stores")
    cpu_metrics_old_map = {metric.container_name: metric for metric in previous.cpu}
    samples: list[CPURateSample] = []
    rates: dict[ContainerName, TimestampedRate] = {}
    for new_sample in cpu_metrics:
        old_sample = cpu_metrics_old_map.get(new_sample.container_name)
        if old_sample is None:
            # We have never seen this container before, and have no raw sample for it.
            # We need two readings before we can calculate a rate.
            continue
        if old_sample.timestamp != new_sample.timestamp:
            # We have a previous old raw sample, its timestamp is different from the current one
            # so we can treat the data as new and use it to compute a new rate.
            sample = CPURateSample(
                pod_name=new_sample.pod_name,
                namespace=new_sample.namespace,
                rate=_calculate_rate(new_sample, old_sample),
            )
            rates[new_sample.container_name] = TimestampedRate(sample=sample, emitted_at=now)
            samples.append(sample)
        else:
            # Otherwise, the old raw sample's timestamp matches the new one. We cannot compute
            # a rate in this case, because we'd end up dividing by 0 ((s2-s1)/(t2-t1) with t2==t1).
            # This means the cluster collector has not gathered a new data point yet.
            # If we have an old rate, we give a grace period where in this case we return the
            # previous rate (up to a point... after a while we give up and let it go stale).

            # We have an old raw sample, but not necessarily an old _calculated rate_.
            # If there's no old calculated rate, there is nothing we could possibly emit anyway.
            stored = previous.rates.get(new_sample.container_name)
            if stored is None:
                continue

            # We have an old rate. If we are within the grace period, emit it, but keep its
            # timestamp so that next time, if we still don't have a new sample, we can see if
            # we should stop emitting.
            if now - stored.emitted_at <= PREVIOUS_RATE_VALIDITY_SECS:
                rates[new_sample.container_name] = stored
                samples.append(stored.sample)

    return samples, rates


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
