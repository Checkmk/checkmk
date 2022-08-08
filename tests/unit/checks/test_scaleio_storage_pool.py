#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS

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
    parsed_section: Mapping[str, Mapping[str, Sequence[str]]],
    discovered_services: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool")]
    assert list(check.discovery_function(parsed_section)) == discovered_services


def test_check_scaleio_storage_pool_with_failed_capacity(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool")]
    check_result = list(
        check.check_function(item=ITEM, params=FILESYSTEM_DEFAULT_PARAMS, section=SECTION)
    )
    assert check_result[-1] == Result(state=State.CRIT, summary="Failed Capacity: 2.20 MiB")


def test_check_scaleio_storage_pool(fix_register: FixRegister) -> None:
    check = fix_register.check_plugins[CheckPluginName("scaleio_storage_pool")]
    check_result = list(
        check.check_function(item=ITEM, params=FILESYSTEM_DEFAULT_PARAMS, section=SECTION)
    )
    assert check_result[0] == Result(state=State.OK, summary="Used: 43.73% - 12.2 TiB of 27.9 TiB")
