#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "section,expected_check_result",
    [
        pytest.param(
            [
                ["Subnet", "=", "127.0.0.1."],
                ["No.", "of", "Addresses", "in", "use", "=", "8."],
                ["No.", "of", "free", "Addresses", "=", "10."],
                ["No.", "of", "pending", "offers", "=", "0."],
            ],
            [
                Result(state=State.OK, summary="Average free: 10 leases (55.6%)"),
                Metric("free_dhcp_leases", 10.0, boundaries=(0.0, 18.0)),
                Result(state=State.OK, summary="Average used: 8 leases (44.4%)"),
                Metric("used_dhcp_leases", 8.0, boundaries=(0.0, 18.0)),
                Result(state=State.OK, summary="Average 0 leases pending"),
                Metric("pending_dhcp_leases", 0.0, boundaries=(0.0, 18.0)),
            ],
            id="Check results of a used Windows DHCP pool",
        ),
    ],
)
def test_check_win_dhcp_pools(
    fix_register: FixRegister,
    section: StringTable,
    expected_check_result: Sequence[Union[Result, Metric]],
) -> None:
    check = fix_register.check_plugins[CheckPluginName("win_dhcp_pools")]
    assert (
        list(check.check_function(item="127.0.0.1", params={}, section=section))
        == expected_check_result
    )
