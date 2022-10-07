#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "0"]]


@pytest.fixture(name="check")
def _fortigate_sync_status_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("fortigate_sync_status")]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service()],
            id="If the length of the input is more than 1, a Service with no item is discovered.",
        ),
        pytest.param(
            [
                ["FW-VPN-RZ1", "1"],
            ],
            [],
            id="If there is only one item in the input, nothing is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_vxvm_multipath(
    check: CheckPlugin,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(check.discovery_function(section)) == expected_discovery_result


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.CRIT, summary="FW-VPN-RZ2: unsynchronized"),
            ],
            id="If one of the items has an 'unsynchronized' status, the check state is CRIT.",
        ),
        pytest.param(
            [["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "1"]],
            [
                Result(state=State.OK, summary="FW-VPN-RZ1: synchronized"),
                Result(state=State.OK, summary="FW-VPN-RZ2: synchronized"),
            ],
            id="If both items have a 'synchronized' status, the check state is OK.",
        ),
        pytest.param(
            [],
            [],
            id="If the input section is empty, there are no results.",
        ),
    ],
)
def test_check_fortigate_sync_status(
    check: CheckPlugin,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check.check_function(
                item="",
                params={},
                section=section,
            )
        )
        == expected_check_result
    )


def test_check_fortigate_sync_status_with_unknown_status(
    check: CheckPlugin,
) -> None:
    with pytest.raises(KeyError):
        assert list(
            check.check_function(
                item="",
                params={},
                section=[["FW-VPN-RZ1", "1"], ["FW-VPN-RZ2", "3"]],
            )
        )
