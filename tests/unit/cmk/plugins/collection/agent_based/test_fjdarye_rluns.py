#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.fjdarye_rluns import (
    check_fjdarye_rluns,
    discover_fjdarye_rluns,
    FjdaryeRlun,
    parse_fjdarye_rluns,
)


@pytest.mark.parametrize(
    "section, parse_result",
    [
        pytest.param(
            [],
            {},
            id="The raw section is empty, so nothing is parsed",
        ),
        pytest.param(
            [
                [
                    [
                        "0",
                        "\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                        # The value above corresponds to: '0.0.0.160.16.16.0.0.3.0.0.0.0.255.255.255.0.0.64.205.4.0.0.0.0.6.0.0.0.6.0.0.0.0.0.0.1.32.64.64.15.1.1.2.50.0.0.0.2.0.0.1'
                    ],
                ],
                [],
                [],
            ],
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            id="Transforms the string table into a mapping containing the index of the rlun and raw ip",
        ),
    ],
)
def test_parse_fjdarye_rluns(
    section: Sequence[StringTable],
    parse_result: Mapping[str, FjdaryeRlun],
) -> None:
    assert parse_fjdarye_rluns(section) == parse_result


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            [Service(item="0")],
            id="Because the value of the fourth byte is '\xa0'(160) RLUN is present and a service is discovered. The item name is the index of the RLUN.",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\x33\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            [],
            id="RLUN is not present and no service is discovered, because the value of the fourth byte is not '\xa0'(160)",
        ),
    ],
)
def test_discover_fjdarye_rluns(
    section: Mapping[str, FjdaryeRlun],
    discovery_result: DiscoveryResult,
) -> None:
    assert list(discover_fjdarye_rluns(section)) == discovery_result


@pytest.mark.parametrize(
    "section, item, rluns_check_result",
    [
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "2",
            [],
            id="If the item is not in the section, the check result is None",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\x43\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.CRIT, summary="RLUN is not present")],
            id="If the fourth byte is not equal to '\xa0'(160), RLUN is not present and check result state is CRIT",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x08\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.WARN, summary="RLUN is rebuilding")],
            id="If the third byte is equal to '\x08'(8), RLUN is rebuilding and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x07\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.WARN, summary="RLUN copyback in progress")],
            id="If the third byte is equal to '\x07'(7), RLUN copyback is in progress and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x41\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.WARN, summary="RLUN spare is in use")],
            id="If the third byte is equal to '\x41'(65), RLUN spare is in use and result state is WARN",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x42\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.OK, summary="RLUN is in RAID0 state")],
            id="If the third byte is equal to '\x42'(66), RLUN is in RAID0 state and result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x00\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.OK, summary="RLUN is in normal state")],
            id="If the third byte is equal to '\x00'(0), RLUN is in normal state and result state is OK",
        ),
        pytest.param(
            {
                "0": FjdaryeRlun(
                    rlun_index="0",
                    raw_string="\x00\x00\x44\xa0\x10\x10\x00\x00\x03\x00\x00\x00\x00ÿÿÿ\x00\x00@Í\x04\x00\x00\x00\x00\x06\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x01 @@\x0f\x01\x01\x022\x00\x00\x00\x02\x00\x00\x01",
                )
            },
            "0",
            [Result(state=State.CRIT, summary="RLUN in unknown state")],
            id="If RLUN is present and none of the above criteria are met, the RLUN state is uknown and the result state is CRIT",
        ),
    ],
)
def test_check_fjdarye_rluns(
    section: Mapping[str, FjdaryeRlun],
    item: str,
    rluns_check_result: CheckResult,
) -> None:
    assert list(check_fjdarye_rluns(item, section)) == rluns_check_result
