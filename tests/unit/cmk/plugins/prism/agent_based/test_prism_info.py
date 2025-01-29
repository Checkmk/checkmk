#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_info import check_prism_info, discovery_prism_info

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
def test_discovery_prism_info(
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
def test_check_prism_info(
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
