#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.plugins.azure_v2.lib import get_params_from_azure_id


@pytest.mark.parametrize(
    "resource_id, resource_types, expected_params",
    [
        pytest.param(
            "/subscriptions/my-subscription/resourceGroups/my-group",
            None,
            ["my-subscription", "my-group"],
            id="subscription_and_group_only",
        ),
        pytest.param(
            "/subscriptions/my-subscription/resourceGroups/my-group"
            "/providers/Microsoft.Network/publicIPAddresses/my-ip",
            ["publicIPAddresses"],
            ["my-subscription", "my-group", "my-ip"],
            id="single_resource_type",
        ),
        pytest.param(
            "/subscriptions/my-subscription/resourceGroups/my-group"
            "/providers/Microsoft.Network/virtualNetworks/my-vnet"
            "/virtualNetworkPeerings/my-peering",
            ["virtualNetworks", "virtualNetworkPeerings"],
            ["my-subscription", "my-group", "my-vnet", "my-peering"],
            id="nested_resource_types",
        ),
        pytest.param(
            "/SUBSCRIPTIONS/My-Subscription/ResourceGroups/My-Group",
            None,
            ["my-subscription", "my-group"],
            id="case_insensitive",
        ),
    ],
)
def test_get_params_from_azure_id(
    resource_id: str, resource_types: Sequence[str] | None, expected_params: Sequence[str]
) -> None:
    assert get_params_from_azure_id(resource_id, resource_types) == expected_params
