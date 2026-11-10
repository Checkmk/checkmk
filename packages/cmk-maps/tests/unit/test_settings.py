#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from pydantic import ValidationError

from cmk.maps.backend.core.config import Settings

_TUNABLES = {
    "MAPS_STATE_REFRESH_INTERVAL": "state_refresh_interval",
    "MAPS_CONNECTION_QUERY_TIMEOUT": "connection_query_timeout",
    "MAPS_CONNECTION_POOL_SIZE": "connection_pool_size",
    "MAPS_MULTISITE_CONNECTIONS": "multisite_connections",
    "MAPS_FLOW_MAX_SERVICES_PER_HOST": "flow_map_max_services_per_host",
    "MAPS_FLOW_TOP_AFFECTED_HOSTS": "flow_map_top_affected_hosts",
    "MAPS_FLOW_BULK_SERVICE_CHUNK_SIZE": "flow_map_bulk_service_chunk_size",
    "MAPS_FLOW_BULK_MAX_CONCURRENT_CHUNKS": "flow_map_bulk_max_concurrent_chunks",
    "MAPS_CONNECTION_WARMUP_INTERVAL": "connection_warmup_interval",
    "MAPS_FOLDER_SEARCH_MAX_SERVICES": "folder_search_max_services",
}


@pytest.fixture(name="defaults")
def fixture_defaults(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for key in _TUNABLES:
        monkeypatch.delenv(key, raising=False)
    return Settings()


@pytest.mark.parametrize("value", ["1000000", "-1", "many"])
@pytest.mark.parametrize("key", list(_TUNABLES))
def test_an_unusable_environment_value_falls_back_to_the_default(
    monkeypatch: pytest.MonkeyPatch, defaults: Settings, key: str, value: str
) -> None:
    monkeypatch.setenv(key, value)

    assert getattr(Settings(), _TUNABLES[key]) == getattr(defaults, _TUNABLES[key])


@pytest.mark.parametrize("value", ["1000000", "many"])
def test_an_unusable_environment_value_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, value: str
) -> None:
    monkeypatch.setenv("MAPS_CONNECTION_POOL_SIZE", value)

    with caplog.at_level(logging.WARNING, logger="cmk.maps.backend.core.config"):
        Settings()

    assert "MAPS_CONNECTION_POOL_SIZE" in caplog.text


def test_a_usable_environment_value_is_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAPS_CONNECTION_POOL_SIZE", "7")

    assert Settings().connection_pool_size == 7


@pytest.mark.parametrize("field", list(_TUNABLES.values()))
def test_a_value_out_of_range_is_refused(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({field: 1_000_000})
