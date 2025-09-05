#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Configuration classes and constants for tests against rules with predictive and fixed levels."""

from typing import NamedTuple

# Test configuration constants
DEFAULT_HORIZON = 90
DEFAULT_PERIOD = "wday"
DEFAULT_LEVELS = ("absolute", (100.0, 200.0))


class BoundConfig(NamedTuple):
    """Configuration for bound settings."""

    bound: tuple[float, float] | None
    description: str


class LevelConfig(NamedTuple):
    """Configuration for level types."""

    levels: tuple[float, float] | tuple[str, tuple[float, float]]
    description: str
    metric: str


class TestRuleConfig(NamedTuple):
    """Configuration for test rule parameters."""

    period: str
    description: str
    horizon: int = DEFAULT_HORIZON
    bound: tuple[float, float] | None = None


BOUND_CONFIGS = [
    BoundConfig(None, "No bounds"),
    BoundConfig((50.0, 150.0), "With bounds"),
]

LEVEL_CONFIGS = [
    LevelConfig(("absolute", (100.0, 200.0)), "Absolute levels", "read_ios"),
    LevelConfig(("relative", (10.0, 20.0)), "Relative levels", "write_ios"),
    LevelConfig(("stdev", (2.0, 3.0)), "Standard deviation levels", "read_throughput"),
]

# Test data configurations
PERIOD_CONFIGS = [
    TestRuleConfig("wday", "Weekly pattern"),
    TestRuleConfig("day", "Daily pattern"),
    TestRuleConfig("hour", "Hourly pattern"),
    TestRuleConfig("minute", "Minute pattern"),
]
