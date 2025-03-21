#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.windows.agent_based import win_dhcp_pools as wdp


@pytest.mark.parametrize(
    "string_table,expected_check_result",
    [
        pytest.param(
            [
                ["Subnet", "=", "127.0.0.1."],
                ["No.", "of", "Addresses", "in", "use", "=", "8."],
                ["No.", "of", "free", "Addresses", "=", "10."],
                ["No.", "of", "pending", "offers", "=", "0."],
            ],
            [
                Result(state=State.OK, summary="Free leases: 10"),
                Result(state=State.OK, summary="55.56%"),
                Metric("free_dhcp_leases", 10.0, boundaries=(0.0, 18.0)),
                Result(state=State.OK, summary="Used leases: 8"),
                Result(state=State.OK, summary="44.44%"),
                Metric("used_dhcp_leases", 8.0, boundaries=(0.0, 18.0)),
                Result(state=State.OK, summary="Pending leases: 0"),
                Result(state=State.OK, summary="0%"),
                Metric("pending_dhcp_leases", 0.0, boundaries=(0.0, 18.0)),
                Result(
                    state=State.OK,
                    summary="Values are averaged",
                    details=(
                        "All values are averaged, as the Windows DHCP plug-in collects statistics, "
                        "not real-time measurements"
                    ),
                ),
            ],
            id="Check results of a used Windows DHCP pool",
        ),
    ],
)
def test_check_win_dhcp_pools(
    string_table: StringTable,
    expected_check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(wdp.check_win_dhcp_pools("127.0.0.1", {}, wdp.parse_win_dhcp_pools(string_table)))
        == expected_check_result
    )
