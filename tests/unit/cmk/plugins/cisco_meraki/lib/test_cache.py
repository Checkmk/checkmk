#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
from pathlib import Path

import pytest

from cmk.plugins.cisco_meraki.lib.cache import cache_ttl
from cmk.server_side_programs.v1_unstable import Storage


@pytest.fixture
def patch_storage_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


@pytest.mark.usefixtures("patch_storage_path")
class TestCacheTTL:
    @pytest.fixture
    def storage(self) -> Storage:
        return Storage("test_agent", "test_host")

    def test_fetcher_with_args_cache_hit(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda x, y: x + y * random.random())
        assert fn(1, 1) == fn(1, 1)

    def test_fetcher_with_args_cache_miss(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=0)(lambda x, y: x + y * random.random())
        assert fn(1, 1) != fn(1, 1)

    def test_fetcher_with_kwargs_cache_hit(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda x, y: x + y * random.random())
        assert fn(x=1, y=1) == fn(x=1, y=1)

    def test_fetcher_with_kwargs_cache_miss(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=0)(lambda x, y: x + y * random.random())
        assert fn(x=1, y=1) != fn(x=1, y=1)

    def test_mixed_args_kwargs_still_hits(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda x, y: x + y * random.random())
        assert fn(1, y=1) == fn(1, y=1)

    def test_mismatch_args_kwargs_misses(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda x, y: x + y * random.random())
        assert fn(x=1, y=1) != fn(1, 1)

    def test_fetcher_with_no_arguments_cache_hit(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda: random.random())
        assert fn() == fn()

    def test_fetcher_with_no_arguments_cache_miss(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=0)(lambda: random.random())
        assert fn() != fn()

    def test_function_with_unhashable_arguments(self, storage: Storage) -> None:
        fn = cache_ttl(storage, ttl=60)(lambda items: len(items))

        with pytest.raises(ValueError):
            fn({1, 2, 3})

        with pytest.raises(ValueError):
            fn(items={1, 2, 3})

    def test_passing_invalid_ttl(self) -> None:
        with pytest.raises(ValueError):
            cache_ttl(Storage("test_agent", "test_host"), ttl=-1)(lambda n: n)
