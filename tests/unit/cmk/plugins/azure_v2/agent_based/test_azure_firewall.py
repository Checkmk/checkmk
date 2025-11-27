#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"


from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.azure_v2.agent_based import azure_firewall
from cmk.plugins.azure_v2.agent_based.azure_firewall import (
    discover_azure_firewall_health,
    discover_azure_firewall_snat,
)
from cmk.plugins.azure_v2.agent_based.lib import AzureMetric, Resource

AZURE_FIREWALL_RESOURCE = Resource(
    id="/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Network/azureFirewalls/test-firewall",
    name="test-firewall",
    type="Microsoft.Network/azureFirewalls",
    location="eastus",
    group="test-rg",
    tags={"env": "production"},
    properties={
        "provisioning_state": "Succeeded",
        "threat_intel_mode": "Alert",
        "ip_configurations": [
            {
                "name": "firewall-ip-config",
                "private_ip_address": "10.0.0.4",
            }
        ],
        "firewall_policy_id": "/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Network/firewallPolicies/test-policy",
    },
    metrics={
        "average_FirewallHealth": AzureMetric(
            name="FirewallHealth",
            aggregation="average",
            value=80.0,
            unit="Percent",
        ),
        "maximum_SNATPortUtilization": AzureMetric(
            name="SNATPortUtilization",
            aggregation="maximum",
            value=90.0,
            unit="Percent",
        ),
    },
)


AZURE_FIREWALL_NO_METRICS = Resource(
    id="/subscriptions/test-sub/resourceGroups/test-rg/providers/Microsoft.Network/azureFirewalls/test-firewall-no-metrics",
    name="test-firewall-no-metrics",
    type="Microsoft.Network/azureFirewalls",
    location="eastus",
    group="test-rg",
    metrics={},
)


@pytest.mark.parametrize(
    "resource, expected_services",
    [
        pytest.param(AZURE_FIREWALL_RESOURCE, [Service()], id="resource with metrics"),
        pytest.param(AZURE_FIREWALL_NO_METRICS, [Service()], id="resource without metrics"),
    ],
)
def test_discover_azure_firewall_health(
    resource: Resource, expected_services: Sequence[Service]
) -> None:
    assert list(discover_azure_firewall_health(resource)) == expected_services


@pytest.mark.parametrize(
    "resource, params, expected_results",
    [
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"health": ("fixed", (70.0, 60.0))},
            [
                Result(
                    state=State.OK,
                    summary="Overall health state: 80.00%",
                ),
                Metric("azure_firewall_health", 80.0),
            ],
            id="healthy firewall is ok",
        ),
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"health": ("fixed", (85.0, 75.0))},
            [
                Result(
                    state=State.WARN,
                    summary="Overall health state: 80.00% (warn/crit below 85.00%/75.00%)",
                ),
                Metric("azure_firewall_health", 80.0),
            ],
            id="degraded health is warn",
        ),
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"health": ("fixed", (99.0, 90.0))},
            [
                Result(
                    state=State.CRIT,
                    summary="Overall health state: 80.00% (warn/crit below 99.00%/90.00%)",
                ),
                Metric("azure_firewall_health", 80.0),
            ],
            id="critical health is crit",
        ),
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"health": ("no_levels", None)},
            [
                Result(
                    state=State.OK,
                    summary="Overall health state: 80.00%",
                ),
                Metric("azure_firewall_health", 80.0),
            ],
            id="no levels configured",
        ),
    ],
)
def test_check_azure_firewall(
    resource: Resource,
    params: Mapping[str, Any],
    expected_results: Sequence[Result | Metric],
) -> None:
    check_function = azure_firewall.check_plugin_azure_firewall_health.check_function
    results = list(check_function(params, resource))

    assert results == expected_results


def test_check_azure_firewall_health_no_metrics() -> None:
    check_function = azure_firewall.check_plugin_azure_firewall_health.check_function
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_function({}, AZURE_FIREWALL_NO_METRICS))


def test_discover_azure_firewall_snat() -> None:
    assert list(discover_azure_firewall_snat(AZURE_FIREWALL_RESOURCE)) == [Service()]


@pytest.mark.parametrize(
    "resource, params, expected_results",
    [
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"snat_utilization": ("fixed", (85.0, 95.0))},
            [
                Result(
                    state=State.WARN,
                    summary="Outbound SNAT port utilization: 90.00% (warn/crit at 85.00%/95.00%)",
                ),
                Metric("azure_firewall_snat_port_utilization", 90.0, levels=(85.0, 95.0)),
            ],
            id="snat utilization at warn level",
        ),
        pytest.param(
            AZURE_FIREWALL_RESOURCE,
            {"snat_utilization": ("fixed", (92.0, 97.0))},
            [
                Result(
                    state=State.OK,
                    summary="Outbound SNAT port utilization: 90.00%",
                ),
                Metric("azure_firewall_snat_port_utilization", 90.0, levels=(92.0, 97.0)),
            ],
            id="snat utilization below warn level",
        ),
    ],
)
def test_check_azure_firewall_snat(
    resource: Resource,
    params: Mapping[str, Any],
    expected_results: Sequence[Result | Metric],
) -> None:
    check_function = azure_firewall.check_plugin_azure_firewall_snat.check_function
    results = list(check_function(params, resource))
    assert results == expected_results
