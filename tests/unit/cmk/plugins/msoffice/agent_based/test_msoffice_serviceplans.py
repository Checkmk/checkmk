#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.msoffice.agent_based.msoffice_serviceplans import (
    check_msoffice_serviceplans,
    parse_msoffice_serviceplans,
)


@pytest.mark.parametrize(
    "params, expected_state, expected_levels_info",
    [
        ({}, State.OK, ""),
        ({"levels": (1, 3)}, State.WARN, " (warn/crit at 1/3)"),
        ({"levels": (0, 1)}, State.CRIT, " (warn/crit at 0/1)"),
    ],
)
def test_check_msoffice_serviceplans(
    params: Mapping[str, tuple[float, float]],
    expected_state: State,
    expected_levels_info: str,
) -> None:
    assert list(
        check_msoffice_serviceplans(
            "bundle",
            params,
            parse_msoffice_serviceplans(
                [
                    ["bundle", "plan-success-1", "Success"],
                    ["bundle", "plan-suc", "cess-2", "Success"],
                    ["bundle", "plan-pending-1", "PendingActivation"],
                    ["bundle", "plan-pen", "ding-2", "PendingActivation"],
                ]
            ),
        ),
    ) == [
        Result(state=expected_state, summary=f"Success: 2, Pending: 2{expected_levels_info}"),
        Result(state=State.OK, summary="Pending Services: plan-pending-1, plan-pen ding-2"),
    ]
