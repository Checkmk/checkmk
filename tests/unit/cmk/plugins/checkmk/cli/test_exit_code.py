#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.exit_code import state_exit_code


@pytest.mark.parametrize(
    ["state", "expected"],
    [
        (0, CLIExitCode.SUCCESS),
        (1, CLIExitCode.FAILURE),
        (2, CLIExitCode.ERROR),
        (3, CLIExitCode.UNKNOWN),
        (4, CLIExitCode.UNKNOWN),
        (-1, CLIExitCode.UNKNOWN),
        (127, CLIExitCode.UNKNOWN),
    ],
)
def test_a_state_exits_with_its_monitoring_meaning(state: int, expected: CLIExitCode) -> None:
    assert state_exit_code(state) == expected
