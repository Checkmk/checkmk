#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable

from .checktestlib import Check

Result = tuple[float, str, Sequence[object]]


def test_discover_sophos_disk_yields_single_service() -> None:
    discovered = Check("sophos_disk").run_discovery(51)
    assert isinstance(discovered, Iterator)
    assert list(discovered) == [(None, {})]


@pytest.mark.parametrize(
    "info, params, expected_result",
    [
        pytest.param(
            [[51]],
            {},
            (0, "Disk percentage usage: 51%", [("disk_utilization", 51, None, None)]),
            id="no_levels_configured",
        ),
        pytest.param(
            [[39]],
            {"disk_levels": (40, 60)},
            (0, "Disk percentage usage: 39%", [("disk_utilization", 39, 40.0, 60.0)]),
            id="ok_below_warn",
        ),
        pytest.param(
            [[51]],
            {"disk_levels": (40, 60)},
            (
                1,
                "Disk percentage usage: 51% (warn/crit at 40%/60%)",
                [("disk_utilization", 51, 40.0, 60.0)],
            ),
            id="warn_above_warn",
        ),
        pytest.param(
            [[61]],
            {"disk_levels": (40, 60)},
            (
                2,
                "Disk percentage usage: 61% (warn/crit at 40%/60%)",
                [("disk_utilization", 61, 40.0, 60.0)],
            ),
            id="crit_above_crit",
        ),
    ],
)
def test_check_sophos_disk(
    info: StringTable, params: Mapping[str, object], expected_result: Result
) -> None:
    parsed_info = Check("sophos_disk").run_parse(info)
    result = Check("sophos_disk").run_check(None, params, parsed_info)
    assert result == expected_result
