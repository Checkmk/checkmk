#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypeAlias

from . import metrics

Quantity: TypeAlias = (
    str
    | metrics.Constant
    | metrics.WarningOf
    | metrics.CriticalOf
    | metrics.MinimumOf
    | metrics.MaximumOf
    | metrics.Sum
    | metrics.Product
    | metrics.Difference
    | metrics.Fraction
)

Bound: TypeAlias = int | float | Quantity
