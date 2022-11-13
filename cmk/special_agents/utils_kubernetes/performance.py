#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
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
from collections.abc import Container, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NewType

from pydantic import BaseModel, parse_raw_as, ValidationError

import cmk.utils

from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes.common import (
    LOGGER,
    lookup_name,
    PodLookupName,
    PodsToHost,
    SectionJson,
    SectionName,
)
from cmk.special_agents.utils_kubernetes.schemata import section

AGENT_TMP_PATH = Path(
    cmk.utils.paths.tmp_dir if os.environ.get("OMD_SITE") else tempfile.gettempdir(), "agent_kube"
)
ContainerName = NewType("ContainerName", str)


class UsedMetrics(str, enum.Enum):
    container_memory_working_set_bytes = "container_memory_working_set_bytes"
    container_cpu_usage_seconds_total = "container_cpu_usage_seconds_total"


class IdentifiableMetric(BaseModel):
    namespace: str
    pod_name: str

    def pod_lookup_from_metric(self) -> PodLookupName:
        return lookup_name(self.namespace, self.pod_name)


class PerformanceMetric(IdentifiableMetric):
    container_name: ContainerName
    name: UsedMetrics
    value: float
    timestamp: float


class MemoryMetric(PerformanceMetric):
    name: Literal[UsedMetrics.container_memory_working_set_bytes]


class CPUMetric(PerformanceMetric):
    name: Literal[UsedMetrics.container_cpu_usage_seconds_total]


class UnusedMetric(BaseModel):
    pass


class CPURateMetric(IdentifiableMetric):
    rate: float


class ContainersStore(BaseModel):
    cpu: Sequence[CPUMetric]


@dataclass
class Metrics:
    cpu: Sequence[CPUMetric]
    memory: Sequence[MemoryMetric]


@dataclass
class PerformancePod:
    # TODO: CMK-11547
    cpu: float
    memory: float


_AllMetrics = MemoryMetric | CPUMetric | UnusedMetric


def parse_performance_metrics(cluster_collector_metrics: bytes) -> Sequence[_AllMetrics]:
    return parse_raw_as(list[_AllMetrics], cluster_collector_metrics)


def group_containers_performance_metrics(
    cluster_name: str,
    container_metrics: Sequence[_AllMetrics],
) -> Mapping[PodLookupName, PerformancePod]:
    """Parse container performance metrics and group them by pod"""

    metrics = _group_metric_types(container_metrics)
    # We only persist the relevant counter metrics (not all metrics)
    current_cycle_store = ContainersStore(cpu=metrics.cpu)
    store_file_name = f"{cluster_name}_containers_counters.json"
    previous_cycle_store = _load_containers_store(
        path=AGENT_TMP_PATH,
        file_name=store_file_name,
    )
    cpu_rate_metrics = _determine_cpu_rate_metrics(
        current_cycle_store.cpu, previous_cycle_store.cpu
    )

    # The agent will store the latest counter values returned by the collector overwriting the
    # previous ones. The collector will return the same metric values for a certain time interval
    # while the values are not updated or outdated. This will result in no rate value if the agent
    # is polled too frequently (no performance section for the checks). All cases where no
    # performance section can be generated should be handled on the check side (reusing the same
    # value, etc.)
    _persist_containers_store(current_cycle_store, path=AGENT_TMP_PATH, file_name=store_file_name)
    return _group_container_metrics_by_pods(cpu_rate_metrics, metrics.memory)


def write_sections_based_on_performance_pods(
    performance_pods: Mapping[PodLookupName, PerformancePod],
    pods_to_host: PodsToHost,
) -> None:
    # TODO: The usage of filter_outdated_and_non_monitored_pods here is really
    # inefficient. We can improve this, if we match the performance_pods to
    # sets of pod_names in a single go.
    LOGGER.info("Write piggyback sections based on performance data")
    for piggy in pods_to_host.piggybacks:
        pods = _select_pods_by_lookup_name(performance_pods, piggy.pod_names)
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in _kube_object_performance_sections(pods):
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)
    LOGGER.info("Write Namespace piggyback sections based on performance data")
    for piggy in pods_to_host.namespace_piggies:
        pods = _select_pods_by_lookup_name(performance_pods, piggy.pod_names)
        resource_quota_pods = _select_pods_by_lookup_name(
            performance_pods, piggy.resource_quota_pod_names
        )
        sections = _kube_object_performance_sections(pods) + _resource_quota_performance_sections(
            resource_quota_pods
        )
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in sections:
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)
    if cluster_performance_pods := _select_pods_by_lookup_name(
        performance_pods, pods_to_host.cluster_pods
    ):
        LOGGER.info("Write cluster sections based on performance data")
        for section_name, section_json in _kube_object_performance_sections(
            cluster_performance_pods
        ):
            with SectionWriter(section_name) as writer:
                writer.append(section_json)


def _group_metric_types(metrics: Sequence[_AllMetrics]) -> Metrics:
    cpu_metrics = []
    memory_metrics = []
    for metric in metrics:
        if isinstance(metric, MemoryMetric):
            memory_metrics.append(metric)
        elif isinstance(metric, CPUMetric):
            cpu_metrics.append(metric)
        elif isinstance(metric, UnusedMetric):
            continue
        else:
            raise NotImplementedError()
    return Metrics(memory=memory_metrics, cpu=cpu_metrics)


