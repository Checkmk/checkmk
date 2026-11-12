#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import MetricNamesCache
from cmk.plugins.azure_v2.special_agent.azure_api_client import BaseAsyncApiClient

_NOW = 1_794_484_800.0
_HOUR = 3600.0
_RESOURCE_ID = "/subscriptions/sub123456/resourceGroups/rg/providers/Microsoft.Web/sites/app"


def _api_client(*names: str) -> AsyncMock:
    api_client = AsyncMock(spec=BaseAsyncApiClient)
    api_client.request_async.side_effect = [[{"name": {"value": name}}] for name in names]
    return api_client


async def _names_at(now: float, api_client: AsyncMock, *, use_cache: bool = True) -> Sequence[str]:
    cache = MetricNamesCache(
        subscription="sub123456",
        resource_type="Microsoft.Web/sites",
        cache_id="azure_host",
        clock=lambda: now,
    )
    names: Sequence[str] = await cache.get_data(api_client, _RESOURCE_ID, use_cache=use_cache)
    return names


def _overwrite_stored_files(storage_path: Path, content: str) -> None:
    stored_files = [path for path in storage_path.rglob("*") if path.is_file()]
    if not stored_files:
        raise AssertionError("The cache stored nothing to overwrite")
    for path in stored_files:
        path.write_text(content)


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_names_within_a_day_come_from_the_cache() -> None:
    api_client = _api_client("first", "second")
    await _names_at(_NOW, api_client)

    names = await _names_at(_NOW + 23 * _HOUR, api_client)

    assert names == ["first"]


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_names_older_than_a_day_are_fetched_again() -> None:
    api_client = _api_client("first", "second")
    await _names_at(_NOW, api_client)

    names = await _names_at(_NOW + 25 * _HOUR, api_client)

    assert names == ["second"]


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_cache_written_in_the_future_is_ignored() -> None:
    api_client = _api_client("first", "second")
    await _names_at(_NOW, api_client)

    names = await _names_at(_NOW - _HOUR, api_client)

    assert names == ["second"]


@pytest.mark.usefixtures("storage_path")
@pytest.mark.asyncio
async def test_names_are_fetched_when_the_cache_is_skipped() -> None:
    api_client = _api_client("first", "second")
    await _names_at(_NOW, api_client)

    names = await _names_at(_NOW + _HOUR, api_client, use_cache=False)

    assert names == ["second"]


@pytest.mark.parametrize(
    "raw_content",
    [
        pytest.param("no timestamp line", id="corrupted storage"),
        pytest.param(f"{_NOW}\nnot json", id="content is not JSON"),
    ],
)
@pytest.mark.asyncio
async def test_unreadable_cache_is_replaced_by_live_names(
    raw_content: str, storage_path: Path
) -> None:
    api_client = _api_client("first", "second")
    await _names_at(_NOW, api_client)
    _overwrite_stored_files(storage_path, raw_content)

    names = await _names_at(_NOW + _HOUR, api_client)

    assert names == ["second"]
