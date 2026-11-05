#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, cast

import pytest

from cmk.agent_based.v2 import (
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.prism.agent_based.prism_cluster_cpu import discovery_prism_cluster_cpu
from cmk.plugins.prism.agent_based.prism_cluster_io import discovery_prism_cluster_io
from cmk.plugins.prism.agent_based.prism_cluster_mem import discovery_prism_cluster_mem
from cmk.plugins.prism.agent_based.prism_info import (
    agent_section_prism_info_v2,
    check_prism_info,
    discovery_prism_info,
    parse_prism_info_v2,
)

SECTION = {
    "block_serials": ["21FM5B310065", "21FM5B310063", "21FM5B310061"],
    "cloudcluster": False,
    "cluster_arch": "X86_64",
    "cluster_fully_qualified_domain_name": None,
    "cluster_usage_critical_alert_threshold_pct": 90,
    "cluster_usage_warning_alert_threshold_pct": 75,
    "encrypted": True,
    "hypervisor_types": ["kKvm"],
    "is_lts": True,
    "name": "Cluster",
    "num_nodes": 3,
    "operation_mode": "Normal",
    "public_keys": [],
    "storage_type": "all_flash",
    "support_verbosity_type": "BASIC_COREDUMP",
    "target_version": "5.20.4.6",
    "version": "5.20.4.6",
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(),
            ],
            id="The service is discovered if data exists.",
        ),
        pytest.param({}, [], id="No services is discovered if no data exists."),
    ],
)
def test_discovery_prism_info(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_info(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["section", "expected_check_result"],
    [
        pytest.param(
            SECTION,
            [
                Result(state=State.OK, summary="Name: Cluster, Version: 5.20.4.6, Nodes: 3"),
            ],
            id="If tunnel is not active the service is OK.",
        ),
        pytest.param(
            {},
            [],
            id="No data",
        ),
    ],
)
def test_check_prism_info(  # type: ignore[misc]
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_info(
                section=section,
            )
        )
        == expected_check_result
    )


def test_v4_cluster_shows_its_name_patch_version_and_nodes(
    v4_cluster_section: Callable[[str], StringTable],
) -> None:
    section = parse_prism_info_v2(v4_cluster_section("cluster-a"))

    assert list(check_prism_info(section)) == [
        Result(state=State.OK, summary="Name: cluster-a, Version: 7.5.0.6, Nodes: 3")
    ]


def test_v4_cluster_without_a_release_in_its_full_version_shows_the_build_version() -> None:
    cluster = {
        "name": "cluster-a",
        "config": {"buildInfo": {"version": "7.5", "fullVersion": "unknown"}},
        "nodes": {"numberOfNodes": 3},
    }

    section = parse_prism_info_v2([[json.dumps(cluster)]])

    assert list(check_prism_info(section)) == [
        Result(state=State.OK, summary="Name: cluster-a, Version: 7.5, Nodes: 3")
    ]


def test_v4_prism_central_shows_its_version_like_the_legacy_api(
    v4_cluster_section: Callable[[str], StringTable],
) -> None:
    section = parse_prism_info_v2(v4_cluster_section("prism-central"))

    assert list(check_prism_info(section)) == [
        Result(state=State.OK, summary="Name: prism-central, Version: pc.7.5.1.1, Nodes: 1")
    ]


@pytest.mark.parametrize("name", ["cluster-a", "prism-central"])
def test_v4_cluster_and_prism_central_are_labelled_as_control_plane(
    name: str, v4_cluster_section: Callable[[str], StringTable]
) -> None:
    section = parse_prism_info_v2(v4_cluster_section(name))
    # The section takes the label function without parameters
    label_function = cast(
        Callable[[Mapping[str, Any]], HostLabelGenerator],
        agent_section_prism_info_v2.host_label_function,
    )

    assert list(label_function(section)) == [HostLabel("cmk/nutanix/object", "control_plane")]


@pytest.mark.parametrize(
    "discover",
    [
        pytest.param(discovery_prism_cluster_cpu, id="CPU"),
        pytest.param(discovery_prism_cluster_mem, id="memory"),
        pytest.param(discovery_prism_cluster_io, id="controller IO"),
    ],
)
def test_v4_cluster_without_stats_gets_no_stats_service(  # type: ignore[misc]
    discover: Callable[[Mapping[str, Any]], DiscoveryResult],
) -> None:
    section = parse_prism_info_v2([[json.dumps({"name": "cluster-a"})]])

    assert not list(discover(section))
