#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Mapping, Sequence
from unittest.mock import AsyncMock

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    AzureResourceGroup,
    process_usage_details,
    TagsImportPatternOption,
    UniqueHostnamesConfig,
)
from cmk.plugins.azure_v2.special_agent.azure_api_client import (
    ApiError,
    BaseAsyncApiClient,
    RateLimitException,
)

from .lib import fake_azure_subscription

_COLUMNS = [{"name": "CostUSD"}, {"name": "ResourceType"}, {"name": "ResourceGroupName"}]
_RETRY_AFTER = "x-ms-ratelimit-microsoft.costmanagement-entity-retry-after"
_REMAINING = "x-ms-ratelimit-remaining-microsoft.costmanagement-tenant-requests"


def _cost_answer(
    rows: Sequence[Sequence[object]], next_link: str | None = None
) -> Mapping[str, object]:
    properties: dict[str, object] = {"columns": _COLUMNS, "rows": list(rows)}
    if next_link is not None:
        properties["nextLink"] = next_link
    return {"id": "query_id", "name": "query", "properties": properties}


def _api_client(*answers: object) -> AsyncMock:
    api_client = AsyncMock(spec=BaseAsyncApiClient)
    api_client.request_async.side_effect = answers
    api_client.lookup_json_data.side_effect = BaseAsyncApiClient.lookup_json_data
    return api_client


def _rate_limit(headers: Mapping[str, str]) -> RateLimitException:
    return RateLimitException("Rate limit exceeded", context=headers)


_GROUP = AzureResourceGroup(
    {"type": "Microsoft.Resources/resourceGroups", "name": "rg"},
    TagsImportPatternOption.import_all,
    fake_azure_subscription(),
    UniqueHostnamesConfig(),
)


async def _process(api_client: AsyncMock) -> None:
    await process_usage_details(
        api_client,
        fake_azure_subscription(),
        {"rg": _GROUP},
        argparse.Namespace(
            cache_id="azure_host",
            debug=False,
            tag_key_pattern=TagsImportPatternOption.import_all,
            unique_hostnames_config=UniqueHostnamesConfig(),
        ),
    )


def _usage_header(piggytarget: str) -> str:
    return f"<<<<{piggytarget}>>>>\n<<<azure_v2_usagedetails:sep(124)>>>"


def _usage_section(output: str, piggytarget: str) -> str:
    header = _usage_header(piggytarget)
    if header not in output:
        raise AssertionError(f"No usage section for {piggytarget}")
    return output.split(header, 1)[1].split("<<<<", 1)[0]


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_costs_go_to_the_subscription_and_the_resource_group(
    capsys: pytest.CaptureFixture[str],
) -> None:
    await _process(_api_client(_cost_answer([[1.5, "virtualmachines", "rg"]])))

    output = capsys.readouterr().out
    assert '"CostUSD": 1.5' in _usage_section(output, fake_azure_subscription().piggytarget)
    assert '"CostUSD": 1.5' in _usage_section(output, _GROUP.piggytarget)


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_costs_of_all_answer_pages_are_written(capsys: pytest.CaptureFixture[str]) -> None:
    api_client = _api_client(
        _cost_answer([[1.5, "virtualmachines", "rg"]], next_link="https://next"),
        _cost_answer([[2.5, "storageaccounts", "rg"]]),
    )

    await _process(api_client)

    output = capsys.readouterr().out
    assert '"name": "query-0"' in output
    assert '"name": "query-1"' in output


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_answer_without_costs_is_reported_in_agent_info(
    capsys: pytest.CaptureFixture[str],
) -> None:
    await _process(_api_client(_cost_answer([])))

    assert "Usage client: Azure API did not return any usage details" in capsys.readouterr().out


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_offer_without_cost_api_writes_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    await _process(_api_client(ApiError("Cost API is not supported for offer MS-AZR-0145P")))

    assert capsys.readouterr().out == ""


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_failed_cost_query_writes_the_error_and_empty_sections(
    capsys: pytest.CaptureFixture[str],
) -> None:
    await _process(_api_client(ApiError("Internal server error")))

    output = capsys.readouterr().out
    assert "Internal server error" in output
    assert _usage_header(fake_azure_subscription().piggytarget) in output
    assert _usage_header(_GROUP.piggytarget) in output


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({_RETRY_AFTER: "60", _REMAINING: "DefaultQuota:5"}, id="long retry time"),
        pytest.param({_RETRY_AFTER: "1", _REMAINING: "DefaultQuota:0"}, id="no requests left"),
    ],
)
@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_cost_query_gives_up_on_a_hard_rate_limit(
    headers: Mapping[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    await _process(_api_client(_rate_limit(headers)))

    assert "Rate limit exceeded for Microsoft.CostManagement API" in capsys.readouterr().out


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_rate_limit_without_headers_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    await _process(_api_client(_rate_limit({})))

    assert "Rate limit information not available" in capsys.readouterr().out


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_cost_query_is_retried_after_a_short_rate_limit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("cmk.plugins.azure_v2.special_agent.agent_azure_v2.asyncio.sleep", sleep)
    api_client = _api_client(
        _rate_limit({_RETRY_AFTER: "0", _REMAINING: "DefaultQuota:5"}),
        _cost_answer([[1.5, "virtualmachines", "rg"]]),
    )

    await _process(api_client)

    sleep.assert_awaited_once_with(1)
    output = capsys.readouterr().out
    assert '"CostUSD": 1.5' in _usage_section(output, fake_azure_subscription().piggytarget)
