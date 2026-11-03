#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric
from cmk.plugins.palo_alto.agent_based.palo_alto_sessions import check_palo_alto_sessions


def test_total_sessions_metric_carries_levels_scaled_to_supported_sessions() -> None:
    section = [["262142", "6785", "4432", "2337", "13", "0"]]

    results = list(check_palo_alto_sessions({"levels_sessions_used": (60, 70)}, section))

    assert results[1] == Metric(
        "total_active_sessions",
        6785.0,
        levels=(157285.2, 183499.4),
        boundaries=(0.0, 262142.0),
    )


def test_total_sessions_metric_has_no_levels_without_supported_sessions() -> None:
    section = [["0", "5", "3", "2", "0", "0"]]

    results = list(check_palo_alto_sessions({"levels_sessions_used": (60, 70)}, section))

    assert results[1] == Metric("total_active_sessions", 5.0)
