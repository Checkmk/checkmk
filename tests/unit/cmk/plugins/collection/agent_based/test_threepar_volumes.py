#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from collections.abc import Mapping, Sequence

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_volumes import (
    check_threepar_volumes,
    discover_threepar_volumes,
    parse_threepar_volumes,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from tests.unit.checks.checktestlib import mock_item_state

STRING_TABLE = [
    [
        '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":1,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 0,"freeMiB": 10240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
    ]
]
STRING_TABLE_WITHOUT_USER_SPACE = [
    [
        '{"total": 149,"members": [{"id": 0,"name": "admin","deduplicationState": 3,"compressionState": 4,"provisioningType": 1,"copyType": 1,"baseId": 0,"readOnly": false,"state": 1,"failedStates": [],"degradedStates": [],"additionalStates": [],"totalReservedMiB": 10240,"totalUsedMiB": 10240,"sizeMiB": 10240,"wwn": "60002AC000000000000000000002ACF2","nguid": "60002AC0000000000002AC000002ACF2","creationTimeSec": 1702991221,"creationTime8601": "2023-12-19T13:07:01+00:00","usrSpcAllocWarningPct": 0,"usrSpcAllocLimitPct": 0,"policies": {"staleSS": true,"oneHost": false,"zeroDetect": false,"system": true,"caching":true},"userCPG": "SSD_r6","uuid": "360d0cc3-8afe-40e5-8ed4-fdf42fbb27d7","udid": 0,"rcopyStatus": 1,"links": [{"href": "https://172.25.0.201/api/v1/volumes/admin", "rel": "self"},{"href":"https://172.25.0.201/api/v1/volumespacedistribution/admin","rel": "volumeSpaceDistribution"}]}]}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="admin"),
            ],
            id="For every volume that is not a system volume, a Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_3par_volumes(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_threepar_volumes(parse_threepar_volumes(section)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, item, parameters, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            "not_found",
            FILESYSTEM_DEFAULT_PARAMS,
            [],
            id="If the item is not found, there are no results.",
        ),
        pytest.param(
            STRING_TABLE,
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="Everything is OK.",
        ),
        pytest.param(
            STRING_TABLE_WITHOUT_USER_SPACE,
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 10240.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.0)),
                Metric("fs_free", 0.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 100.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.CRIT,
                    summary="Used: 100.00% - 10.0 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.5917133490073674),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +606 KiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.5917133490073674),
                Result(state=State.OK, summary="Time left until disk full: 0 seconds"),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC000000000000000000002ACF2"),
                Metric("fs_provisioning", 10737418240.0),
            ],
            id="StringTable without userSpace key.",
        ),
        pytest.param(
            [
                [
                    '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":1,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 8240,"freeMiB": 2000},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
                ]
            ],
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 8240.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 2000.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 80.46875, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.WARN,
                    summary="Used: 80.47% - 8.05 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.47614433552936597),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +488 KiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.47614433552936597),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="If the used space is above the WARN level, the check result is WARN.",
        ),
        pytest.param(
            [
                [
                    '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":1,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 10000,"freeMiB": 240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
                ]
            ],
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 10000.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 97.65625, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(
                    state=State.CRIT,
                    summary="Used: 97.66% - 9.77 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.5778450673900072),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +592 KiB"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +<0.01%"),
                Metric("trend", 0.5778450673900072),
                Result(state=State.OK, summary="Time left until disk full: 1 year 50 days"),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="If the used space is above the CRIT level, the check result is CRIT.",
        ),
        pytest.param(
            [
                [
                    '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":2,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 0,"freeMiB": 10240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
                ]
            ],
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(
                    state=State.WARN, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"
                ),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="The state of the volume is WARN.",
        ),
        pytest.param(
            [
                [
                    '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":3,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 0,"freeMiB": 10240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
                ]
            ],
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(
                    state=State.CRIT, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"
                ),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="The state of the volume is CRIT.",
        ),
        pytest.param(
            [
                [
                    '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":1,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 0,"freeMiB": 10240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false}}]}'
                ]
            ],
            "admin",
            FILESYSTEM_DEFAULT_PARAMS,
            [
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, 10240.00)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Metric("growth", 0.0),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
                Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
                Metric("trend", 0.0),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="If information about the capacity efficiency of the volume is not present, no results for it are created.",
        ),
    ],
)
def test_check_3par_volumes(
    section: StringTable,
    item: str,
    parameters: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    with (
        time_machine.travel(datetime.datetime.fromisoformat("2022-07-11 07:00:00Z")),
        mock_item_state((162312321.0, 0.0)),
    ):
        assert (
            list(
                check_threepar_volumes(
                    item=item,
                    params=parameters,
                    section=parse_threepar_volumes(section),
                )
            )
            == expected_check_result
        )
