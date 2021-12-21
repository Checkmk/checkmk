#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.pdu_gude import check_pdu_gude, GudePDUProperty, parse_pdu_gude

_SECTION = {
    "1": [
        GudePDUProperty(
            value=13.478,
            unit="kWh",
            label="Total accumulated active energy",
        ),
        GudePDUProperty(
            value=4010.0,
            unit="W",
            label="Active power",
        ),
        GudePDUProperty(
            value=0.0,
            unit="A",
            label="Current",
        ),
        GudePDUProperty(
            value=228.0,
            unit="V",
            label="Voltage",
        ),
        GudePDUProperty(
            value=0.0,
            unit="VA",
            label="Mean apparent power",
        ),
    ],
    "2": [
        GudePDUProperty(
            value=0.008,
            unit="kWh",
            label="Total accumulated active energy",
        ),
        GudePDUProperty(
            value=0.0,
            unit="W",
            label="Active power",
        ),
        GudePDUProperty(
            value=0.0,
            unit="A",
            label="Current",
        ),
        GudePDUProperty(
            value=0.0,
            unit="V",
            label="Voltage",
        ),
        GudePDUProperty(
            value=0.0,
            unit="VA",
            label="Mean apparent power",
        ),
    ],
}


def test_parse_pdu_gude() -> None:
    assert (
        parse_pdu_gude(
            [
                ["13478", "4010", "0", "228", "0"],
                ["8", "0", "0", "0", "0"],
            ]
        )
        == _SECTION
    )


def test_check_pdu_gude() -> None:
    assert list(
        check_pdu_gude(
            item="1",
            params={
                "V": (250, 210),
                "A": (15, 16),
                "W": (3500, 3600),
            },
            section=_SECTION,
        )
    ) == [
        Result(
            state=State.OK,
            summary="Total accumulated active energy: 13.48 kWh",
        ),
        Metric("kWh", 13.478),
        Result(
            state=State.CRIT,
            summary="Active power: 4010.00 W (warn/crit at 3500.00 W/3600.00 W)",
        ),
        Metric("W", 4010.0, levels=(3500.0, 3600.0)),
        Result(
            state=State.OK,
            summary="Current: 0.00 A",
        ),
        Metric("A", 0.0, levels=(15.0, 16.0)),
        Result(
            state=State.WARN,
            summary="Voltage: 228.00 V (warn/crit below 250.00 V/210.00 V)",
        ),
        Metric("V", 228.0),
        Result(
            state=State.OK,
            summary="Mean apparent power: 0.00 VA",
        ),
        Metric("VA", 0.0),
    ]
