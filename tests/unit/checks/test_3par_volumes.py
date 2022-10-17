#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    [
        '{"total": 19,"members": [{"id": 0,"name": "admin","provisioningType": 1,"state":1,"userSpace": {"reservedMiB": 10240,"rawReservedMiB": 30720,"usedMiB": 0,"freeMiB": 10240},"sizeMiB": 10240,"wwn":"60002AC0000000000000003F000292E7","policies": {"system": false},"capacityEfficiency": {"compaction": 19.54,"deduplication": 1.65,"compression": 2.06}}]}'
    ]
]


@pytest.fixture(name="check")
def _3par_volumes_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("3par_volumes")]


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
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    parse_3par_volumes = fix_register.agent_sections[SectionName("3par_volumes")].parse_function
    assert list(check.discovery_function(parse_3par_volumes(section))) == expected_discovery_result


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
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Dedup: 1.65"),
                Result(state=State.OK, summary="Compact: 19.54"),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="Everything is OK.",
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
                Result(
                    state=State.WARN,
                    summary="Used: 80.47% - 8.05 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_used", 8240.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 2000.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 80.46875, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
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
                Result(
                    state=State.CRIT,
                    summary="Used: 97.66% - 9.77 GiB of 10.0 GiB (warn/crit at 80.00%/90.00% used)",
                ),
                Metric("fs_used", 10000.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 97.65625, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
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
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
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
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
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
                Result(state=State.OK, summary="Used: 0% - 0 B of 10.0 GiB"),
                Metric("fs_used", 0.0, levels=(8192.0, 9216.0), boundaries=(0.0, None)),
                Metric("fs_free", 10240.0, boundaries=(0.0, None)),
                Metric("fs_used_percent", 0.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
                Metric("fs_size", 10240.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Type: FULL, WWN: 60002AC0000000000000003F000292E7"),
                Metric("fs_provisioning", 32212254720.0),
            ],
            id="If information about the capacity efficiency of the volume is not present, no results for it are created.",
        ),
    ],
)
def test_check_3par_volumes(
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    item: str,
    parameters: Mapping[str, tuple[float, float]],
    expected_check_result: Sequence[Result | Metric],
) -> None:
    parse_3par_volumes = fix_register.agent_sections[SectionName("3par_volumes")].parse_function
    assert (
        list(
            check.check_function(
                item=item,
                params=parameters,
                section=parse_3par_volumes(section),
            )
        )
        == expected_check_result
    )
