#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.pulse_secure_log_util import (
    check_pulse_secure_log_util,
    discover_pulse_secure_log_util,
    parse_pulse_secure_log_utils,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([["19"]], [(None, {})]),
    ],
)
def test_discover_pulse_secure_log(
    info: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for pulse_secure_log_util check."""
    parsed = parse_pulse_secure_log_utils(info)
    if parsed is not None:
        result = list(discover_pulse_secure_log_util(parsed))
    else:
        result = []
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            None,
            {},
            [["19"]],
            [
                (
                    0,
                    "Percentage of log file used: 19.00%",
                    [("log_file_utilization", 19, None, None)],
                )
            ],
        ),
    ],
)
def test_check_pulse_secure_log(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for pulse_secure_log_util check."""
    parsed = parse_pulse_secure_log_utils(info)
    result = list(check_pulse_secure_log_util(item, params, parsed))
    assert result == expected_results
