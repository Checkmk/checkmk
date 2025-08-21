#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cmk.plugins.azure.special_agent.agent_azure import _get_subscriptions, AzureSubscription
from cmk.plugins.azure.special_agent.azure_api_client import ApiError

Args = argparse.Namespace


@pytest.mark.parametrize(
    "azure_subscription, expected_hostname",
    [
        (
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription name",
                tags={},
                safe_hostnames=False,
            ),
            "subscription_name",
        ),
        (
            AzureSubscription(
                id="subscription_id_12345678",
                name="subscription:name",
                tags={},
                safe_hostnames=True,
            ),
            "azr-subscription_name-12345678",
        ),
    ],
)
def test_azuresubscription_hostname(
    azure_subscription: AzureSubscription, expected_hostname: str
) -> None:
    assert azure_subscription.hostname == expected_hostname


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
                proxy="",
                tenant="tenant",
                client="",
                secret="",
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
                proxy="",
                tenant="tenant",
                client="",
                secret="",
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
                proxy="",
                tenant="tenant",
                client="",
                secret="",
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
                proxy="",
                tenant="tenant",
                client="",
                secret="",
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
                proxy="",
                tenant="tenant",
                client="",
                secret="",
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
        "cmk.plugins.azure.special_agent.agent_azure.BaseAsyncApiClient",
        return_value=mock_context_manager,
    ):
        result = await _get_subscriptions(args)
        assert {el.id for el in result} == returned_subscriptions_ids


@pytest.mark.asyncio
async def test_get_subscriptions_wrong_subscription(mock_api_client: AsyncMock) -> None:
    args = Args(
        proxy="",
        tenant="tenant",
        client="",
        secret="",
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
        "cmk.plugins.azure.special_agent.agent_azure.BaseAsyncApiClient",
        return_value=mock_context_manager,
    ):
        with pytest.raises(ApiError, match="Subscription non_existent_subscription_id not found."):
            await _get_subscriptions(args)
