#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any, Mapping, Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    State,
)
from cmk.base.plugins.agent_based.azure_load_balancer import (
    check_byte_count,
    check_health,
    check_snat,
)
from cmk.base.plugins.agent_based.utils.azure import AzureMetric, Resource, Section


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={
                        "total_ByteCount": AzureMetric(
                            name="ByteCount", aggregation="total", value=15000.0, unit="bytes"
                        ),
                    },
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            {"lower_levels": (300, 100), "upper_levels": (100000, 500000)},
            [
                Result(
                    state=State.WARN,
                    summary="Bytes transmitted: 250 B/s (warn/crit below 300 B/s/100 B/s)",
                ),
                Metric("byte_count", 250.0, levels=(100000.0, 500000.0)),
            ],
        ),
    ],
)
def test_check_byte_count(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_byte_count(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param({}, "myLoadBalancer", id="no_item_in_section"),
        pytest.param(
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={},
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            id="no_metric_in_section",
        ),
    ],
)
def test_check_byte_count_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_byte_count(item, {}, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        pytest.param(
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={
                        "average_AllocatedSnatPorts": AzureMetric(
                            name="AllocatedSnatPorts",
                            aggregation="average",
                            value=15.5,
                            unit="count",
                        ),
                        "average_UsedSnatPorts": AzureMetric(
                            name="UsedSnatPorts", aggregation="average", value=2.8, unit="count"
                        ),
                    },
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            {"upper_levels": (10, 20)},
            [
                Result(state=State.WARN, summary="SNAT usage: 18.75% (warn/crit at 10.00%/20.00%)"),
                Metric("snat_usage", 18.75, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Allocated SNAT ports: 16"),
                Metric("allocated_snat_ports", 16.0),
                Result(state=State.OK, summary="Used SNAT ports: 3"),
                Metric("used_snat_ports", 3.0),
            ],
            id="allocated_ports_not_0",
        ),
        pytest.param(
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={
                        "average_AllocatedSnatPorts": AzureMetric(
                            name="AllocatedSnatPorts",
                            aggregation="average",
                            value=0.0,
                            unit="count",
                        ),
                        "average_UsedSnatPorts": AzureMetric(
                            name="UsedSnatPorts", aggregation="average", value=3.0, unit="count"
                        ),
                    },
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            {},
            [
                Result(state=State.OK, summary="Allocated SNAT ports: 0"),
                Metric("allocated_snat_ports", 0.0),
                Result(state=State.OK, summary="Used SNAT ports: 3"),
                Metric("used_snat_ports", 3.0),
            ],
            id="allocated_ports_is_0",
        ),
    ],
)
def test_check_snat(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_snat(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        pytest.param({}, "myLoadBalancer", id="no_item_in_section"),
        pytest.param(
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={},
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            id="no_metric_in_section",
        ),
    ],
)
def test_check_snat_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_snat(item, {}, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            {
                "myLoadBalancer": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/CreatePubLBQS-rg/providers/Microsoft.Network/loadBalancers/myLoadBalancer",
                    name="myLoadBalancer",
                    type="Microsoft.Network/loadBalancers",
                    group="CreatePubLBQS-rg",
                    kind=None,
                    location="westeurope",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={
                        "average_VipAvailability": AzureMetric(
                            name="VipAvailability", aggregation="average", value=100.0, unit="count"
                        ),
                        "average_DipAvailability": AzureMetric(
                            name="DipAvailability", aggregation="average", value=50.0, unit="count"
                        ),
                    },
                    subscription="c17d121d-dd5c-4156-875f-1df9862eef93",
                )
            },
            "myLoadBalancer",
            {"vip_availability": (90.0, 25.0), "health_probe": (90.0, 25.0)},
            [
                Result(
                    state=State.OK,
                    summary="Data path availability: 100.00%",
                ),
                Metric("availability", 100.0),
                Result(
                    state=State.WARN,
                    summary="Health probe status: 50.00% (warn/crit below 90.00%/25.00%)",
                ),
                Metric("health_perc", 50.0),
            ],
        ),
    ],
)
def test_check_health(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_health()(item, params, section)) == expected_result
