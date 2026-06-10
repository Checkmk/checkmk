#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class TimeRange:
    start: int
    end: int
    step: int


@dataclass(frozen=True, kw_only=True)
class CommonOptions:
    time_range: TimeRange


class ConsolidationFunction(enum.StrEnum):
    MIN = "min"
    MAX = "max"
    AVERAGE = "average"
