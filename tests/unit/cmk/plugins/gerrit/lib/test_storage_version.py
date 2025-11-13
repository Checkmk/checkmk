#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import dataclasses
from pathlib import Path

import pytest

from cmk.plugins.gerrit.lib.schema import VersionInfo
from cmk.plugins.gerrit.lib.storage import VersionCache


@pytest.mark.parametrize(
    "ttl, n_times, expected",
    [
        pytest.param(600, 2, 1, id="cache is used"),
        pytest.param(600, 100, 1, id="cache is used many times"),
        pytest.param(0, 2, 2, id="cache is not used"),
    ],
)
def test_version_cache(tmp_path: Path, ttl: int, n_times: int, expected: int) -> None:
    collector = _VersionCollectorSpy()
    cache = VersionCache(collector=collector, interval=ttl, directory=tmp_path)

    for _ in range(n_times):
        cache.get_data()

    assert collector.number_of_times_data_was_fetched == expected


@dataclasses.dataclass
class _VersionCollectorSpy:
    number_of_times_data_was_fetched: int = 0

    def collect(self) -> VersionInfo:
        self.number_of_times_data_was_fetched += 1
        return {
            "current": "1.2.3",
            "latest": {"major": "2.0.0", "minor": "1.3.0", "patch": "1.2.4"},
        }
