#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

__all__ = ["MetricName", "MetricTuple"]


MetricName = str


@dataclasses.dataclass(frozen=True, kw_only=True)
class MetricTuple:
    name: MetricName
    value: float
    warn: float | None
    crit: float | None
    min_: float | None
    max_: float | None
    warn_lower: float | None = None
    crit_lower: float | None = None
