#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.modes.check_mk import state_exit_code
from cmk.cli.internal import ExitCode


@pytest.mark.parametrize(
    ["state", "expected"],
    [
        (0, ExitCode.SUCCESS),
        (1, ExitCode.FAILURE),
        (2, ExitCode.ERROR),
        (3, ExitCode.UNKNOWN),
        (4, ExitCode.UNKNOWN),
        (-1, ExitCode.UNKNOWN),
        (127, ExitCode.UNKNOWN),
    ],
)
def test_a_state_exits_with_its_monitoring_meaning(state: int, expected: ExitCode) -> None:
    assert state_exit_code(state) == expected
