#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]

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
                (0, 'free: 10 leases (55.6%)', [('free_dhcp_leases', 10, None, None, 0, 18)]),
                (0, 'used: 8 leases (44.4%)', [('used_dhcp_leases', 8, None, None, 0, 18)]),
                (0, '0 leases pending', [('pending_dhcp_leases', 0, None, None, 0, 18)]),
            ],
            id="Check results of a used Windows DHCP pool",
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_win_dhcp_pools(
    section: StringTable,
    expected_check_result,
) -> None:
    check = Check("win_dhcp_pools")
    assert (list(check.run_check("127.0.0.1", {}, section)) == expected_check_result)
