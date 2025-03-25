#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Module for definitions and functions which are used by both the special_agent/agent_kube and
the utils_kubernetes/performance
"""

import itertools
import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

from pydantic import BaseModel

from cmk.plugins.kube.schemata import section
from cmk.special_agents.v0_unstable.agent_common import ConditionalPiggybackSection, SectionWriter

LOGGER = logging.getLogger()
RawMetrics = Mapping[str, str]
PodLookupName = NewType("PodLookupName", str)

SectionName = NewType("SectionName", str)


@dataclass
class Piggyback:
    piggyback: str
    pod_names: Sequence[PodLookupName]


@dataclass
class PodsToHost:
    piggybacks: Sequence[Piggyback]
    namespace_piggies: Sequence[Piggyback]


def lookup_name(namespace: str, name: str) -> PodLookupName:
    """Parse the pod lookup name

    This function parses an identifier which is used to match the pod based on the
    performance data to the associating pod based on the Kubernetes API data

    The namespace & pod name combination is unique across the cluster and is used instead of the pod
    uid due to a cAdvisor bug. This bug causes it to return the container config hash value
    (kubernetes.io/config.hash) as the pod uid for system containers and consequently differs to the
    uid reported by the Kubernetes API.
    """
    return PodLookupName(f"{namespace}_{name}")


class IdentifiableSample(BaseModel):
    namespace: str
    pod_name: str

    def pod_lookup_from_metric(self) -> PodLookupName:
        return lookup_name(self.namespace, self.pod_name)


@dataclass(frozen=True)
class WriteableSection:
    piggyback_name: str
    section_name: SectionName
    section: section.Section


def write_sections(items: Iterable[WriteableSection]) -> None:
    def key_function(item: WriteableSection) -> str:
        return item.piggyback_name

    # Optimize for size of agent output
    for key, group in itertools.groupby(sorted(items, key=key_function), key_function):
        with ConditionalPiggybackSection(key):
            for item in group:
                with SectionWriter(item.section_name) as writer:
                    writer.append(item.section.json())


T_co = TypeVar("T_co", covariant=True, bound=IdentifiableSample)


class Selector(Generic[T_co]):
    def __init__(
        self, metrics: Sequence[T_co], aggregator: Callable[[Sequence[T_co]], section.Section]
    ):
        self.aggregator = aggregator
        self.metrics_map: dict[PodLookupName, list[T_co]] = {}
        for m in metrics:
            key = m.pod_lookup_from_metric()
            self.metrics_map.setdefault(key, []).append(m)

    def get_section(
        self, piggyback: Piggyback, section_name: SectionName
    ) -> Iterator[WriteableSection]:
        metrics = [
            m for pod_name in piggyback.pod_names for m in self.metrics_map.get(pod_name, [])
        ]
        if metrics:
            yield WriteableSection(
                piggyback_name=piggyback.piggyback,
                section_name=section_name,
                section=self.aggregator(metrics),
            )


def create_sections(
    cpu_selector: Selector[IdentifiableSample],
    memory_selector: Selector[IdentifiableSample],
    pods_to_host: PodsToHost,
) -> Iterator[WriteableSection]:
    for piggyback in pods_to_host.piggybacks:
        yield from memory_selector.get_section(
            piggyback,
            SectionName("kube_performance_memory_v1"),
        )
        yield from cpu_selector.get_section(
            piggyback,
            SectionName("kube_performance_cpu_v1"),
        )

    for piggyback in pods_to_host.namespace_piggies:
        yield from memory_selector.get_section(
            piggyback,
            SectionName("kube_resource_quota_performance_memory_v1"),
        )
        yield from cpu_selector.get_section(
            piggyback,
            SectionName("kube_resource_quota_performance_cpu_v1"),
        )
