#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    CPUSampleFactory,
    IdentifiableSampleFactory,
)

from cmk.special_agents.utils_kubernetes.common import (
    create_sections,
    Piggyback,
    PodsToHost,
    SectionName,
    Selector,
)
from cmk.special_agents.utils_kubernetes.performance import _determine_cpu_rate_metrics


def test_determine_cpu_rate_metrics() -> None:
    current_cpu_metric = CPUSampleFactory.build(timestamp=1)
    old_cpu_metric = current_cpu_metric.copy()
    old_cpu_metric.timestamp = 0
    containers_rate_metrics = _determine_cpu_rate_metrics([current_cpu_metric], [old_cpu_metric])
    assert len(containers_rate_metrics) == 1
    assert (
        containers_rate_metrics[0].pod_lookup_from_metric()
        == current_cpu_metric.pod_lookup_from_metric()
    )


def test_determine_cpu_rate_metrics_for_containers_with_same_timestamp() -> None:
    """Test that no rate metrics are returned if no rates can be determined."""
    cpu_metric = CPUSampleFactory.build()
    containers_rate_metrics = _determine_cpu_rate_metrics([cpu_metric], [cpu_metric])
    assert len(containers_rate_metrics) == 0


@pytest.mark.parametrize("size", [2, 4])
def test_selector_one_metric_per_pod(size: int) -> None:
    identies = IdentifiableSampleFactory.batch(size=size)
    pod_names = [i.pod_lookup_from_metric() for i in identies]
    selector: Selector[Any] = Selector(identies, len)  # type: ignore[arg-type]

    sections = list(
        selector.get_section(Piggyback(piggyback="p", pod_names=pod_names), SectionName("s"))
    )

    assert len(sections) == 1
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
