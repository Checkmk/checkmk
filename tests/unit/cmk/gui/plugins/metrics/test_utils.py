#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.metrics import utils


@pytest.mark.parametrize(
    "check_command, expected",
    [
        pytest.param(
            "check-mk-custom!foobar",
            "check-mk-custom",
            id="custom-foobar",
        ),
        pytest.param(
            "check-mk-custom!check_ping",
            "check_ping",
            id="custom-check_ping",
        ),
        pytest.param(
            "check-mk-custom!./check_ping",
            "check_ping",
            id="custom-check_ping-2",
        ),
    ],
)
def test__parse_check_command(check_command: str, expected: str) -> None:
    assert utils._parse_check_command(check_command) == expected
