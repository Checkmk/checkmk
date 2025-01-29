#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence

import pytest
import time_machine

from tests.unit.checks.checktestlib import mock_item_state

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_capacity import (
    check_threepar_capacity,
    discover_threepar_capacity,
    parse_threepar_capacity,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    [
        '{"allCapacity": {"totalMiB": 161120256,"freeMiB": 120660992,"failedCapacityMiB": 0},"FCCapacity": {"totalMiB": 0,"freeMiB": 0,"failedCapacityMiB": 0},"NLCapacity": {"totalMiB": 0,"freeMiB": 0,"failedCapacityMiB": 0},"SSDCapacity": {"totalMiB": 161120256,"freeMiB": 120660992,"failedCapacityMiB": 0}}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="all"),
                Service(item="SSD"),
            ],
            id="For every disk whos total capacity is greater than 0, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_threepar_capacity(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_threepar_capacity(parse_threepar_capacity(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, item, parameters, expected_check_result",
    [
        pytest.param(
            [
                [
                    '{"allCapacity": {"totalMiB": 161120256,"freeMiB": 120660992,"failedCapacityMiB": 0},"FCCapacity": {"totalMiB": 0,"freeMiB": 0,"failedCapacityMiB": 0},"NLCapacity": {"totalMiB": 0,"freeMiB": 0,"failedCapacityMiB": 0},"SSDCapacity": {"totalMiB": 161120256,"freeMiB": 120660992,"failedCapacityMiB": 0}}'
                ]
            ],
            "not_found",
            FILESYSTEM_DEFAULT_PARAMS,
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            [],
            "not_found",
            FILESYSTEM_DEFAULT_PARAMS,
            [],
            id="If the section is empty, there are no results.",
        ),
        pytest.param(
            [
                [
                    '{"allCapacity": {"totalMiB": 161120256,"freeMiB": 120660992,"failedCapacityMiB": 0}}'
                ]
            ],
            "all",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric(
                    "fs_used",
                    40459264.0,
                    levels=(128896204.79999924, 145008230.39999962),
                    boundaries=(0.0, 161120256.0),
                ),
                Metric("fs_free", 120660992.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    25.111221273134028,
                    levels=(79.99999999999953, 89.99999999999976),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 25.11% - 38.6 TiB of 154 TiB"),
                Metric("fs_size", 161120256.0, boundaries=(0.0, None)),
                Metric("growth", 2337.2427533197924),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +2.28 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 2337.2427533197924),
            ],
            id="If the free capacity is above the WARN/CRIT level, the check result is OK.",
        ),
        pytest.param(
            [['{"allCapacity": {"totalMiB": 100,"freeMiB": 19,"failedCapacityMiB": 0}}']],
            "all",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 81.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_free", 19.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 81.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.WARN,
                    summary="Used: 81.00% - 81.0 MiB of 100 MiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 100.0, boundaries=(0.0, None)),
                Metric("growth", 0.004101514958375289),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +4.20 KiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.004101514958375289),
            ],
            id="If the free capacity is below the WARN level, the check result is WARN.",
        ),
        pytest.param(
            [['{"allCapacity": {"totalMiB": 100,"freeMiB": 9,"failedCapacityMiB": 0}}']],
            "all",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 91.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_free", 9.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 91.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.CRIT,
                    summary="Used: 91.00% - 91.0 MiB of 100 MiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 100.0, boundaries=(0.0, None)),
                Metric("growth", 0.004679193121526739),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +4.79 KiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.004679193121526739),
                Result(state=State.OK, summary="Time left until disk full: 5 years 98 days"),
            ],
            id="If the free capacity is below the CRIT level, the check result is CRIT.",
        ),
        pytest.param(
            [['{"allCapacity": {"totalMiB": 100,"freeMiB": 80,"failedCapacityMiB": 3}}']],
            "all",
            dict(FILESYSTEM_DEFAULT_PARAMS) | {"failed_capacity_levels": (2.0, 5.0)},
            [
                Metric("fs_used", 20.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_free", 80.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 20.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 20.00% - 20.0 MiB of 100 MiB"),
                Metric("fs_size", 100.0, boundaries=(0.0, None)),
                Metric("growth", 0.0005776781631514493),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +606 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.0005776781631514493),
                Result(state=State.WARN, summary="3.0 MB failed: 3.00% (warn/crit at 2.00%/5.00%)"),
            ],
            id="If the failed capacity is above the WARN level, the result is WARN.",
        ),
        pytest.param(
            [['{"allCapacity": {"totalMiB": 100,"freeMiB": 80,"failedCapacityMiB": 6}}']],
            "all",
            dict(FILESYSTEM_DEFAULT_PARAMS) | {"failed_capacity_levels": (2.0, 5.0)},
            [
                Metric("fs_used", 20.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_free", 80.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 20.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 20.00% - 20.0 MiB of 100 MiB"),
                Metric("fs_size", 100.0, boundaries=(0.0, None)),
                Metric("growth", 0.0005776781631514493),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +606 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.0005776781631514493),
                Result(state=State.CRIT, summary="6.0 MB failed: 6.00% (warn/crit at 2.00%/5.00%)"),
            ],
            id="If the failed capacity is above the CRIT level, the result is CRIT.",
        ),
    ],
)
def test_check_threepar_capacity(
    section: StringTable,
    item: str,
    parameters: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    with (
        time_machine.travel(datetime.datetime.fromisoformat("2022-07-16 07:00:00Z")),
        mock_item_state((162312321.0, 10.0)),
    ):
        assert (
            list(
                check_threepar_capacity(
                    item=item,
                    params=parameters,
                    section=parse_threepar_capacity(section),
                )
            )
            == expected_check_result
        )
