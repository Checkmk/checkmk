#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.azure.agent_based.azure_status import (
    _NO_ISSUES,
    AzureIssue,
    AzureStatusesPerRegion,
    check_azure_status,
    discover_azure_status,
    parse_azure_status,
)

AZURE_STATUS = AzureStatusesPerRegion(
    link="https://status.azure.com/en-us/status/",
    regions={
        "East US": [],
        "Central US": [],
        "North Central US": [
            AzureIssue(
                region="North Central US",
                title="Azure Databricks - North Central US - Investigating",
                description="Some description",
            )
        ],
        "Global": [
            AzureIssue(
                region="Global",
                title="Azure Key Vault issue affecting Azure China",
                description="See details below for status of Azure Key Vault in Azure China regions.",
            ),
            AzureIssue(
                region="Global",
                title="Azure Load Balancer issue",
                description="Azure Load Balancer doesn't work",
            ),
        ],
    },
)


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        (
            [
                [
                    '{"link": "https://status.azure.com/en-us/status/", "regions": ["East US", "Central US", "North Central US", "Global"], "issues": [{"region": "Global", "title": "Azure Key Vault issue affecting Azure China", "description": "See details below for status of Azure Key Vault in Azure China regions."}, {"region": "Global", "title": "Azure Load Balancer issue", "description": "Azure Load Balancer doesn\'t work"}, {"region": "North Central US", "title": "Azure Databricks - North Central US - Investigating", "description": "Some description"}]}'
                ]
            ],
            AZURE_STATUS,
        )
    ],
)
def test_parse_azure_status(
    string_table: StringTable, expected_section: AzureStatusesPerRegion
) -> None:
    assert parse_azure_status(string_table) == expected_section


@pytest.mark.parametrize(
    "section, expected_services",
    [
        (
            AZURE_STATUS,
            [
                Service(item="East US"),
                Service(item="Central US"),
                Service(item="North Central US"),
                Service(item="Global"),
            ],
        )
    ],
)
def test_discover_azure_status(
    section: AzureStatusesPerRegion, expected_services: Sequence[Service]
) -> None:
    assert list(discover_azure_status(section)) == expected_services


@pytest.mark.parametrize(
    "item, section, expected_results",
    [
        pytest.param("West US 2", AZURE_STATUS, [], id="no_item"),
        pytest.param(
            "Central US",
            AZURE_STATUS,
            [_NO_ISSUES],
            id="no_issues",
        ),
        pytest.param(
            "North Central US",
            AZURE_STATUS,
            [
                Result(state=State.WARN, summary="1 issue: https://status.azure.com/en-us/status/"),
                Result(
                    state=State.OK, summary="Azure Databricks - North Central US - Investigating"
                ),
                Result(state=State.OK, notice="Some description"),
            ],
            id="one_issue",
        ),
        pytest.param(
            "Global",
            AZURE_STATUS,
            [
                Result(
                    state=State.WARN, summary="2 issues: https://status.azure.com/en-us/status/"
                ),
                Result(state=State.OK, summary="Azure Key Vault issue affecting Azure China"),
                Result(
                    state=State.OK,
                    notice="See details below for status of Azure Key Vault in Azure China regions.",
                ),
                Result(state=State.OK, summary="Azure Load Balancer issue"),
                Result(state=State.OK, notice="Azure Load Balancer doesn't work"),
            ],
            id="multiple_issues",
        ),
    ],
)
def test_check_azure_status(
    item: str, section: AzureStatusesPerRegion, expected_results: Sequence[Result]
) -> None:
    assert list(check_azure_status(item, section)) == expected_results
