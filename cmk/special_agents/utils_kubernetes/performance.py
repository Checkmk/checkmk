#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Module which contains functions to parse and write out the performance data collected from the
Cluster Collector for the Kubernetes Monitoring solution
"""
from __future__ import annotations

import collections
import json
import os
import tempfile
from pathlib import Path
from typing import (
    Callable,
    Collection,
    Container,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pydantic import BaseModel

import cmk.utils

from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils_kubernetes.common import (
    LOGGER,
    lookup_name,
    PodLookupName,
    PodsToHost,
    RawMetrics,
    SectionJson,
    SectionName,
)
from cmk.special_agents.utils_kubernetes.schemata import section

AGENT_TMP_PATH = Path(
    cmk.utils.paths.tmp_dir if os.environ.get("OMD_SITE") else tempfile.gettempdir(), "agent_kube"
)
MetricName = NewType("MetricName", str)
ContainerName = NewType("ContainerName", str)


class PerformanceMetric(BaseModel):
    container_name: ContainerName
    name: MetricName
    value: float
    timestamp: float


class RateMetric(BaseModel):
    name: str
    rate: float


class PerformanceContainer(BaseModel):
    name: ContainerName
    pod_lookup_name: PodLookupName
    metrics: Mapping[MetricName, PerformanceMetric]
    rate_metrics: Optional[Mapping[MetricName, RateMetric]]


class PerformancePod(BaseModel):
    lookup_name: PodLookupName
    containers: List[PerformanceContainer]


class CounterMetric(BaseModel):
    name: MetricName
    value: float
    timestamp: float


class ContainerMetricsStore(BaseModel):
    name: ContainerName
    metrics: Mapping[MetricName, CounterMetric]


class ContainersStore(BaseModel):
    containers: Mapping[ContainerName, ContainerMetricsStore]


class ContainerMetadata(BaseModel):
    name: ContainerName
    pod_lookup_name: PodLookupName


def parse_and_group_containers_performance_metrics(
    cluster_name: str,
    container_metrics: Sequence[RawMetrics],
) -> Mapping[PodLookupName, PerformancePod]:
    """Parse container performance metrics and group them by pod"""

    performance_metrics = _parse_performance_metrics(container_metrics)
    relevant_counter_metrics = [MetricName("cpu_usage_seconds_total")]
    performance_counter_metrics = _filter_specific_metrics(
        performance_metrics, metric_names=relevant_counter_metrics
    )
    containers_counter_metrics = _group_metrics_by_container(performance_counter_metrics)
    # We only persist the relevant counter metrics (not all metrics)
    current_cycle_store = ContainersStore(
        containers={
            # CMK-10333
            container_name: ContainerMetricsStore(name=container_name, metrics=metrics)  # type: ignore[arg-type]
            for container_name, metrics in containers_counter_metrics.items()
        }
    )
    store_file_name = f"{cluster_name}_containers_counters.json"
    previous_cycle_store = _load_containers_store(
        path=AGENT_TMP_PATH,
        file_name=store_file_name,
    )
    containers_rate_metrics = _determine_rate_metrics(
        current_cycle_store.containers, previous_cycle_store.containers
    )

    # The agent will store the latest counter values returned by the collector overwriting the
    # previous ones. The collector will return the same metric values for a certain time interval
    # while the values are not updated or outdated. This will result in no rate value if the agent
    # is polled too frequently (no performance section for the checks). All cases where no
    # performance section can be generated should be handled on the check side (reusing the same
    # value, etc.)
    _persist_containers_store(current_cycle_store, path=AGENT_TMP_PATH, file_name=store_file_name)
    containers_metrics = _group_metrics_by_container(
        performance_metrics, omit_metrics=relevant_counter_metrics
    )
    containers_metadata = _parse_containers_metadata(container_metrics, _pod_lookup_from_metric)
    performance_containers = _group_container_components(
        containers_metadata, containers_metrics, containers_rate_metrics
    )

    performance_pods = _group_containers_by_pods(performance_containers)
    return performance_pods


def write_sections_based_on_performance_pods(
    performance_pods: Mapping[PodLookupName, PerformancePod],
    pods_to_host: PodsToHost,
) -> None:
    # TODO: The usage of filter_outdated_and_non_monitored_pods here is really
    # inefficient. We can improve this, if we match the performance_pods to
    # sets of pod_names in a single go.
    LOGGER.info("Write piggyback sections based on performance data")
    for piggy in pods_to_host.piggybacks:
        pods = _filter_outdated_and_non_monitored_pods(performance_pods.values(), piggy.pod_names)
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in _kube_object_performance_sections(pods):
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)

    LOGGER.info("Write Namespace piggyback sections based on performance data")
    for piggy in pods_to_host.namespace_piggies:
        pods = _filter_outdated_and_non_monitored_pods(performance_pods.values(), piggy.pod_names)
        resource_quota_pods = _filter_outdated_and_non_monitored_pods(
            performance_pods.values(), piggy.resource_quota_pod_names
        )
        sections = _kube_object_performance_sections(pods) + _resource_quota_performance_sections(
            resource_quota_pods
        )
        with ConditionalPiggybackSection(piggy.piggyback):
            for section_name, section_json in sections:
                with SectionWriter(section_name) as writer:
                    writer.append(section_json)

    if cluster_performance_pods := _filter_outdated_and_non_monitored_pods(
        performance_pods.values(), pods_to_host.cluster_pods
    ):
        LOGGER.info("Write cluster sections based on performance data")
        for section_name, section_json in _kube_object_performance_sections(
            cluster_performance_pods
        ):
            with SectionWriter(section_name) as writer:
                writer.append(section_json)


def _pod_lookup_from_metric(metric: Mapping[str, str]) -> PodLookupName:
    return lookup_name(metric["namespace"], metric["pod_name"])


def _load_containers_store(path: Path, file_name: str) -> ContainersStore:
    LOGGER.debug("Load previous cycle containers store from %s", file_name)
    try:
        with open(f"{path}/{file_name}", "r") as f:
            return ContainersStore(**json.loads(f.read()))
    except FileNotFoundError as e:
        LOGGER.info("Could not find metrics file. This is expected if the first run.")
        LOGGER.debug("Exception: %s", e)
    except SyntaxError:
        LOGGER.exception("Found metrics file, but could not parse it.")

    return ContainersStore(containers={})


def _persist_containers_store(
    containers_store: ContainersStore, path: Path, file_name: str
) -> None:
    file_path = f"{path}/{file_name}"
    LOGGER.debug("Creating directory %s for containers store file", path)
    path.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Persisting current containers store under %s", file_path)
    with open(file_path, "w") as f:
        f.write(containers_store.json())


def _parse_performance_metrics(
    cluster_collector_metrics: Sequence[RawMetrics],
) -> Sequence[PerformanceMetric]:
    metrics = []
    for metric in cluster_collector_metrics:
        metric_name = metric["metric_name"].replace("container_", "", 1)
        metrics.append(
            PerformanceMetric(
                container_name=ContainerName(metric["container_name"]),
                name=MetricName(metric_name),
                value=float(metric["metric_value_string"]),
                timestamp=float(metric["timestamp"]),
            )
        )
    return metrics


def _parse_containers_metadata(
    metrics: Sequence[RawMetrics], lookup_func: Callable[[Mapping[str, str]], PodLookupName]
) -> Mapping[ContainerName, ContainerMetadata]:
    containers = {}
    for metric in metrics:
        if (container_name := metric["container_name"]) in containers:
            continue
        containers[ContainerName(container_name)] = ContainerMetadata(
            name=ContainerName(container_name), pod_lookup_name=lookup_func(metric)
        )
    return containers


def _filter_specific_metrics(
    metrics: Sequence[PerformanceMetric], metric_names: Sequence[MetricName]
) -> Iterator[PerformanceMetric]:
    for metric in metrics:
        if metric.name in metric_names:
            yield metric


def _determine_rate_metrics(
    containers_counters: Mapping[ContainerName, ContainerMetricsStore],
    containers_counters_old: Mapping[ContainerName, ContainerMetricsStore],
) -> Mapping[ContainerName, Mapping[MetricName, RateMetric]]:
    """Determine the rate metrics for each container based on the current and previous
    counter metric values"""

    LOGGER.debug("Determine rate metrics from the latest containers counters stores")
    containers = {}
    for container in containers_counters.values():
        if (old_container := containers_counters_old.get(container.name)) is None:
            continue

        container_rate_metrics = _container_available_rate_metrics(
            container.metrics, old_container.metrics
        )

        if not container_rate_metrics:
            continue

        containers[container.name] = container_rate_metrics
    return containers


def _container_available_rate_metrics(
    counter_metrics: Mapping[MetricName, CounterMetric],
    old_counter_metrics: Mapping[MetricName, CounterMetric],
) -> Mapping[MetricName, RateMetric]:
    rate_metrics = {}
    for counter_metric in counter_metrics.values():
        if counter_metric.name not in old_counter_metrics:
            continue

        try:
            rate_value = _calculate_rate(counter_metric, old_counter_metrics[counter_metric.name])
        except ZeroDivisionError:
            continue

        rate_metrics[counter_metric.name] = RateMetric(
            name=counter_metric.name,
            rate=rate_value,
        )
    return rate_metrics


def _calculate_rate(counter_metric: CounterMetric, old_counter_metric: CounterMetric) -> float:
    """Calculate the rate value based on two counter metric values
    Examples:
        >>> _calculate_rate(CounterMetric(name="foo", value=40, timestamp=60),
        ... CounterMetric(name="foo", value=10, timestamp=30))
        1.0
    """
    time_delta = counter_metric.timestamp - old_counter_metric.timestamp
    return (counter_metric.value - old_counter_metric.value) / time_delta


def _group_metrics_by_container(
    performance_metrics: Union[Iterator[PerformanceMetric], Sequence[PerformanceMetric]],
    omit_metrics: Sequence[MetricName] = (),
) -> Mapping[ContainerName, Mapping[MetricName, PerformanceMetric]]:
    containers: DefaultDict[
        ContainerName, Dict[MetricName, PerformanceMetric]
    ] = collections.defaultdict(dict)
    for performance_metric in performance_metrics:
        if performance_metric.name in omit_metrics:
            continue
        containers[performance_metric.container_name][performance_metric.name] = performance_metric
    return containers


def _group_containers_by_pods(
    performance_containers: Iterator[PerformanceContainer],
) -> Mapping[PodLookupName, PerformancePod]:
    parsed_pods: Dict[PodLookupName, List[PerformanceContainer]] = {}
    for container in performance_containers:
        pod_containers = parsed_pods.setdefault(container.pod_lookup_name, [])
        pod_containers.append(container)

    return {
        pod_lookup_name: PerformancePod(lookup_name=pod_lookup_name, containers=containers)
        for pod_lookup_name, containers in parsed_pods.items()
    }


def _group_container_components(
    containers_metadata: Mapping[ContainerName, ContainerMetadata],
    containers_metrics: Mapping[ContainerName, Mapping[MetricName, PerformanceMetric]],
    containers_rate_metrics: Optional[
        Mapping[ContainerName, Mapping[MetricName, RateMetric]]
    ] = None,
) -> Iterator[PerformanceContainer]:
    if containers_rate_metrics is None:
        containers_rate_metrics = {}

    for container in containers_metadata.values():
        yield PerformanceContainer(
            name=container.name,
            pod_lookup_name=container.pod_lookup_name,
            metrics=containers_metrics[container.name],
            rate_metrics=containers_rate_metrics.get(container.name),
        )


# TODO: this function is called multiple times at the moment, ideally this should be called once
# probably to do when merging the section write logic
def _filter_outdated_and_non_monitored_pods(
    performance_pods: Iterable[PerformancePod],
    lookup_name_to_piggyback_mappings: Container[PodLookupName],
) -> Sequence[PerformancePod]:
    """Filter out all performance data based pods that are not in the API data based lookup table

    Examples:
        >>> len(_filter_outdated_and_non_monitored_pods(
        ... [PerformancePod(lookup_name=PodLookupName("foobar"), containers=[])],
        ... {PodLookupName("foobar")}))
        1

        >>> len(_filter_outdated_and_non_monitored_pods(
        ... [PerformancePod(lookup_name=PodLookupName("foobar"), containers=[])],
        ... set()))
        0

    """
    LOGGER.info("Filtering out outdated and non-monitored pods from performance data")
    current_pods = []
    outdated_and_non_monitored_pods = []
    for performance_pod in performance_pods:
        if performance_pod.lookup_name in lookup_name_to_piggyback_mappings:
            current_pods.append(performance_pod)
            continue
        outdated_and_non_monitored_pods.append(performance_pod.lookup_name)

    LOGGER.debug(
        "Outdated or non-monitored performance pods: %s",
        ", ".join(outdated_and_non_monitored_pods),
    )
    return current_pods


def _kube_object_performance_sections(
    performance_pods: Sequence[PerformancePod],
) -> List[Tuple[SectionName, SectionJson]]:
    performance_containers = [container for pod in performance_pods for container in pod.containers]
    return [
        (
            SectionName("kube_performance_memory_v1"),
            _section_memory(performance_containers),
        ),
        (
            SectionName("kube_performance_cpu_v1"),
            _section_cpu(performance_containers),
        ),
    ]


def _resource_quota_performance_sections(
    resource_quota_performance_pods: Sequence[PerformancePod],
) -> List[Tuple[SectionName, SectionJson]]:
    if not resource_quota_performance_pods:
        return []

    performance_containers = [
        container for pod in resource_quota_performance_pods for container in pod.containers
    ]
    return [
        (
            SectionName("kube_resource_quota_performance_memory_v1"),
            _section_memory(performance_containers),
        ),
        (
            SectionName("kube_resource_quota_performance_cpu_v1"),
            _section_cpu(performance_containers),
        ),
    ]


def _section_memory(containers: Collection[PerformanceContainer]) -> SectionJson:
    """Aggregate a metric across all containers"""
    metric = MetricName("memory_working_set_bytes")

    return SectionJson(
        section.PerformanceUsage(
            resource=section.Memory(
                usage=0.0
                + sum(
                    container.metrics[metric].value
                    for container in containers
                    if metric in container.metrics
                ),
            ),
        ).json()
    )


def _section_cpu(containers: Collection[PerformanceContainer]) -> SectionJson:
    """Aggregate a rate metric across all containers"""
    rate_metric = MetricName("cpu_usage_seconds_total")
    return SectionJson(
        section.PerformanceUsage(
            resource=section.Cpu(
                usage=0.0
                + sum(
                    container.rate_metrics[rate_metric].rate
                    for container in containers
                    if container.rate_metrics is not None and rate_metric in container.rate_metrics
                ),
            ),
        ).json()
    )
