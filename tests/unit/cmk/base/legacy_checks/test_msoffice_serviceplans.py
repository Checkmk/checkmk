#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.legacy_checks.msoffice_serviceplans import (
    check_msoffice_serviceplans,
    parse_msoffice_serviceplans,
)


@pytest.mark.parametrize(
    "params, expected_status, expected_levels_info",
    [
        ({}, 0, ""),
        ({"levels": (1, 3)}, 1, " (warn/crit at 1/3)"),
        ({"levels": (0, 1)}, 2, " (warn/crit at 0/1)"),
    ],
)
def test_check_win_license(
    params: Mapping[str, tuple[float, float]], expected_status: int, expected_levels_info: str
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
        (expected_status, "Success: 2, Pending: 2%s" % expected_levels_info),
        (0, "Pending Services: plan-pending-1, plan-pen ding-2"),
    ]
