#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from unittest import mock

import pytest
from feedparser.util import FeedParserDict  # type: ignore[import-untyped,unused-ignore]

from cmk.plugins.azure_status.lib.azure_regions import AZURE_REGIONS
from cmk.plugins.azure_status.special_agent.agent_azure_status import (
    get_affected_regions,
    parse_arguments,
    write_section,
)

STATUS_RESPONSE = """
<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:a10="http://www.w3.org/2005/Atom"
  version="2.0">
  <channel xmlns:slash="http://purl.org/rss/1.0/modules/slash/" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:wfw="http://wellformedweb.org/CommentAPI/" xmlns:dc="http://purl.org/dc/elements/1.1/">
    <title>Azure Status</title>
    <link>https://status.azure.com/en-us/status/</link>
    <description>Azure Status</description>
    <language>en-us</language>
    <lastBuildDate>Thu, 17 Nov 2022 08:36:00 Z</lastBuildDate>
    <item> <title>Azure Key Vault issue affecting Azure China</title> <description>Description of the Azure Key Vault problem</description></item>
    <item> <title>Azure Databricks - North Central US - Investigating</title><description>Description of the Azure Databricks problem</description></item>
    <item> <category>Azure Synapse Analytics</category><category>West Europe</category><title>Azure Synapse Analytics Mitigating</title><description><p><strong>Impact Statement:</strong> Azure Synapse Analytics customers  may be experiencing connectivity issues</p></description></item>
  </channel>
</rss>
"""


class MockResponse:
    text = STATUS_RESPONSE


def test_parse_arguments() -> None:
    args = parse_arguments(["eastus", "centralus", "northcentralus"])
    assert args.regions == ["eastus", "centralus", "northcentralus"]


@pytest.mark.parametrize(
    "entry, expected_result",
    [
        (
            FeedParserDict(
                {
                    "title": "Azure Databricks - North Central US - Investigating",
                    "title_detail": {
                        "type": "text/plain",
                        "language": None,
                        "base": "",
                        "value": "Azure Databricks - North Central US - Investigating",
                    },
                    "summary": "Description of the Azure Databricks problem",
                    "summary_detail": {
                        "type": "text/html",
                        "language": None,
                        "base": "",
                        "value": "Description of the Azure Databricks problem",
                    },
                }
            ),
            {"North Central US"},
        ),
        (
            FeedParserDict(
                {
                    "title": "Azure Key Vault issue affecting Azure China",
                    "title_detail": {
                        "type": "text/plain",
                        "language": None,
                        "base": "",
                        "value": "Azure Key Vault issue affecting Azure China",
                    },
                    "summary": "The problem is affecting the region China North 2",
                    "summary_detail": {
                        "type": "text/html",
                        "language": None,
                        "base": "",
                        "value": "The problem is affecting the region China North 2",
                    },
                }
            ),
            {"China North 2"},
        ),
        (
            FeedParserDict(
                {
                    "title": "Azure Synapse Analytics Mitigating",
                    "title_detail": {
                        "type": "text/plain",
                        "language": None,
                        "base": "",
                        "value": "Issue affecting Azure Synapse Analytics",
                    },
                    "summary": "The problem is affecting Azure Synapse Analytics",
                    "summary_detail": {
                        "type": "text/html",
                        "language": None,
                        "base": "",
                        "value": "The problem is affecting Azure Synapse Analytics",
                    },
                    "tags": [
                        {"label": None, "scheme": None, "term": "Azure Synapse Analytics"},
                        {"label": None, "scheme": None, "term": "West Europe"},
                    ],
                }
            ),
            {"West Europe"},
        ),
    ],
)
def test_get_affected_regions(entry: FeedParserDict, expected_result: set[str]) -> None:
    all_regions = sorted(list(AZURE_REGIONS.values()), key=len, reverse=True)
    assert get_affected_regions(all_regions, entry) == expected_result


@mock.patch(
    "cmk.plugins.azure_status.special_agent.agent_azure_status.requests.get",
    mock.Mock(return_value=MockResponse),
)
def test_write_section(capsys: pytest.CaptureFixture[str]) -> None:
    arg_list = ["eastus", "centralus", "northcentralus", "westeurope"]
    args = parse_arguments(arg_list)

    write_section(args)

    captured = capsys.readouterr()
    assert captured.out.rstrip().split("\n") == [
        "<<<azure_status:sep(0)>>>",
        '{"issues": [{"description": "Description of the Azure Key Vault problem", '
        '"region": "Global", "title": "Azure Key Vault issue affecting Azure China"}, '
        '{"description": "Description of the Azure Databricks problem", "region": '
        '"North Central US", "title": "Azure Databricks - North Central US - '
        'Investigating"}, {"description": "Impact Statement: Azure Synapse Analytics '
        'customers  may be experiencing connectivity issues", "region": "West '
        'Europe", "title": "Azure Synapse Analytics Mitigating"}], "link": '
        '"https://status.azure.com/en-us/status/", "regions": ["East US", "Central '
        'US", "North Central US", "West Europe", "Global"]}',
    ]
    assert captured.err == ""
