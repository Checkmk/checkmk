#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public Licensv2
# This filis part of Checkmk (https://checkmk.com). It is subject to thterms and
# conditions defined in thfilCOPYING, which is part of this sourccodpackage.

from typing import Sequence, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.base.plugins.agent_based import cisco_vpn_tunnel
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.cisco_vpn_tunnel import (
    check_cisco_vpn_tunnel,
    CheckParameters,
    discover_cisco_vpn_tunnel,
    parse_cisco_vpn_tunnel,
    Phase,
    VPNTunnel,
)

_STRING_TABLE = [
    [
        ["761856", "211.26.203.53", "6048", "6080"],
        ["12509184", "158.244.78.71", "77536", "77632"],
        ["13746176", "110.173.49.157", "57872", "60680"],
        ["22503424", "237.39.169.243", "618480", "619920"],
        ["43585536", "88.40.117.192", "4720", "4720"],
        ["45854720", "99.155.108.155", "18944", "18992"],
        ["55197696", "107.36.151.171", "13120", "13120"],
        ["67805184", "211.167.210.107", "1564", "1600"],
        ["81604608", "62.111.62.165", "1828836", "540776"],
        ["89939968", "158.8.11.214", "86240", "86720"],
        ["100876288", "176.210.155.217", "3176", "2424"],
        ["107544576", "13.232.54.46", "12400", "12464"],
        ["118820864", "", "", ""],
    ],
    [
        ["221540352", "1", "29603616", "29606724"],
        ["13746176", "1", "4275671278", "552070119"],
        ["181399552", "1", "34440168", "265351058"],
        ["248475648", "1", "971342856", "972010160"],
        ["81604608", "1", "418226309", "2404964353"],
        ["12509184", "1", "1445263205", "1124929982"],
        ["253952000", "1", "356940563", "861342895"],
        ["242581504", "1", "103816", "34333876"],
        ["242581504", "1", "1951457951", "1352517430"],
        ["242581504", "1", "2260468", "3172212"],
        ["242581504", "1", "879749", "1769163"],
        ["89939968", "1", "8302751", "85269964"],
        ["89939968", "1", "836794", "1016956"],
        ["107544576", "1", "729386986", "181978684"],
        ["146874368", "1", "20042695", "139631395"],
        ["190656512", "1", "1632632", "2622595"],
        ["175759360", "1", "1190381852", "2072225340"],
        ["175759360", "1", "6456504", "9433584"],
        ["175759360", "1", "2037804", "2062476"],
        ["175759360", "1", "2558867", "2271498"],
        ["175759360", "1", "2618100", "3383666"],
        ["190656512", "1", "51552982", "1464267"],
        ["183275520", "1", "368040", "7596836"],
        ["22503424", "1", "2911153", "2849138"],
        ["22503424", "1", "2815031", "2755928"],
        ["22503424", "1", "4583776", "72612782"],
        ["22503424", "1", "5580736", "5342356"],
        ["221634560", "1", "995702379", "1060325044"],
        ["221634560", "1", "9778928", "8595392"],
        ["221634560", "1", "542364", "542364"],
        ["234635264", "1", "3169086", "10990082"],
        ["176361472", "1", "4133255", "334298"],
        ["100876288", "1", "805509", "996792"],
        ["55197696", "1", "0", "0"],
        ["202616832", "1", "328", "212"],
        ["45854720", "1", "0", "0"],
        ["242376704", "1", "528", "720"],
        ["81604608", "1", "0", "0"],
        ["195731456", "1", "0", "0"],
        ["761856", "1", "0", "0"],
        ["761856", "1", "0", "0"],
        ["179777536", "1", "120", "156"],
        ["43585536", "1", "0", "0"],
        ["242581504", "1", "0", "0"],
    ],
]

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
    "107.36.151.171": VPNTunnel(
        phase_1=Phase(input=13120.0, output=13120.0),
        phase_2=Phase(input=0.0, output=0.0),
    ),
    "13.232.54.46": VPNTunnel(
        phase_1=Phase(input=12400.0, output=12464.0),
        phase_2=Phase(input=729386986.0, output=181978684.0),
    ),
    "158.8.11.214": VPNTunnel(
        phase_1=Phase(input=86240.0, output=86720.0),
        phase_2=Phase(input=9139545.0, output=86286920.0),
    ),
    "237.39.169.243": VPNTunnel(
        phase_1=Phase(input=618480.0, output=619920.0),
        phase_2=Phase(input=15890696.0, output=83560204.0),
    ),
    "99.155.108.155": VPNTunnel(
        phase_1=Phase(input=18944.0, output=18992.0),
        phase_2=Phase(input=0.0, output=0.0),
    ),
    "88.40.117.192": VPNTunnel(
        phase_1=Phase(input=4720.0, output=4720.0),
        phase_2=Phase(input=0.0, output=0.0),
    ),
    "211.26.203.53": VPNTunnel(
        phase_1=Phase(input=6048.0, output=6080.0),
        phase_2=Phase(input=0.0, output=0.0),
    ),
}


