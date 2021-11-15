#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.snmp_info import parse_snmp_info, SNMPInfo


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            [
                [
                    "KONICA MINOLTA bizhub C451",
                    "R. Hantzsch",
                    "Bizhub C451 1.OG\n",
                    "1.OG / Raum 1.08",
                ]
            ],
            SNMPInfo(
                "KONICA MINOLTA bizhub C451", "R. Hantzsch", "Bizhub C451 1.OG", "1.OG / Raum 1.08"
            ),
        ),
        (
            [
                [
                    "KONICA MINOLTA bizhub C451",
                    "R. Hantzsch",
                    "Bizhub C451\n1.OG",
                    "1.OG / Raum 1.08",
                ]
            ],
            SNMPInfo(
                "KONICA MINOLTA bizhub C451", "R. Hantzsch", "Bizhub C451 1.OG", "1.OG / Raum 1.08"
            ),
        ),
        (
            [
                [
                    "KONICA MINOLTA bizhub C451",
                    "R. Hantzsch",
                    "Bizhub C451\r\n1.OG",
                    "1.OG / Raum 1.08",
                ]
            ],
            SNMPInfo(
                "KONICA MINOLTA bizhub C451", "R. Hantzsch", "Bizhub C451 1.OG", "1.OG / Raum 1.08"
            ),
        ),
    ],
)
def test_parse_snmp_info(string_table, expected_result):
    result = parse_snmp_info(string_table)
    assert result == expected_result
