#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from cmk.plugins.kube.common import create_sections, Piggyback, PodsToHost, SectionName, Selector
from cmk.plugins.kube.performance import (
    _determine_cpu_rate_samples,
    ContainersStore,
    PREVIOUS_RATE_VALIDITY_SECS,
    TimestampedRate,
)
from tests.cmk.plugins.kube.agent_kube.factory import (
    CPURateSampleFactory,
    CPUSampleFactory,
    IdentifiableSampleFactory,
)


def test_determine_cpu_rate_samples() -> None:
    current_cpu_metric = CPUSampleFactory.build(timestamp=1)
    old_cpu_metric = current_cpu_metric.model_copy()
    old_cpu_metric.timestamp = 0

    containers_rate_metrics, rates = _determine_cpu_rate_samples(
        [current_cpu_metric], ContainersStore(cpu=[old_cpu_metric]), 100.0
    )

    assert len(containers_rate_metrics) == 1
    assert (
        containers_rate_metrics[0].pod_lookup_from_metric()
        == current_cpu_metric.pod_lookup_from_metric()
    )
    assert rates[current_cpu_metric.container_name].emitted_at == 100.0


def test_determine_cpu_rate_samples_for_containers_with_same_timestamp() -> None:
    """No rate can be determined and none was computed previously."""
    cpu_metric = CPUSampleFactory.build()

    containers_rate_metrics, rates = _determine_cpu_rate_samples(
        [cpu_metric], ContainersStore(cpu=[cpu_metric]), 100.0
    )

    assert len(containers_rate_metrics) == 0
    assert not rates


def test_determine_cpu_rate_samples_reuses_previously_computed_rate() -> None:
    cpu_metric = CPUSampleFactory.build()
    previous_rate = CPURateSampleFactory.build()
    previous = ContainersStore(
        cpu=[cpu_metric],
        rates={cpu_metric.container_name: TimestampedRate(sample=previous_rate, emitted_at=100.0)},
    )

    containers_rate_metrics, rates = _determine_cpu_rate_samples(
        [cpu_metric], previous, 100.0 + PREVIOUS_RATE_VALIDITY_SECS
    )

    assert list(containers_rate_metrics) == [previous_rate]
    # the age of a reused rate must not be reset, or it would never expire
    assert rates[cpu_metric.container_name].emitted_at == 100.0


@pytest.mark.parametrize("size", [2, 4])
def test_selector_one_metric_per_pod(size: int) -> None:
    identies = IdentifiableSampleFactory.batch(size=size)
    pod_names = [i.pod_lookup_from_metric() for i in identies]
    selector: Selector[Any] = Selector(identies, len)  # type: ignore[arg-type]

    sections = list(
        selector.get_section(Piggyback(piggyback="p", pod_names=pod_names), SectionName("s"))
    )

    assert len(sections) == 1
    assert isinstance(sections[0].section, int)
    assert sections[0].section == size


def test_selector_no_metrics() -> None:
    pod_names = [i.pod_lookup_from_metric() for i in IdentifiableSampleFactory.batch(size=5)]
    selector: Selector[Any] = Selector([], len)  # type: ignore[arg-type]

    sections = list(
        selector.get_section(Piggyback(piggyback="p", pod_names=pod_names), SectionName("s"))
    )

    assert len(sections) == 0


def test_kube_create_sections() -> None:
    # Assemble
    identities = IdentifiableSampleFactory.batch(size=2)
    one_metric_per_pod_selector: Selector[Any] = Selector(identities, len)  # type: ignore[arg-type]
    piggyback_name = "host_name"
    piggyback_to_pod_names = [
        Piggyback(piggyback_name, [i.pod_lookup_from_metric() for i in identities])
    ]

    # Act
    sections = list(
        create_sections(
            one_metric_per_pod_selector,
            one_metric_per_pod_selector,
            PodsToHost(
                piggybacks=piggyback_to_pod_names,
                namespace_piggies=[],
            ),
        )
    )

    # Assert
    assert {s.piggyback_name for s in sections} == {piggyback_name}
    assert {s.section_name for s in sections} == {
        SectionName("kube_performance_memory_v1"),
        SectionName("kube_performance_cpu_v1"),
    }


def test_kube_create_resource_quota_sections() -> None:
    # Assemble
    identities = IdentifiableSampleFactory.batch(size=2)
    one_metric_per_pod_selector: Selector[Any] = Selector(identities, len)  # type: ignore[arg-type]
    piggyback_name = "host_name"
    piggyback_to_pod_names = [
        Piggyback(piggyback_name, [i.pod_lookup_from_metric() for i in identities])
    ]

    # Act
    sections = list(
        create_sections(
            one_metric_per_pod_selector,
            one_metric_per_pod_selector,
            PodsToHost(
                piggybacks=[],
                namespace_piggies=piggyback_to_pod_names,
            ),
        )
    )

    # Assert
    assert {s.piggyback_name for s in sections} == {piggyback_name}
    assert {s.section_name for s in sections} == {
        SectionName("kube_resource_quota_performance_memory_v1"),
        SectionName("kube_resource_quota_performance_cpu_v1"),
    }
