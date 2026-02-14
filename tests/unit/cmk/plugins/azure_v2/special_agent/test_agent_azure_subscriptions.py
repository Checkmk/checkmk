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
    "azure_subscription, expected_piggytarget",
    [
        pytest.param(
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription name",
                tags={},
                use_unique_names=False,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "subscription name",
            id="Subscription without unique names",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription:name",
                tags={},
                use_unique_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "subscription:name_2a0cae26",
            id="Subscription with unique names",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_abcdefgh",
                name="My Subscription",
                tags={},
                use_unique_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "My Subscription_560cb603",
            id="Subscription with unique names, different subscription id",
        ),
        pytest.param(
            AzureSubscription(
                id="subscription_id_xyz12345",
                name="My Subscription",
                tags={},
                use_unique_names=True,
                tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
            ),
            "My Subscription_6ab7efb2",
            id="Subscription with unique names, same subscription name, ensures uniqueness",
        ),
    ],
)
def test_azuresubscription_hostname(
    azure_subscription: AzureSubscription, expected_piggytarget: str
) -> None:
    assert azure_subscription.piggytarget == expected_piggytarget


RESOURCE_SUBSCRIPTION = AzureSubscription(
    id="subscription_id",
    name="My Subscription",
    tags={},
    # this should not affect resource groups, although use_unique_name
    # must always be valid for the entire run, and be identical for every object
    use_unique_names=False,
    tenant_id="tenant_id_123",
)
RESOURCE_SUBSCRIPTION_2 = AzureSubscription(
    id="different_subscription_id",
    name="My Subscription 2",
    tags={},
    # this should not affect resource groups, although use_unique_name
    # must always be valid for the entire run, and be identical for every object
    use_unique_names=False,
    tenant_id="tenant_id_123",
)


@pytest.mark.parametrize(
    "resource_group_info, subscription, use_unique_names, expected_piggytarget",
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
            id="Resourcegroup without unique names",
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
            "myresourcegroup_5d6f43b3",
            id="Resourcegroup with unique names",
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
            "myresourcegroup_64a5c469",
            id="Resourcegroup with unique names, different subscription, ensures subscription uniqueness",
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
            "productionrg_5d6f43b3",
            id="Resourcegroup with unique names different_name",
        ),
    ],
)
def test_azureresourcegroup_piggytarget(
    resource_group_info: Mapping[str, Any],
    subscription: AzureSubscription,
    use_unique_names: bool,
    expected_piggytarget: str,
) -> None:
    resource_group = AzureResourceGroup(
        info=resource_group_info,
        tag_key_pattern=TagsImportPatternOption.import_all,
        subscription=subscription,
        use_unique_names=use_unique_names,
    )
    assert resource_group.piggytarget == expected_piggytarget


def test_ensure_different_hashes_subscription_resourcegroups() -> None:
    for use_unique_names in (True, False):
        subscription = AzureSubscription(
            id="subscription_id",
            name="my_subscription",
            tags={},
            use_unique_names=use_unique_names,
            tenant_id="tenant_id_123",
        )

        resource_group = AzureResourceGroup(
            info={
                "id": "/subscriptions/subscription_id/resourceGroups/ProductionRG",
                "name": "my_subscription",  # same name as subscription!
                "type": "Microsoft.Resources/resourceGroups",
                "location": "eastus",
                "tags": {"env": "prod"},
            },
            tag_key_pattern=TagsImportPatternOption.import_all,
            subscription=subscription,
            use_unique_names=use_unique_names,
        )
        # with unique names, the hashes must be different because of different types
        # without unique names, the piggytarget are identical because names are identical
        if use_unique_names:
            assert resource_group.piggytarget != subscription.piggytarget
        else:
            assert resource_group.piggytarget == subscription.piggytarget


@pytest.mark.parametrize(
    "resource_info, subscription, use_unique_names, expected_piggytarget",
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
            id="resource_without_unique_names",
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
            "myVM_555a1dc6",
            id="resource_with_unique_names",
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
            "myVM_b7b0437c",
            id="resource_with_unique_names_ensures_resourcegroup_uniqueness",
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
            "myVM_e9a9a152",
            id="resource_with_unique_names_ensures_subscription_uniqueness",
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
            "mystorageaccount_f5118f4b",
            id="resource_with_unique_names_ensures_type_uniqueness",
        ),
    ],
)
def test_azureresource_piggytarget(
    resource_info: dict[str, Any],
    subscription: AzureSubscription,
    use_unique_names: bool,
    expected_piggytarget: str,
) -> None:
    resource = AzureResource(
        info=resource_info,
        tag_key_pattern=TagsImportPatternOption.import_all,
        subscription=subscription,
        use_unique_names=use_unique_names,
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
                unique_hostnames=False,
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
                unique_hostnames=False,
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
                unique_hostnames=False,
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
                unique_hostnames=False,
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
                unique_hostnames=False,
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
        unique_hostnames=False,
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
