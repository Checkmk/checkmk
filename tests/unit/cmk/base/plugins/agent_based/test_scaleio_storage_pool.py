#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.scaleio_storage_pool import (
    _check_scaleio_storage_pool,
    discover_scaleio_storage_pool,
    parse_scaleio_storage_pool,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.base.plugins.agent_based.utils.scaleio import ScaleioSection

SECTION = {
    "4e9a44c700000000": {
        "ID": ["4e9a44c700000000"],
        "NAME": ["pool01"],
        "MAX_CAPACITY_IN_KB": ["27.9", "TB", "(28599", "GB)"],
        "UNUSED_CAPACITY_IN_KB": ["15.7", "TB", "(16105", "GB)"],
        "FAILED_CAPACITY_IN_KB": ["2311212", "Bytes"],
        "TOTAL_READ_BWC": [
            "7",
            "IOPS",
            "33.2",
            "KB",
            "(33996",
            "Bytes)",
            "per-second",
        ],
        "TOTAL_WRITE_BWC": [
            "63",
            "IOPS",
            "219.6",
            "KB",
            "(224870",
            "Bytes)",
            "per-second",
        ],
        "REBALANCE_READ_BWC": ["0", "IOPS", "0", "Bytes", "per-second"],
        "REBALANCE_WRITE_BWC": ["0", "IOPS", "0", "Bytes", "per-second"],
    }
}

ITEM = "4e9a44c700000000"


@pytest.mark.parametrize(
    "string_table, parsed_section",
    [
        pytest.param(
            [
                ["aardvark", "b"],
                ["STORAGE_POOL", "4e9a44c700000000:"],
                ["ID", "4e9a44c700000000"],
                ["NAME", "pool01"],
                ["STORAGE_POOL", "BANANA"],
                ["ID", "BANANA"],
                ["NAME", "pool02"],
            ],
            {
                "4e9a44c700000000": {
                    "ID": ["4e9a44c700000000"],
                    "NAME": ["pool01"],
                },
                "BANANA": {
                    "ID": ["BANANA"],
                    "NAME": ["pool02"],
                },
            },
            id="If the storage section is present in the string_table, a mapping with the storage ID as the item and with the storage info as the value is returned",
        ),
        pytest.param(
            [
                ["VOLUME", "4e9a44c700000000:"],
                ["ID", "4e9a44c700000000"],
                ["NAME", "pool01"],
            ],
            {},
            id="If the storage section is not present in the info, an empty mapping is returned",
        ),
    ],
)
def test_parse_scaleio(
    string_table: StringTable,
    parsed_section: ScaleioSection,
) -> None:
    assert parse_scaleio_storage_pool(string_table) == parsed_section


@pytest.mark.parametrize(
    "parsed_section, discovered_services",
    [
        pytest.param(
            {
                "4e9a44c700000000": {
                    "ID": ["4e9a44c700000000"],
                    "NAME": ["pool01"],
                }
            },
            [Service(item="4e9a44c700000000")],
            id="A service is created for each storage pool that is present in the parsed section",
        ),
        pytest.param(
            {},
            [],
            id="If no storage pool is present in the parsed section, no services are discovered",
        ),
    ],
)
def test_inventory_scaleio_storage_pool(
    parsed_section: ScaleioSection,
    discovered_services: Sequence[Service],
) -> None:
    assert list(discover_scaleio_storage_pool(parsed_section)) == discovered_services


def test_check_scaleio_storage_pool_with_failed_capacity() -> None:
    check_result = list(
        _check_scaleio_storage_pool(
            item=ITEM,
            params=FILESYSTEM_DEFAULT_PARAMS,
            section=SECTION,
            value_store={"4e9a44c700000000.delta": (1660684225.0453863, 12792627.2)},
        )
    )
    assert check_result[-1] == Result(state=State.CRIT, summary="Failed Capacity: 2.20 MiB")


def test_check_scaleio_storage_pool() -> None:
    check_result = list(
        _check_scaleio_storage_pool(
            item=ITEM,
            params=FILESYSTEM_DEFAULT_PARAMS,
            section=SECTION,
            value_store={"4e9a44c700000000.delta": (1660684225.0453863, 12792627.2)},
        )
    )
    assert check_result[3] == Result(state=State.OK, summary="Used: 43.73% - 12.2 TiB of 27.9 TiB")
