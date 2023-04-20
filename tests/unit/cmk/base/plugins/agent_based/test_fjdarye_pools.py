#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import freezegun
import pytest

from tests.unit.checks.checktestlib import mock_item_state

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.fjdarye_pools import (
    check_fjdarye_pools,
    discover_fjdarye_pools,
    FjdaryePoolsSection,
    parse_fjdarye_pools,
    PoolEntry,
)
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_PARAMS


@pytest.mark.parametrize(
    "string_table, parse_result",
    [
        pytest.param(
            [
                [["0", "117190584", "105269493"]],
            ],
            {"0": PoolEntry(capacity=117190584, usage=105269493, available=11921091)},
            id="The input is parsed into a dictionary and contains the id of the pool, the capacity, the usage and the available space.",
        ),
        pytest.param(
            [],
            {},
            id="If the input is empty, nothing is parsed.",
        ),
    ],
)
def test_parse_fjdarye_pools(
    string_table: list[StringTable], parse_result: FjdaryePoolsSection
) -> None:
    assert parse_fjdarye_pools(string_table) == parse_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {
                "0": PoolEntry(capacity=117190584, usage=105269493, available=11921091),
                "1": PoolEntry(capacity=117190584, usage=105269493, available=11921091),
            },
            [Service(item="0"), Service(item="1")],
            id="Services with the pool id as item are discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no services are discovered.",
        ),
    ],
)
def test_discover_fjdarye_pools(
    section: FjdaryePoolsSection, discovery_result: Sequence[Service]
) -> None:
    assert list(discover_fjdarye_pools(section)) == discovery_result


@pytest.mark.parametrize(
    "item, section",
    [
        pytest.param(
            "0",
            {"0": PoolEntry(capacity=117190584, usage=111331055, available=5859529)},
            id="Testing if the check function is being called.",
        ),
    ],
)
def test_check_fjdarye_pools(
    item: str,
    section: FjdaryePoolsSection,
) -> None:
    with freezegun.freeze_time("2022-07-16 07:00:00"), mock_item_state((1596100000, 42)):
        assert list(
            check_fjdarye_pools(item=item, params=FILESYSTEM_DEFAULT_PARAMS, section=section)
        )


@pytest.mark.parametrize(
    "item, section, check_result",
    [
        pytest.param(
            "1",
            {"0": PoolEntry(capacity=117190584, usage=111331055, available=5859529)},
            [],
            id="If the item is not found, no result is returned. This will lead to a UNKNOWN state on the service.",
        ),
    ],
)
def test_check_fjdarye_pools_no_item_found(
    item: str,
    section: FjdaryePoolsSection,
    check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(check_fjdarye_pools(item=item, params=FILESYSTEM_DEFAULT_PARAMS, section=section))
        == check_result
    )
