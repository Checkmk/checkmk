#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import IgnoreResults, Service
from cmk.plugins.akcp.agent_based import akcp_sensor_drycontact as drycontact

# Rows as reported by the device of SUP-29863, which intermittently drops fields.
DRYCONTACT_TABLE_CORRUPTED = [["Smoke Detector 1", "", "1"], ["", "2", "1"]]

# The online field is the last column of this table, not the third.
EXP_TABLE_CORRUPTED = [
    ["Drycontact 1", "2", "Critical desc", "Normal desc", ""],
    ["", "2", "Critical desc", "Normal desc", "1"],
]


def test_drycontact_discover_keeps_corrupted_row_drops_nameless_one() -> None:
    assert list(
        drycontact.discover_akcp_sensor_drycontact(
            drycontact.parse_akcp_sensor2plus_drycontact(DRYCONTACT_TABLE_CORRUPTED)
        )
    ) == [Service(item="Smoke Detector 1")]


def test_drycontact_check_corrupted_row_goes_stale() -> None:
    assert list(
        drycontact.check_akcp_sensor_drycontact(
            "Smoke Detector 1",
            drycontact.parse_akcp_sensor2plus_drycontact(DRYCONTACT_TABLE_CORRUPTED),
        )
    ) == [IgnoreResults("Sensor reported corrupted values")]


def test_exp_drycontact_discover_keeps_corrupted_row_drops_nameless_one() -> None:
    assert list(
        drycontact.discover_akcp_exp_drycontact(
            drycontact.parse_akcp_exp_drycontact(EXP_TABLE_CORRUPTED)
        )
    ) == [Service(item="Drycontact 1")]


def test_exp_drycontact_check_corrupted_row_goes_stale() -> None:
    assert list(
        drycontact.check_akcp_exp_drycontact(
            "Drycontact 1",
            drycontact.parse_akcp_exp_drycontact(EXP_TABLE_CORRUPTED),
        )
    ) == [IgnoreResults("Sensor reported corrupted values")]
