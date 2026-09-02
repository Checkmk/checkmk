#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.sophos_disk import (
    check_sophos_disk,
    discover_sophos_disk,
    Params,
    parse_sophos_disk,
)


def test_discover_sophos_disk_yields_single_service() -> None:
    assert list(discover_sophos_disk(51)) == [Service()]


@pytest.mark.parametrize(
    "info, params, expected_result",
    [
        pytest.param(
            [[51]],
            {},
            [
                Result(state=State.OK, summary="Disk percentage usage: 51%"),
                Metric("disk_utilization", 51.0),
            ],
            id="no_levels_configured",
        ),
        pytest.param(
            [[39]],
            {"disk_levels": (40, 60)},
            [
                Result(state=State.OK, summary="Disk percentage usage: 39%"),
                Metric("disk_utilization", 39.0, levels=(40.0, 60.0)),
            ],
            id="ok_below_warn",
        ),
        pytest.param(
            [[51]],
            {"disk_levels": (40, 60)},
            [
                Result(
                    state=State.WARN,
                    summary="Disk percentage usage: 51% (warn/crit at 40%/60%)",
                ),
                Metric("disk_utilization", 51.0, levels=(40.0, 60.0)),
            ],
            id="warn_above_warn",
        ),
        pytest.param(
            [[61]],
            {"disk_levels": (40, 60)},
            [
                Result(
                    state=State.CRIT,
                    summary="Disk percentage usage: 61% (warn/crit at 40%/60%)",
                ),
                Metric("disk_utilization", 61.0, levels=(40.0, 60.0)),
            ],
            id="crit_above_crit",
        ),
    ],
)
def test_check_sophos_disk(
    info: StringTable, params: Params, expected_result: Sequence[Result | Metric]
) -> None:
    parsed_info = parse_sophos_disk(info)
    assert parsed_info is not None
    result = list(check_sophos_disk(params, parsed_info))
    assert result == expected_result
