#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cmk.licensing.internal import (
    CounterCollectionContext,
    LicenseUsageCounter,
    LicenseUsageCounterName,
)
from cmk.licensing.usage_counters import collect_license_usage_counters


@pytest.fixture
def context() -> CounterCollectionContext:
    return CounterCollectionContext(omd_root=Path(), query_livestatus=lambda _query: [])


@pytest.fixture
def logger() -> MagicMock:
    return MagicMock(spec=logging.Logger)


def test_counters_of_all_plugins_are_collected(
    context: CounterCollectionContext, logger: MagicMock
) -> None:
    plugins = [
        LicenseUsageCounter(
            name="one", collect=lambda _ctx: {"synthetic_tests": 1, "synthetic_kpis": 2}
        ),
        LicenseUsageCounter(name="two", collect=lambda _ctx: {"active_metric_series": 3}),
    ]

    assert collect_license_usage_counters(plugins, context, logger) == {
        "synthetic_tests": 1,
        "synthetic_kpis": 2,
        "active_metric_series": 3,
    }


def test_no_plugins_yield_no_counters(context: CounterCollectionContext, logger: MagicMock) -> None:
    assert collect_license_usage_counters([], context, logger) == {}


def test_failing_plugin_is_logged_and_skipped(
    context: CounterCollectionContext,
    logger: MagicMock,
) -> None:
    exception = ValueError("boom")

    def _raise(_ctx: CounterCollectionContext) -> Mapping[LicenseUsageCounterName, int]:
        raise exception

    plugins = [
        LicenseUsageCounter(name="broken", collect=_raise),
        LicenseUsageCounter(name="working", collect=lambda _ctx: {"active_metric_series": 1}),
    ]

    assert collect_license_usage_counters(plugins, context, logger) == {"active_metric_series": 1}
    logger.exception.assert_called_once()


def test_duplicate_counter_is_logged_and_first_wins(
    context: CounterCollectionContext,
    logger: MagicMock,
) -> None:
    plugins = [
        LicenseUsageCounter(name="one", collect=lambda _ctx: {"active_metric_series": 1}),
        LicenseUsageCounter(
            name="two", collect=lambda _ctx: {"active_metric_series": 2, "synthetic_tests": 3}
        ),
    ]

    assert collect_license_usage_counters(plugins, context, logger) == {
        "active_metric_series": 1,
        "synthetic_tests": 3,
    }
    logger.error.assert_called_once()
