#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest

from cmk.plugins.veeam.lib import parse_dotnet_timespan_seconds, parse_iso8601_epoch


@pytest.mark.parametrize(
    "value, expected_epoch",
    [
        pytest.param(
            "2024-02-04T21:40:34.473+03:00",
            datetime.fromisoformat("2024-02-04T21:40:34.473+03:00").timestamp(),
            id="with fractional seconds",
        ),
        pytest.param("garbage", None, id="unparsable"),
    ],
)
def test_parse_iso8601_epoch(value: str, expected_epoch: float | None) -> None:
    assert parse_iso8601_epoch(value) == expected_epoch


@pytest.mark.parametrize(
    "duration, expected_seconds",
    [
        pytest.param("0.00:18:50", 1130.0, id="with leading days"),
        pytest.param("01:20:30", 4830.0, id="without days"),
        pytest.param(
            "1.02:03:04.5000000", (26 * 3600) + (3 * 60) + 4, id="with fractional seconds"
        ),
        pytest.param("garbage", None, id="unparsable"),
    ],
)
def test_parse_dotnet_timespan_seconds(duration: str, expected_seconds: float | None) -> None:
    assert parse_dotnet_timespan_seconds(duration) == expected_seconds