def test_parse_cisco_vpn_tunnel() -> None:
    assert parse_cisco_vpn_tunnel(_STRING_TABLE) == _SECTION


def test_discover_cisco_vpn_tunnel() -> None:
    assert list(discover_cisco_vpn_tunnel(_SECTION)) == [
        Service(item="110.173.49.157"),
        Service(item="211.167.210.107"),
        Service(item="176.210.155.217"),
        Service(item="62.111.62.165"),
        Service(item="158.244.78.71"),
        Service(item="107.36.151.171"),
        Service(item="13.232.54.46"),
        Service(item="158.8.11.214"),
        Service(item="237.39.169.243"),
        Service(item="99.155.108.155"),
        Service(item="88.40.117.192"),
        Service(item="211.26.203.53"),
    ]


@pytest.fixture(name="time_and_value_store")
def fixture_time_and_value_store(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cisco_vpn_tunnel,
        "time",
        lambda: 1,
    )
    monkeypatch.setattr(
        cisco_vpn_tunnel,
        "get_value_store",
        lambda: {
            "phase_1_input": (0, 0),
            "phase_1_output": (0, 0),
            "phase_2_input": (0, 0),
            "phase_2_output": (0, 0),
        },
    )


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "110.173.49.157",
            {},
            [
                Result(state=State.OK, summary="Phase 1: in: 463 kBit/s, out: 485 kBit/s"),
                Result(state=State.OK, summary="Phase 2: in: 34.2 GBit/s, out: 4.42 GBit/s"),
                Metric("if_in_octets", 4275729150.0),
                Metric("if_out_octets", 552130799.0),
            ],
            id="standard case",
        ),
        pytest.param(
            "211.167.210.107",
            {},
            [
                Result(state=State.OK, summary="Phase 1: in: 12.5 kBit/s, out: 12.8 kBit/s"),
                Result(state=State.OK, summary="Phase 2 missing"),
                Metric("if_in_octets", 1564.0),
                Metric("if_out_octets", 1600.0),
            ],
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
            [
                Result(
                    state=State.OK,
                    summary="[herbert] [hansi] Phase 1: in: 463 kBit/s, out: 485 kBit/s",
                ),
                Result(state=State.OK, summary="Phase 2: in: 34.2 GBit/s, out: 4.42 GBit/s"),
                Metric("if_in_octets", 4275729150.0),
                Metric("if_out_octets", 552130799.0),
            ],
            id="with aliases",
        ),
        pytest.param(
            "1.2.3.4",
            {},
            [
                Result(state=State.CRIT, summary="Tunnel is missing"),
            ],
            id="tunnel missing, no params",
        ),
        pytest.param(
            "1.2.3.4",
            {"state": 3},
            [
                Result(state=State.UNKNOWN, summary="Tunnel is missing"),
            ],
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
            [
                Result(state=State.WARN, summary="[annegret] Tunnel is missing"),
            ],
            id="tunnel missing, default and tunnel-specific missing state configured",
        ),
    ],
)
@pytest.mark.usefixtures("time_and_value_store")
def test_check_cisco_vpn_tunnel(
    item: str,
    params: CheckParameters,
    expected_result: Sequence[Union[Result, Metric]],
) -> None:
    assert (
        list(
            check_cisco_vpn_tunnel(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )


def test_check_cisco_vpn_tunnel_counter_init() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            check_cisco_vpn_tunnel(
                "110.173.49.157",
                {},
                _SECTION,
            )
        )
    list(
        check_cisco_vpn_tunnel(
            "110.173.49.157",
            {},
            _SECTION,
        )
    )
