#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"


import argparse
from collections.abc import Mapping
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cmk.password_store.v1_unstable import Secret
from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    _get_subscriptions,
    AzureResource,
    AzureResourceGroup,
    AzureSubscription,
    TagsImportPatternOption,
)
from cmk.plugins.azure_v2.special_agent.azure_api_client import ApiError

Args = argparse.Namespace


@pytest.mark.parametrize(
    "azure_subscription, expected_hostname, expected_piggytarget",
    [
        pytest.param(
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription name",
                tags={},
                use_safe_names=False,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "subscription_name",
            "subscription_name",
            id="Subscription without safe names",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription:name",
                tags={},
                use_safe_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "subscription_name",
            "subscription_name-7828a502",
            id="Subscription with safe names",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_abcdefgh",
                name="My Subscription",
                tags={},
                use_safe_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "My_Subscription",
            "My_Subscription-b03956d8",
            id="Subscription with safe names, different tenant",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_abcdefgh",
                name="My Subscription",
                tags={},
                use_safe_names=True,
                tenant_id="different-tenant-id-12345",
            ),
            "My_Subscription",
            "My_Subscription-adf12475",
            id="Subscription with safe names, different tenant, ensures uniqueness",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_xyz12345",
                name="My Subscription",
                tags={},
                use_safe_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "My_Subscription",
            "My_Subscription-0829b6a4",
            id="Subscription with safe names, same subscription name, ensures uniqueness",
        ),
    ],
)
def test_azuresubscription_hostname(
    azure_subscription: AzureSubscription, expected_hostname: str, expected_piggytarget: str
) -> None:
    assert azure_subscription.hostname == expected_hostname
    assert azure_subscription.piggytarget == expected_piggytarget


RESOURCE_SUBSCRIPTION = AzureSubscription(
    id="subscription_id",
    name="My Subscription",
    tags={},
    # this should not affect resource groups, although use_safe_name
    # must always be valid for the entire run, and be identical for every object
    use_safe_names=False,
    tenant_id="tenant_id_123",
)
RESOURCE_SUBSCRIPTION_2 = AzureSubscription(
    id="different_subscription_id",
    name="My Subscription 2",
    tags={},
    # this should not affect resource groups, although use_safe_name
    # must always be valid for the entire run, and be identical for every object
    use_safe_names=False,
    tenant_id="tenant_id_123",
)


@pytest.mark.parametrize(
    "resource_group_info, subscription, use_safe_names, expected_piggytarget",
    [
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/myResourceGroup",
                "name": "myResourceGroup",
                "type": "Microsoft.Resources/resourceGroups",
                "location": "westeurope",
                "tags": {},
            },
            RESOURCE_SUBSCRIPTION,
            False,
            "myresourcegroup",
            id="Resourcegroup without safe names",
        ),
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/myResourceGroup",
                "name": "myResourceGroup",
                "type": "Microsoft.Resources/resourceGroups",
                "location": "westeurope",
                "tags": {},
            },
            RESOURCE_SUBSCRIPTION,
            True,
            "myresourcegroup-2c08a2b6",
            id="Resourcegroup with safe names",
        ),
        pytest.param(
            {
                "id": "/subscriptions/different_subscription_id/resourceGroups/myResourceGroup",
                "name": "myResourceGroup",
                "type": "Microsoft.Resources/resourceGroups",
                "location": "westeurope",
                "tags": {},
            },
            RESOURCE_SUBSCRIPTION_2,
            True,
            "myresourcegroup-2a69b329",
            id="Resourcegroup with safe names, different subscription, ensures subscription uniqueness",
        ),
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/ProductionRG",
                "name": "ProductionRG",
                "type": "Microsoft.Resources/resourceGroups",
                "location": "eastus",
                "tags": {"env": "prod"},
            },
            RESOURCE_SUBSCRIPTION,
            True,
            "productionrg-2c08a2b6",
            id="Resourcegroup with safe names different_name",
        ),
    ],
)
def test_azureresourcegroup_piggytarget(
    resource_group_info: Mapping[str, Any],
    subscription: AzureSubscription,
    use_safe_names: bool,
    expected_piggytarget: str,
) -> None:
    resource_group = AzureResourceGroup(
        info=resource_group_info,
        tag_key_pattern=TagsImportPatternOption.import_all,
        subscription=subscription,
        use_safe_names=use_safe_names,
    )
    assert resource_group.piggytarget == expected_piggytarget


