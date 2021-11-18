#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.pdu_gude import GudePDUProperty, parse_pdu_gude

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
    assert (parse_pdu_gude([
        ["13478", "4010", "0", "228", "0"],
        ["8", "0", "0", "0", "0"],
    ]) == _SECTION)
