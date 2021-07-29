#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public Licensv2
# This filis part of Checkmk (https://checkmk.com). It is subject to thterms and
# conditions defined in thfilCOPYING, which is part of this sourccodpackage.

from typing import Any, Mapping, Sequence, Tuple

import pytest

from cmk.base.plugins.agent_based.cisco_vpn_tunnel import Phase, VPNTunnel
from tests.testlib import Check

pytestmark = pytest.mark.checks

_SECTION = {
    "110.173.49.157": VPNTunnel(
        phase_1=Phase(input=57872.0, output=60680.0),
        phase_2=Phase(input=4275671278.0, output=552070119.0),
    ),
    "211.167.210.107": VPNTunnel(
        phase_1=Phase(input=1564.0, output=1600.0),
        phase_2=None,
    ),
    "176.210.155.217": VPNTunnel(
        phase_1=Phase(input=3176.0, output=2424.0),
        phase_2=Phase(input=805509.0, output=996792.0),
    ),
    "62.111.62.165": VPNTunnel(
        phase_1=Phase(input=1828836.0, output=540776.0),
        phase_2=Phase(input=418226309.0, output=2404964353.0),
    ),
    "158.244.78.71": VPNTunnel(
        phase_1=Phase(input=77536.0, output=77632.0),
        phase_2=Phase(input=1445263205.0, output=1124929982.0),
    ),
}


def test_inventory_cisco_vpn_tunnel() -> None:
    assert Check("cisco_vpn_tunnel").run_discovery(_SECTION) == [(ip, {}) for ip in _SECTION]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "110.173.49.157",
            {},
            (
                0,
                "Phase 1: in: 0.00 B/s, out: 0.00 B/s, Phase 2: in: 0.00 B/s, out: 0.00 B/s",
                [("if_in_octets", 0.0), ("if_out_octets", 0.0)],
            ),
            id="standard case",
        ),
        pytest.param(
            "211.167.210.107",
            {},
            (
                0,
                "Phase 1: in: 0.00 B/s, out: 0.00 B/s, Phase 2 missing",
                [("if_in_octets", 0.0), ("if_out_octets", 0.0)],
            ),
            id="phase 2 missing",
        ),
        pytest.param(
            "110.173.49.157",
            {
                "tunnels": [
                    ("110.173.49.157", "herbert", 1),
                    ("110.173.49.157", "hansi", 2),
                    ("158.244.78.71", "fritz", 3),
                ],
            },
            (
                0,
                "[herbert] [hansi] Phase 1: in: 0.00 B/s, out: 0.00 B/s, Phase 2: in: 0.00 B/s, out: 0.00 B/s",
                [("if_in_octets", 0.0), ("if_out_octets", 0.0)],
            ),
            id="with aliases",
        ),
        pytest.param(
            "1.2.3.4",
            {},
            (
                2,
                "Tunnel is missing",
                [("if_in_octets", 0), ("if_out_octets", 0)],
            ),
            id="tunnel missing, no params",
        ),
        pytest.param(
            "1.2.3.4",
            {"state": 3},
            (
                3,
                "Tunnel is missing",
                [("if_in_octets", 0), ("if_out_octets", 0)],
            ),
            id="tunnel missing, default missing state configured",
        ),
        pytest.param(
            "1.2.3.4",
            {
                "tunnels": [
                    ("110.173.49.157", "herbert", 1),
                    ("1.2.3.4", "annegret", 1),
                ],
                "state": 3,
            },
            (
                1,
                "[annegret] Tunnel is missing",
                [("if_in_octets", 0), ("if_out_octets", 0)],
            ),
            id="tunnel missing, default and tunnel-specific missing state configured",
        ),
    ],
)
def test_check_cisco_vpn_tunnel(
    item: str,
    params: Mapping[str, Any],
    expected_result: Tuple[int, str, Sequence[Tuple[str, float]]],
) -> None:
    assert Check("cisco_vpn_tunnel").run_check(
        item,
        params,
        _SECTION,
    ) == expected_result