@pytest.mark.parametrize(
    "resource_info, subscription, use_safe_names, expected_piggytarget",
    [
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/myResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
                "name": "myVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {},
                "group": "myResourceGroup",
            },
            RESOURCE_SUBSCRIPTION,
            False,
            "myVM",
            id="resource_without_safe_names",
        ),
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/myResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
                "name": "myVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {},
                "group": "myResourceGroup",
            },
            RESOURCE_SUBSCRIPTION,
            True,
            "myVM-eaad1ffc",
            id="resource_with_safe_names",
        ),
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/DifferentRG/providers/Microsoft.Compute/virtualMachines/myVM",
                "name": "myVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {},
                "group": "DifferentRG",
            },
            RESOURCE_SUBSCRIPTION,
            True,
            "myVM-03064269",
            id="resource_with_safe_names_ensures_resourcegroup_uniqueness",
        ),
        pytest.param(
            {
                "id": "/subscriptions/different_subscription_id/resourceGroups/myResourceGroup/providers/Microsoft.Compute/virtualMachines/myVM",
                "name": "myVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {},
                "group": "myResourceGroup",
            },
            RESOURCE_SUBSCRIPTION_2,
            True,
            "myVM-c22c6773",
            id="resource_with_safe_names_ensures_subscription_uniqueness",
        ),
        pytest.param(
            {
                "id": "/subscriptions/subscription_id/resourceGroups/myResourceGroup/providers/Microsoft.Storage/storageAccounts/mystorageaccount",
                "name": "mystorageaccount",
                "type": "Microsoft.Storage/storageAccounts",
                "location": "westeurope",
                "tags": {},
                "group": "myResourceGroup",
            },
            RESOURCE_SUBSCRIPTION,
            True,
            "mystorageaccount-17e577e2",
            id="resource_with_safe_names_ensures_type_uniqueness",
        ),
    ],
)
def test_azureresource_piggytarget(
    resource_info: dict[str, Any],
    subscription: AzureSubscription,
    use_safe_names: bool,
    expected_piggytarget: str,
) -> None:
    resource = AzureResource(
        info=resource_info,
        tag_key_pattern=TagsImportPatternOption.import_all,
        subscription=subscription,
        use_safe_names=use_safe_names,
    )
    assert resource.piggytarget == expected_piggytarget


RESOURCE_GROUPS_RESPONSE = {
    "value": [
        {
            "subscriptionId": "subscription_id_12345678",
            "displayName": "Subscription Name 1",
            "tags": {"key1": "value1", "key2": "value2"},
        },
        {
            "subscriptionId": "subscription_id_987654321",
            "displayName": "Subscription Name 2",
            "tags": {},
        },
        {
            "subscriptionId": "subscription_id_abcdefgh",
            "displayName": "Subscription Name 3",
            "tags": {},
        },
    ]
}


@pytest.mark.parametrize(
    "args, returned_subscriptions_ids",
    [
        (
            Args(
                debug=True,
                proxy="",
                tenant="tenant",
                client="",
                secret=Secret(""),
                authority="global",
                no_subscriptions=True,
                all_subscriptions=False,
                subscriptions=None,
                safe_hostnames=False,
                subscriptions_require_tag=[],
                subscriptions_require_tag_value=[],
            ),
            set(),
        ),
        (
            Args(
                debug=True,
                proxy="",
                tenant="tenant",
                client="",
                secret=Secret(""),
                authority="global",
                no_subscriptions=False,
                all_subscriptions=True,
                subscriptions=None,
                safe_hostnames=False,
                subscriptions_require_tag=[],
                subscriptions_require_tag_value=[],
            ),
            {
                "subscription_id_12345678",
                "subscription_id_987654321",
                "subscription_id_abcdefgh",
            },
        ),
        (
            Args(
                debug=True,
                proxy="",
                tenant="tenant",
                client="",
                secret=Secret(""),
                authority="global",
                no_subscriptions=False,
                all_subscriptions=False,
                subscriptions=[
                    "subscription_id_987654321",
                    "subscription_id_abcdefgh",
                ],
                safe_hostnames=False,
                subscriptions_require_tag=[],
                subscriptions_require_tag_value=[],
            ),
            {
                "subscription_id_987654321",
                "subscription_id_abcdefgh",
            },
        ),
        (
            Args(
                debug=True,
                proxy="",
                tenant="tenant",
                client="",
                secret=Secret(""),
                authority="global",
                no_subscriptions=False,
                all_subscriptions=False,
                subscriptions=None,
                safe_hostnames=False,
                subscriptions_require_tag=[("key2")],
                subscriptions_require_tag_value=[("key1", "value1")],
            ),
            {
                "subscription_id_12345678",
            },
        ),
        (
            Args(
                debug=True,
                proxy="",
                tenant="tenant",
                client="",
                secret=Secret(""),
                authority="global",
                no_subscriptions=False,
                all_subscriptions=False,
                subscriptions=None,
                safe_hostnames=False,
                subscriptions_require_tag=[("key_non_existent")],
                subscriptions_require_tag_value=[("key1", "value1")],
            ),
            set(),
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_subscriptions(
    args: Args,
    returned_subscriptions_ids: set[str],
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.request_async.return_value = RESOURCE_GROUPS_RESPONSE
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__.return_value = mock_api_client

    with patch(
        "cmk.plugins.azure_v2.special_agent.agent_azure_v2.BaseAsyncApiClient",
        return_value=mock_context_manager,
    ):
        result = await _get_subscriptions(args)
        assert {el.id for el in result} == returned_subscriptions_ids


@pytest.mark.asyncio
async def test_get_subscriptions_wrong_subscription(mock_api_client: AsyncMock) -> None:
    args = Args(
        debug=True,
        proxy="",
        tenant="tenant",
        client="",
        secret=Secret(""),
        authority="global",
        no_subscriptions=False,
        all_subscriptions=False,
        subscriptions=[
            "subscription_id_987654321",
            "non_existent_subscription_id",
        ],
        safe_hostnames=False,
        subscriptions_require_tag=[],
        subscriptions_require_tag_value=[],
    )

    mock_api_client.request_async.return_value = RESOURCE_GROUPS_RESPONSE
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__.return_value = mock_api_client

    with patch(
        "cmk.plugins.azure_v2.special_agent.agent_azure_v2.BaseAsyncApiClient",
        return_value=mock_context_manager,
    ):
        with pytest.raises(ApiError, match="Subscription non_existent_subscription_id not found."):
            await _get_subscriptions(args)
