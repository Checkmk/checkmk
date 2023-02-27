#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.special_agents.agent_azure import ApiError, MgmtApiClient


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
            "AverageBandwidth,P2SBandwidth",
            ApiError(
                "Failed to find metric configuration for provider: Microsoft.Network, resource Type: virtualNetworkGateways, metric: NonExistingMetric"
            ),
            None,
            id="no valid metrics",
        ),
        pytest.param(
            "AverageBandwidth,P2SBandwidth",
            ApiError("Unexpected ApiError"),
            None,
            id="unexpected error",
        ),
    ],
)
def test_get_available_metrics_from_exception(
    desired_names: str, api_error: ApiError, expected_result: str
) -> None:
    client = MgmtApiClient("1234")

    assert client._get_available_metrics_from_exception(desired_names, api_error) == expected_result
