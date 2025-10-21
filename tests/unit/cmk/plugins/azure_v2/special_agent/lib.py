#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable
from typing import Any

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import AzureSection, AzureSubscription


class MockAzureSection(AzureSection):
    def __init__(
        self,
        name: str,
        content: list[Any] = [],
        piggytargets: Iterable[str] = ("",),
        separator: int = 124,
    ) -> None:
        super().__init__(name, piggytargets, separator, fake_azure_subscription())
        self._cont = content


def fake_azure_subscription() -> AzureSubscription:
    return AzureSubscription(
        id="mock_subscription_id",
        name="mock_subscription_name",
        tags={},
        safe_hostnames=False,
        tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
    )
