#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# Helper classes for Predictive Levels in Checkmk.
# Checkmk documentation: https://docs.checkmk.com/master/en/predictive_monitoring.html

PREDICTIVE_LEVEL_DEFAULT_HORIZON: Final = 90  # Default horizon in days for predictive levels


class LevelType(StrEnum):
    NO_LEVELS = "No levels"
    FIXED_LEVELS = "Fixed levels"
    PREDICTIVE_LEVELS = "Predictive levels (only on CMC)"


class PredictionPeriod(StrEnum):
    WEEKLY = "Day of the week (1-7, 1 is Monday)"
    MONTHLY = "Day of the month (1-31)"
    HOURLY = "Hour of the day (0-23)"
    MINUTELY = "Minute of the hour (0-59)"


class PredictionPeriodShort(StrEnum):
    WEEKLY = "Day of the week"
    MONTHLY = "Day of the month"
    HOURLY = "Hour of the day"
    MINUTELY = "Minute of the hour"


class PredictiveLevelType(StrEnum):
    ABSOLUTE = "Absolute difference from prediction"
    RELATIVE = "Relative difference from prediction"
    STANDARD_DEVIATION = "In relation to standard deviation"


class PredictiveLevelTypeShort(StrEnum):
    ABSOLUTE = "Absolute difference"
    RELATIVE = "Relative difference"
    STANDARD_DEVIATION = "Standard deviation difference"


class BoundType(StrEnum):
    DYNAMIC_UPPER = "Dynamic levels - upper bound"
    DYNAMIC_LOWER = "Dynamic levels - lower bound"
    LIMIT_DYNAMIC_UPPER = "Limit for upper bound dynamic levels"
    RELATIVE = "Level definition in relation to the predicted value"


@dataclass
class BoundLevels:
    warning: int | float
    critical: int | float


@dataclass
class PredictiveLevels:
    period: PredictionPeriod | PredictionPeriodShort = PredictionPeriodShort.WEEKLY
    horizon_days: int = PREDICTIVE_LEVEL_DEFAULT_HORIZON
    upper_level_type: PredictiveLevelType | PredictiveLevelTypeShort | None = (
        PredictiveLevelTypeShort.ABSOLUTE
    )
    lower_level_type: PredictiveLevelType | PredictiveLevelTypeShort | None = (
        PredictiveLevelTypeShort.ABSOLUTE
    )
    relative_level_type: PredictiveLevelType | PredictiveLevelTypeShort | None = (
        PredictiveLevelTypeShort.ABSOLUTE
    )
    upper_bound: BoundLevels | None = None
    lower_bound: BoundLevels | None = None
    relative_bound: BoundLevels | None = None
    upper_bound_limit: BoundLevels | None = None
    fixed_limits: BoundLevels | None = None

    def get_checked_values(self) -> list[str]:
        """Return list of values to be checked in tests."""
        res = [
            f"{self.period.value}",
            f"{self.horizon_days}",
        ]

        match self.relative_level_type:
            case PredictiveLevelTypeShort.ABSOLUTE:
                res.append("Absolute difference")
            case PredictiveLevelTypeShort.RELATIVE:
                res.append("Relative difference")
            case PredictiveLevelTypeShort.STANDARD_DEVIATION:
                res.append("Standard deviation difference")

        if self.upper_bound:
            res.append(BoundType.DYNAMIC_UPPER.value + "")
            res.extend(
                [
                    f"{self.upper_bound.warning}",
                    f"{self.upper_bound.critical}",
                ]
            )
        if self.lower_bound:
            res.append(BoundType.DYNAMIC_LOWER.value + "")
            res.extend(
                [
                    f"{self.lower_bound.warning}",
                    f"{self.lower_bound.critical}",
                ]
            )
        if self.relative_bound:
            res.append(f"{BoundType.RELATIVE.value}")
            res.extend(
                [
                    f"{self.relative_bound.warning}",
                    f"{self.relative_bound.critical}",
                ]
            )
            res.append("Fixed limits")
            if self.fixed_limits:
                res.extend(
                    [
                        f"{self.fixed_limits.warning}",
                        f"{self.fixed_limits.critical}",
                    ]
                )
            else:
                res.append("(unset)")
        if self.upper_bound_limit:
            res.append(f"{BoundType.LIMIT_DYNAMIC_UPPER.value}")
            res.extend(
                [
                    f"{self.upper_bound_limit.warning}",
                    f"{self.upper_bound_limit.critical}",
                ]
            )
        return res
