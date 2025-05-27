#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any

from cmk.bi.packs import BIAggregationPacks


class MockBIAggregationPack(BIAggregationPacks):
    def __init__(self, config: dict[Any, Any]) -> None:
        super().__init__(Path(""))
        self._load_config(config)

    def load_config(self) -> None:
        pass

    def save_config(self) -> None:
        pass
