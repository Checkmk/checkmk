#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [
    ["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"],
    ["md36xxf0", "MD36xxf", "6C81F66000C458900000000054331291", "CONNECTED", "A/P", "5", "0820"],
]

STRING_TABLE_WITH_ERROR = [
    ["============"],
    ["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"],
    ["md36xxf0", "MD36xxf", "6C81F66000C458900000000054331291", "CONNECTED", "A/P", "5", "0820"],
]


@pytest.fixture(name="check")
def _vxvm_enclosures_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("vxvm_enclosures")]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="san_vc0"),
                Service(item="md36xxf0"),
            ],
            id="Discovery with section that has no error.",
        ),
        pytest.param(
            STRING_TABLE_WITH_ERROR,
            [
                Service(item="san_vc0"),
                Service(item="md36xxf0"),
            ],
            id="Discovery with section that has an error. Now the check can handle 'bad' input.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    parse_vxvm_enclosures = fix_register.agent_sections[
        SectionName("vxvm_enclosures")
    ].parse_function
    assert (
        list(check.discovery_function(parse_vxvm_enclosures(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "item, section, expected_check_result",
    [
        pytest.param(
            "san_vc0",
            STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status is CONNECTED",
                )
            ],
            id="If the status of the enclosure is CONNECTED, the state is OK.",
        ),
        pytest.param(
            "san_vc0",
            [["san_vc0", "SAN_VC", "02006021c03c", "DISCONNECTED", "IBMSVC-ALUA", "8", "0000"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Status is DISCONNECTED",
                )
            ],
            id="If the status of the enclosure is not CONNECTED, the state is CRIT and the status is indicated.",
        ),
        pytest.param(
            "not_found",
            [["san_vc0", "SAN_VC", "02006021c03c", "CONNECTED", "IBMSVC-ALUA", "8", "0000"]],
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Item not found",
                )
            ],
            id="The item was not found, so the state is UNKNOWN.",
        ),
    ],
)
def test_check_vxvm_enclosures(
    check: CheckPlugin,
    fix_register: FixRegister,
    item: str,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    parse_vxvm_enclosures = fix_register.agent_sections[
        SectionName("vxvm_enclosures")
    ].parse_function
    assert (
        list(
            check.check_function(
                item=item,
                params={},
                section=parse_vxvm_enclosures(section),
            )
        )
        == expected_check_result
    )
