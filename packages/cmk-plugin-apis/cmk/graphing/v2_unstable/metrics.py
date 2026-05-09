#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from dataclasses import dataclass

from cmk.graphing.v1.metrics import AutoPrecision as AutoPrecision
from cmk.graphing.v1.metrics import Color as Color
from cmk.graphing.v1.metrics import Constant as Constant
from cmk.graphing.v1.metrics import CriticalOf as CriticalOf
from cmk.graphing.v1.metrics import DecimalNotation as DecimalNotation
from cmk.graphing.v1.metrics import Difference as Difference
from cmk.graphing.v1.metrics import (
    EngineeringScientificNotation as EngineeringScientificNotation,
)
from cmk.graphing.v1.metrics import Fraction as Fraction
from cmk.graphing.v1.metrics import IECNotation as IECNotation
from cmk.graphing.v1.metrics import MaximumOf as MaximumOf
from cmk.graphing.v1.metrics import Metric as Metric
from cmk.graphing.v1.metrics import MinimumOf as MinimumOf
from cmk.graphing.v1.metrics import Product as Product
from cmk.graphing.v1.metrics import SINotation as SINotation
from cmk.graphing.v1.metrics import (
    StandardScientificNotation as StandardScientificNotation,
)
from cmk.graphing.v1.metrics import StrictPrecision as StrictPrecision
from cmk.graphing.v1.metrics import Sum as Sum
from cmk.graphing.v1.metrics import TimeNotation as TimeNotation
from cmk.graphing.v1.metrics import Unit as Unit
from cmk.graphing.v1.metrics import WarningOf as WarningOf

__all__ = [
    "AutoPrecision",
    "Color",
    "Constant",
    "CriticalOf",
    "DecimalNotation",
    "Difference",
    "EngineeringScientificNotation",
    "Fraction",
    "IECNotation",
    "LowerCriticalOf",
    "LowerWarningOf",
    "MaximumOf",
    "Metric",
    "MinimumOf",
    "Product",
    "SINotation",
    "StandardScientificNotation",
    "StrictPrecision",
    "Sum",
    "TimeNotation",
    "Unit",
    "WarningOf",
]


@dataclass(frozen=True)
class LowerWarningOf(WarningOf):
    """
    Extracts the lower warning level of a metric by its name. It can be used within other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric

    Example:

        >>> LowerWarningOf("metric-name")
        LowerWarningOf(metric_name='metric-name')
    """


@dataclass(frozen=True)
class LowerCriticalOf(CriticalOf):
    """
    Extracts the lower critical level of a metric by its name. It can be used within other metric
    operations, perfometers or graphs.

    Args:
        metric_name: Name of a metric

    Example:

        >>> LowerCriticalOf("metric-name")
        LowerCriticalOf(metric_name='metric-name')
    """
