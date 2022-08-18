#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils.scaleio import ScaleioSection

SECTION = {
    "4e9a44c700000000": {
        "ID": ["4e9a44c700000000"],
        "NAME": ["pool01"],
        "MAX_CAPACITY_IN_KB": ["27.9", "TB", "(28599", "GB)"],
        "UNUSED_CAPACITY_IN_KB": ["15.7", "TB", "(16105", "GB)"],
        "FAILED_CAPACITY_IN_KB": ["123132", "Bytes"],
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
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool_totalrw")]
    assert list(check.discovery_function(parsed_section)) == discovered_services


def test_check_scaleio_storage_pool_item_not_found(
    fix_register: FixRegister,
) -> None:

    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool_totalrw")]
    assert list(check.check_function(item="not_existing_item", params={}, section=SECTION)) == []


def test_check_scaleio_storage_pool_first_check_result_is_ok(
    fix_register: FixRegister,
) -> None:

    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool_totalrw")]
    assert list(check.check_function(item=ITEM, params={}, section=SECTION))[0] == Result(
        state=State.OK,
        summary="Name: pool01",
    )


def test_check_scaleio_storage_pool_check_diskstat_is_run(
    fix_register: FixRegister,
) -> None:

    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool_totalrw")]
    assert check.check_function(item=ITEM, params={}, section=SECTION)
    assert (
        len(list(check.check_function(item=ITEM, params={}, section=SECTION))) == 9
    )  # 1 for the first OK result, 4 results and 4 metrics for the read/write_tp and read/write_ios
