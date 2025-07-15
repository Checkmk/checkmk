#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from pathlib import Path
from typing import Any

from cmk.plugins.gerrit.lib.shared_typing import SectionCollector, Sections
from cmk.special_agents.v0_unstable.misc import DataCache
from cmk.utils.paths import tmp_dir


class VersionCache(DataCache):
    def __init__(
        self, *, collector: SectionCollector, interval: float, directory: Path | None = None
    ) -> None:
        super().__init__(
            cache_file_dir=directory or (tmp_dir / "agents"),
            cache_file_name="gerrit_version",
        )
        self._collector = collector
        self._interval = interval

    @property
    def cache_interval(self) -> int:
        return datetime.timedelta(seconds=self._interval).seconds

    def get_validity_from_args(self, *args: Any) -> bool:
        return True

    def get_live_data(self, *args: Any) -> Any:
        return self._collector.collect()

    def get_sections(self) -> Sections:
        return super().get_data()
