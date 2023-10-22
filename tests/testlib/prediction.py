#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


_Levels = tuple[float | None, float | None, float | None, float | None]


class FixedPredictionUpdater:
    def __init__(self, ref_value: float | None, levels: _Levels) -> None:
        self._return_value = ref_value, levels

    def get_predictive_levels(
        self, metric: str, levels_factor: float = 1.0
    ) -> tuple[float | None, _Levels]:
        return self._return_value
