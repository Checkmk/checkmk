#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, State
from cmk.plugins.collection.agent_based.mobileiron_section import parse_mobileiron_statistics
from cmk.plugins.collection.agent_based.mobileiron_statistics import check_mobileiron_sourcehost
from cmk.plugins.lib.mobileiron import SourceHostSection

DEVICE_DATA = parse_mobileiron_statistics([['{"non_compliant": 12, "total_count": 22}']])


@pytest.mark.parametrize(
    "params, section, expected_results",
    [
        (
            {"non_compliant_summary_levels": (10, 20)},
            DEVICE_DATA,
            (
                Metric("mobileiron_devices_total", 22.0),
                Metric("mobileiron_non_compliant", 12.0),
                Result(
                    state=State.CRIT,
                    summary="Non-compliant devices: 54.55% (warn/crit at 10.00%/20.00%)",
                ),
                Metric(
                    "mobileiron_non_compliant_summary",
                    54.54545454545454,
                    levels=(10.0, 20.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Non-compliant: 12"),
                Result(state=State.OK, summary="Total: 22"),
            ),
        ),
        (
            {"non_compliant_summary_levels": (50, 60)},
            DEVICE_DATA,
            (
                Metric("mobileiron_devices_total", 22.0),
                Metric("mobileiron_non_compliant", 12.0),
                Result(
                    state=State.WARN,
                    summary="Non-compliant devices: 54.55% (warn/crit at 50.00%/60.00%)",
                ),
                Metric(
                    "mobileiron_non_compliant_summary",
                    54.54545454545454,
                    levels=(50.0, 60.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Non-compliant: 12"),
                Result(state=State.OK, summary="Total: 22"),
            ),
        ),
    ],
)
def test_check_mobileiron_sourcehost(
    params: Mapping[str, Any], section: SourceHostSection, expected_results: CheckResult
) -> None:
    results = tuple(check_mobileiron_sourcehost(params, section))
    assert results == expected_results
