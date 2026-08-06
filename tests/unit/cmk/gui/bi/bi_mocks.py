#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path
from typing import override

from cmk.bi.packs import BIAggregationPacks
from cmk.bi.type_defs import BIPackConfig


class MockBIAggregationPack(BIAggregationPacks):
    def __init__(self, packs_data: Iterable[BIPackConfig]) -> None:
        super().__init__(Path(""))
        self._cleanup_and_load_packs(packs_data)

    @override
    def load_config(self) -> None:
        pass

    @override
    def save_config(self) -> None:
        pass
