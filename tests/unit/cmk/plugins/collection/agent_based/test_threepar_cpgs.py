#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Sequence

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_cpgs import (
    check_threepar_cpgs,
    check_threepar_cpgs_usage,
    discover_threepar_cpgs,
    discover_threepar_cpgs_usage,
    parse_threepar_cpgs,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

from tests.unit.checks.checktestlib import mock_item_state

STRING_TABLE = [
    [
        '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 20261120,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 94976,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 25600,"rawUsedMiB": 30719},"state": 1}]}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service(item="SSD_R6")],
            id="For every disk that a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_threepar_cpgs(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_threepar_cpgs(parse_threepar_cpgs(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            "not_found",
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            STRING_TABLE,
            "SSD_R6",
            [Result(state=State.OK, summary="Normal, 16 VVs")],
            id="If the state of the disk is 1, the check result is OK (Normal) and information about how many VVs are available is displayed.",
        ),
        pytest.param(
            [
                [
                    '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 20261120,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 94976,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 25600,"rawUsedMiB": 30719},"state": 2}]}'
                ]
            ],
            "SSD_R6",
            [Result(state=State.WARN, summary="Degraded, 16 VVs")],
            id="If the state of the disk is 2, the check result is WARN (Degraded) and information about how many VVs are available is displayed.",
        ),
        pytest.param(
            [
                [
                    '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 20261120,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 94976,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 25600,"rawUsedMiB": 30719},"state": 3}]}'
                ]
            ],
            "SSD_R6",
            [Result(state=State.CRIT, summary="Failed, 16 VVs")],
            id="If the state of the disk is 3, the check result is CRIT (Failed) and information about how many VVs are available is displayed.",
        ),
    ],
)
def test_check_3par_cpgs(
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_threepar_cpgs(
                item=item,
                section=parse_threepar_cpgs(section),
            )
        )
        == expected_check_result
    )


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="SSD_R6 SAUsage"),
                Service(item="SSD_R6 SDUsage"),
                Service(item="SSD_R6 UsrUsage"),
            ],
            id="For each disk a Service for SAUsage, SDUsage and UsrUsage is created if they are available.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_threepar_cpgs_usage(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_threepar_cpgs_usage(parse_threepar_cpgs(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            "not_found",
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            [
                [
                    '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 0,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 0,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 0,"rawUsedMiB": 30719},"state": 2}]}'
                ]
            ],
            "SSD_R6 SAUsage",
            [
                Metric(
                    "fs_used",
                    0.0,
                    levels=(83558.39999961853, 94003.19999980927),
                    boundaries=(0.0, 104448.0),
                ),
                Metric("fs_free", 104448.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    0.0,
                    levels=(79.99999999963478, 89.99999999981739),
                    boundaries=(0.0, 100.0),
                ),
                Result(state=State.OK, summary="Used: 0% - 0 B of 102 GiB"),
                Metric("fs_size", 104448.0, boundaries=(0.0, None)),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0),
            ],
            id="If the used space is below the WARN/CRIT levels, the result is OK.",
        ),
        pytest.param(
            [
                [
                    '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 0,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 0,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 37890,"rawUsedMiB": 30719},"state": 2}]}'
                ]
            ],
            "SSD_R6 SDUsage",
            [
                Metric("fs_used", 37890.0, levels=(35840.0, 40320.0), boundaries=(0.0, 44800.0)),
                Metric("fs_free", 6910.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    84.57589285714285,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.WARN,
                    summary="Used: 84.58% - 37.0 GiB of 43.8 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 44800.0, boundaries=(0.0, None)),
                Metric("growth", 2.1894549603407376),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +2.19 MiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 2.1894549603407376),
                Result(state=State.OK, summary="Time left until disk full: 8 years 236 days"),
            ],
            id="If the used space is above the WARN levels, the result is WARN.",
        ),
        pytest.param(
            [
                [
                    '{"total": 1,"members": [{"id": 0,"uuid": "b5611ec3-b459-4cfe-91d8-64b6c074e72b","name": "SSD_R6","numFPVVs": 1,"numTPVVs": 0,"numTDVVs": 15,"UsrUsage": {"totalMiB": 20261120,"rawTotalMiB": 24313343,"usedMiB": 20161120,"rawUsedMiB": 24313343},"SAUsage": {"totalMiB": 104448,"rawTotalMiB": 313344,"usedMiB": 0,"rawUsedMiB": 284928},"SDUsage": {"totalMiB": 44800,"rawTotalMiB": 53760,"usedMiB": 37890,"rawUsedMiB": 30719},"state": 2}]}'
                ]
            ],
            "SSD_R6 UsrUsage",
            [
                Metric(
                    "fs_used",
                    20161120.0,
                    levels=(16208896.0, 18235008.0),
                    boundaries=(0.0, 20261120.0),
                ),
                Metric("fs_free", 100000.0, boundaries=(0.0, None)),
                Metric(
                    "fs_used_percent",
                    99.50644386884832,
                    levels=(80.0, 90.0),
                    boundaries=(0.0, 100.0),
                ),
                Result(
                    state=State.CRIT,
                    summary="Used: 99.51% - 19.2 TiB of 19.3 TiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 20261120.0, boundaries=(0.0, None)),
                Metric("growth", 1165.0003745058023),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +1.14 GiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 1165.0003745058023),
                Result(state=State.OK, summary="Time left until disk full: 85 days 20 hours"),
            ],
            id="If the used space is above the CRIT levels, the result is CRIT.",
        ),
    ],
)
def test_check_3par_cpgs_usage(
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    with (
        time_machine.travel(datetime.datetime.fromisoformat("2022-07-11 07:00:00Z")),
        mock_item_state((162312321.0, 0.0)),
    ):
        assert (
            list(
                check_threepar_cpgs_usage(
                    item=item,
                    params=FILESYSTEM_DEFAULT_PARAMS,
                    section=parse_threepar_cpgs(section),
                )
            )
            == expected_check_result
        )
