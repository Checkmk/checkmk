#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from unittest.mock import AsyncMock

import pytest

from cmk.plugins.azure.special_agent.agent_azure import AzureSubscription
from cmk.plugins.azure.special_agent.azure_api_client import BaseAsyncApiClient


@pytest.fixture(scope="session")
def mock_api_client() -> AsyncMock:
    return AsyncMock(spec=BaseAsyncApiClient)


def fake_azure_subscription() -> AzureSubscription:
    return AzureSubscription(
        id="mock_subscription_id",
        name="mock_subscription_name",
        tags={},
        safe_hostnames=False,
    )


@pytest.fixture(scope="session")
def mock_azure_subscription() -> AzureSubscription:
    return fake_azure_subscription()
