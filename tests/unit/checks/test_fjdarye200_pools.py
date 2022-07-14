#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import namedtuple
from typing import Any, Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks

PoolEntry = namedtuple(  # pylint: disable=collections-namedtuple-call
    "PoolEntry",
    ["capacity", "usage", "available"],
)


@pytest.mark.parametrize(
    "info, parse_result",
    [
        pytest.param(
            [[["0", "117190584", "105269493"]]],
            {"0": PoolEntry(capacity=117190584, usage=105269493, available=11921091)},
            id="The input is parsed into a dictionary and contains the id of the pool, the capacity, the usage and the available space.",
        ),
        pytest.param(
            [],
            None,
            id="If the input is empty, nothing is parsed.",
        ),
    ],
)
def test_parse_fjdarye200_pools(
    info: StringTable,
    parse_result: Mapping[str, PoolEntry],
    fix_register: FixRegister,
) -> None:
    check = fix_register.snmp_sections[SectionName("fjdarye200_pools")]
    assert check.parse_function(info) == parse_result


@pytest.mark.parametrize(
    "item, entry, params",
    [
        pytest.param(
            "0",
            {"0": PoolEntry(capacity=117190584, usage=111331055, available=5859529)},
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
                "trend_range": 24,
                "trend_perfdata": True,
            },
            id="Checking if the check function is being called.",
        ),
    ],
)
def test_check_fjdarye200_pools(
    item: str,
    entry: Mapping[str, PoolEntry],
    params: Mapping[str, Any],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("fjdarye200_pools")]
    assert list(check.check_function(item=item, params=params, section=entry))


@pytest.mark.parametrize(
    "item, entry, params, check_result",
    [
        pytest.param(
            "1",
            {"0": PoolEntry(capacity=117190584, usage=111331055, available=5859529)},
            {
                "levels": (80.0, 90.0),
                "magic_normsize": 20,
                "levels_low": (50.0, 60.0),
                "show_levels": "onmagic",
                "inodes_levels": (10.0, 5.0),
                "show_inodes": "onlow",
                "show_reserved": False,
                "trend_range": 24,
                "trend_perfdata": True,
            },
            [],
            id="If the item is not found, no result is returned. This will lead to a UNKNOWN state on the service.",
        ),
    ],
)
def test_check_fjdarye200_pools_no_item_found(
    item: str,
    entry: Mapping[str, PoolEntry],
    params: Mapping[str, Any],
    check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("fjdarye200_pools")]
    assert list(check.check_function(item=item, params=params, section=entry)) == check_result
