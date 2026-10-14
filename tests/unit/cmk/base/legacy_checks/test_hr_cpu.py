#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence
from typing import Any

import pytest

from cmk.base.legacy_checks.hr_cpu import check_hr_cpu, parse_hr_cpu

from cmk.agent_based.v2 import StringTable


@pytest.mark.parametrize(
    "string_table, expected_results",
    [
        pytest.param(
            [[""]],
            [(3, "Cannot parse processor load of core 0: got '' (expected integer)")],
            id="only_core_empty",
        ),
        pytest.param(
            [["20"], [""]],
            [
                (3, "Cannot parse processor load of core 1: got '' (expected integer)"),
                (0, "Total CPU: 20.00%", [("util", 20.0, 80.0, 90.0, 0, 100)]),
            ],
            id="one_of_two_cores_empty",
        ),
    ],
)
def test_check_hr_cpu_unparsable_processor_load(
    string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    # The device reports an empty hrProcessorLoad value instead of an integer.
    parsed = parse_hr_cpu(string_table)
    assert list(check_hr_cpu(None, {"util": (80.0, 90.0)}, parsed)) == expected_results
