#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-untyped-call"


from pathlib import Path
from typing import Any

import pytest

from cmk.special_agents.v0_unstable.misc import DataCache


@pytest.fixture(autouse=True)
def _patch_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


class KeksDose(DataCache):
    @property
    def cache_interval(self) -> int:
        return 5

    def get_validity_from_args(self, *args: Any) -> bool:
        return bool(args[0])

    def get_live_data(self, *args: Any) -> Any:
        return "live data"


def test_datacache_timestamp() -> None:
    tcache = KeksDose(host_name="myhost", agent="agent_smith", key="test")

    assert tcache.cache_timestamp is None  # file doesn't exist yet

    tcache._write_to_cache("")
    assert isinstance(tcache.cache_timestamp, float)


def test_datacache_valid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tcache = KeksDose(host_name="myhost", agent="agent_smith", key="test")
    tcache._write_to_cache("cached data")
    assert tcache.cache_timestamp is not None

    valid_time = tcache.cache_timestamp + tcache.cache_interval - 1
    monkeypatch.setattr("time.time", lambda: valid_time)

    assert tcache._cache_is_valid()
    # regular case
    assert tcache.get_data(True) == "cached data"
    # force live data
    assert tcache.get_data(True, use_cache=False) == "live data"
    # cache is valid, but get_validity_from_args wants live data
    assert tcache.get_data(False) == "live data"
    # now live data should be in the cache file
    assert tcache.get_data(True) == "live data"


def test_datacache_validity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tcache = KeksDose(host_name="myhost", agent="agent_smith", key="test")
    tcache._write_to_cache("cached data")
    assert tcache.cache_timestamp is not None

    invalid_time = tcache.cache_timestamp + tcache.cache_interval + 1
    monkeypatch.setattr("time.time", lambda: invalid_time)

    assert not tcache._cache_is_valid()
    assert tcache.get_data(True) == "live data"
