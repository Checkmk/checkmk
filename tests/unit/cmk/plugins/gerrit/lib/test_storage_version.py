#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from pathlib import Path

from cmk.plugins.gerrit.lib.shared_typing import SectionName, Sections
from cmk.plugins.gerrit.lib.storage import VersionCache


def test_version_cache_used(tmp_path: Path) -> None:
    interval = 600.0  # 10 mins
    collector = _VersionCollectorSpy()
    cache = VersionCache(collector=collector, interval=interval, directory=tmp_path)
    cache.get_sections()  # trigger once beforehand

    value = cache.get_sections()
    expected = {"version": {"times": 1}}

    assert value == expected


def test_version_cache_not_used(tmp_path: Path) -> None:
    interval = 0.0
    collector = _VersionCollectorSpy()
    cache = VersionCache(collector=collector, interval=interval, directory=tmp_path)
    cache.get_sections()  # trigger once beforehand

    value = cache.get_sections()
    expected = {"version": {"times": 2}}

    assert value == expected


@dataclasses.dataclass
class _VersionCollectorSpy:
    number_of_times_data_was_fetched: int = 0

    def collect(self) -> Sections:
        self.number_of_times_data_was_fetched += 1
        return {SectionName("version"): {"times": self.number_of_times_data_was_fetched}}