def _load_containers_store(path: Path, file_name: str) -> ContainersStore:
    LOGGER.debug("Load previous cycle containers store from %s", file_name)
    try:
        return ContainersStore.parse_file(f"{path}/{file_name}")
    except FileNotFoundError as e:
        LOGGER.info("Could not find metrics file. This is expected if the first run.")
        LOGGER.debug("Exception: %s", e)
    except (ValidationError, json.decoder.JSONDecodeError):
        LOGGER.exception("Found metrics file, but could not parse it.")

    return ContainersStore(cpu=[])


def _persist_containers_store(
    containers_store: ContainersStore, path: Path, file_name: str
) -> None:
    file_path = f"{path}/{file_name}"
    LOGGER.debug("Creating directory %s for containers store file", path)
    path.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Persisting current containers store under %s", file_path)
    with open(file_path, "w") as f:
        f.write(containers_store.json())


def _determine_cpu_rate_metrics(
    cpu_metrics: Sequence[CPUMetric],
    cpu_metrics_old: Sequence[CPUMetric],
) -> Sequence[CPURateMetric]:
    """Determine the rate metrics for each container based on the current and previous
    counter metric values"""

    LOGGER.debug("Determine rate metrics from the latest containers counters stores")
    cpu_metrics_old_map = {metric.container_name: metric for metric in cpu_metrics_old}
    return [
        CPURateMetric(
            pod_name=metric.pod_name,
            namespace=metric.namespace,
            rate=_calculate_rate(metric, old_metric),
        )
        for metric in cpu_metrics
        if (old_metric := cpu_metrics_old_map.get(metric.container_name)) is not None
        and old_metric.timestamp != metric.timestamp
    ]


def _calculate_rate(counter_metric: CPUMetric, old_counter_metric: CPUMetric) -> float:
    """Calculate the rate value based on two counter metric values
    Examples:
        >>> from pydantic_factories import ModelFactory
        >>> class MetricFactory(ModelFactory):
        ...    __model__ = CPUMetric
        >>> _calculate_rate(MetricFactory.build(value=40, timestamp=60),
        ... MetricFactory.build(value=10, timestamp=30))
        1.0
    """
    time_delta = counter_metric.timestamp - old_counter_metric.timestamp
    return (counter_metric.value - old_counter_metric.value) / time_delta


def _group_container_metrics_by_pods(
    cpu_metrics: Sequence[CPURateMetric],
    memory_metrics: Sequence[MemoryMetric],
) -> Mapping[PodLookupName, PerformancePod]:
    parsed_pods: dict[PodLookupName, PerformancePod] = {}
    # TODO: CMK-11547
    for cpu_metric in cpu_metrics:
        parsed_pods.setdefault(
            cpu_metric.pod_lookup_from_metric(), PerformancePod(cpu=0.0, memory=0.0)
        ).cpu += cpu_metric.rate
    for memory_metric in memory_metrics:
        parsed_pods.setdefault(
            memory_metric.pod_lookup_from_metric(), PerformancePod(cpu=0.0, memory=0.0)
        ).memory += memory_metric.value
    return parsed_pods


# TODO: this function is called multiple times at the moment, ideally this should be called once
# probably to do when merging the section write logic
def _select_pods_by_lookup_name(
    performance_pods: Mapping[PodLookupName, PerformancePod],
    lookup_name_to_piggyback_mappings: Container[PodLookupName],
) -> Sequence[PerformancePod]:
    """Filter out all performance data based pods that are not in the API data based lookup table
    Examples:
        >>> from pydantic_factories import ModelFactory
        >>> class PerformancePodFactory(ModelFactory):
        ...    __model__ = PerformancePod
        >>> len(_select_pods_by_lookup_name(
        ... {PodLookupName("foo"): PerformancePodFactory.build()},
        ... {PodLookupName("foo")}))
        1
        >>> _select_pods_by_lookup_name({"foo": PerformancePodFactory.build()}, set())
        []
    """
    LOGGER.info("Filtering out outdated and non-monitored pods from performance data")
    current_pods = []
    outdated_and_non_monitored_pods = []
    for lookup, performance_pod in performance_pods.items():
        if lookup in lookup_name_to_piggyback_mappings:
            current_pods.append(performance_pod)
            continue
        outdated_and_non_monitored_pods.append(lookup)
    LOGGER.debug(
        "Outdated or non-monitored performance pods: %s",
        ", ".join(outdated_and_non_monitored_pods),
    )
    return current_pods


def _kube_object_performance_sections(
    performance_pods: Sequence[PerformancePod],
) -> list[tuple[SectionName, SectionJson]]:
    return [
        (
            SectionName("kube_performance_memory_v1"),
            _section_memory(performance_pods),
        ),
        (
            SectionName("kube_performance_cpu_v1"),
            _section_cpu(performance_pods),
        ),
    ]


def _resource_quota_performance_sections(
    resource_quota_performance_pods: Sequence[PerformancePod],
) -> list[tuple[SectionName, SectionJson]]:
    if not resource_quota_performance_pods:
        return []
    return [
        (
            SectionName("kube_resource_quota_performance_memory_v1"),
            _section_memory(resource_quota_performance_pods),
        ),
        (
            SectionName("kube_resource_quota_performance_cpu_v1"),
            _section_cpu(resource_quota_performance_pods),
        ),
    ]


def _section_memory(
    performance_pods: Sequence[PerformancePod],
) -> SectionJson:
    return SectionJson(
        section.PerformanceUsage(
            resource=section.Memory(usage=sum(pod.memory for pod in performance_pods)),
        ).json()
    )


def _section_cpu(
    performance_pods: Sequence[PerformancePod],
) -> SectionJson:
    return SectionJson(
        section.PerformanceUsage(
            resource=section.Cpu(usage=sum(pod.cpu for pod in performance_pods)),
        ).json()
    )
