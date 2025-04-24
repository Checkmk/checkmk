#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.brocade_sfp import (
    check_brocade_sfp,
    discover_brocade_sfp,
    parse_brocade_sfp,
)
from cmk.plugins.lib.brocade import DISCOVERY_DEFAULT_PARAMETERS

_STRING_TABLE = [
    [
        ["1", "6", "1", "1", "DC-GA-SAN-1_128_P0_DC-PU-SAN-1_128_P0_ISL"],
        ["2", "4", "2", "2", "DC-GA-SAN-1_128_P1_DC-PU-SAN-1_128_P1_RES_ISL"],
        ["3", "6", "1", "1", "STSV5HRAGP00_SR_GA_S2_N3P1_STG"],
        ["5", "6", "1", "1", "STSV5HRAGP00_SR_GA_S2_N4P1_STG"],
        ["7", "6", "1", "1", "ESX_N5_HBA1_P1_HST"],
        ["8", "6", "1", "1", "ESX_N7_HBA1_P1_HST"],
        ["9", "6", "1", "1", "RAG10050_SLOT_6_HBA1_SR_GA_S2_TAP"],
        ["10", "6", "1", "1", "SOVM01_SR_GA_S2_HBA1P1_HST"],
    ],
    [["1"]],
    [
        ["37", "3376.8", "24.702", "-1.6", "0.0", "0.1"],
        ["44", "3331.8", "7.408", "-2.2", "-2.5", "0.3"],
        ["42", "3332.2", "7.346", "-1.8", "-2.5", "0.5"],
        ["42", "3328.5", "7.378", "-3.0", "-2.6", "0.7"],
        ["42", "3332.7", "7.346", "-2.5", "-2.6", "0.8"],
        ["39", "3328.6", "7.346", "-3.2", "-3.0", "0.9"],
        ["39", "3326.1", "7.378", "-2.0", "-2.6", "0.10"],
    ],
]


def test_discover_brocade_sfp() -> None:
    assert list(
        discover_brocade_sfp(
            DISCOVERY_DEFAULT_PARAMETERS,
            parse_brocade_sfp(
                _STRING_TABLE,
            ),
        )
    ) == [
        Service(item="0 ISL DC-GA-SAN-1_128_P0_DC-PU-SAN-1_128_P0_ISL"),
        Service(item="2 STSV5HRAGP00_SR_GA_S2_N3P1_STG"),
        Service(item="4 STSV5HRAGP00_SR_GA_S2_N4P1_STG"),
        Service(item="6 ESX_N5_HBA1_P1_HST"),
        Service(item="7 ESX_N7_HBA1_P1_HST"),
        Service(item="8 RAG10050_SLOT_6_HBA1_SR_GA_S2_TAP"),
        Service(item="9 SOVM01_SR_GA_S2_HBA1P1_HST"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        (
            "00 ISL DC-GA-SAN-1_128_P0_DC-PU-SAN-1_128_P0_ISL",
            {"voltage": (0.0, 0.0, 3.3, 3.5)},
            [
                Result(state=State.OK, summary="Rx: -1.60 dBm"),
                Metric("input_signal_power_dbm", -1.6),
                Result(state=State.OK, summary="Tx: 0.00 dBm"),
                Metric("output_signal_power_dbm", 0.0),
                Result(state=State.OK, summary="Current: 0.02 A"),
                Metric("current", 0.024702),
                Result(state=State.WARN, summary="Voltage: 3.38 V (warn/crit at 3.30 V/3.50 V)"),
                Metric("voltage", 3.3768000000000002, levels=(3.3, 3.5)),
            ],
        )
    ],
)
def test_check_brocade_sfp(
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_brocade_sfp(
                item,
                params,
                parse_brocade_sfp(_STRING_TABLE),
            )
        )
        == expected_result
    )
