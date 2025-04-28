#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.http_proxy_config import EnvironmentProxyConfig, ExplicitProxyConfig

from cmk.plugins.azure.special_agent.agent_azure import _AuthorityURLs, ApiError, MgmtApiClient

RESOURCE_ID = "/subscriptions/1234/resourceGroups/test/providers/Microsoft.Network/virtualNetworkGateways/vnet_gateway"


@pytest.mark.parametrize(
    "desired_names,api_error,expected_result",
    [
        pytest.param(
            "AverageBandwidth,P2SBandwidth",
            ApiError(
                "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric, Valid metrics: AverageBandwidth,P2SBandwidth"
            ),
            "AverageBandwidth,P2SBandwidth",
            id="all metrics valid",
        ),
        pytest.param(
            "AverageBandwidth,P2SBandwidth",
            ApiError(
                "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric, Valid metrics: AverageBandwidth"
            ),
            "AverageBandwidth",
            id="only one valid",
        ),
        pytest.param(
            "P2SBandwidth",
            ApiError(
                "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric, Valid metrics: AverageBandwidth"
            ),
            None,
            id="no metrics to retry",
        ),
    ],
)
def test_get_available_metrics_from_exception(
    desired_names: str, api_error: ApiError, expected_result: str
) -> None:
    client = MgmtApiClient(
        _AuthorityURLs("login-url", "resource-url", "base-url"),
        EnvironmentProxyConfig(),
        "subscription",
    )

    result = client._get_available_metrics_from_exception(desired_names, api_error, RESOURCE_ID)
    assert result == expected_result


@pytest.mark.parametrize(
    "desired_names,api_error,expected_error",
    [
        pytest.param(
            "AverageBandwidth,P2SBandwidth",
            ApiError(
                "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric"
            ),
            "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric",
            id="no valid metrics",
        ),
        pytest.param(
            "AverageBandwidth,P2SBandwidth",
            ApiError("Unexpected ApiError"),
            "Unexpected ApiError",
            id="unexpected error",
        ),
    ],
)
def test_get_available_metrics_from_exception_error(
    desired_names: str, api_error: ApiError, expected_error: str
) -> None:
    client = MgmtApiClient(
        _AuthorityURLs("login-url", "resource-url", "base-url"),
        ExplicitProxyConfig("http://my-proxy:1234"),
        "subscription",
    )

    with pytest.raises(ApiError, match=expected_error):
        client._get_available_metrics_from_exception(desired_names, api_error, RESOURCE_ID)
