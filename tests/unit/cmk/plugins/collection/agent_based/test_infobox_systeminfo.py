#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.plugins.infoblox.agent_based.infoblox_systeminfo as ibsi
from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Attributes


def _section() -> ibsi.Section:
    assert (
        section := ibsi.parse_infoblox_systeminfo(
            [
                [
                    "IB-VM-820",
                    "422cc26d1a7a6eec1b03bd16cc74cfe7",
                    "422cc26d1a7a6eec1b03bd16cc74cfe7",
                    "7.2.7",
                ]
            ]
        )
    ) is not None
    return section


def test_inventorize_infoblox_systeminfo() -> None:
    assert list(ibsi.inventorize_infoblox_systeminfo(_section())) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "model": "IB-VM-820",
                "hardware_id": "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "serial": "422cc26d1a7a6eec1b03bd16cc74cfe7",
                "version": "7.2.7",
            },
        ),
    ]


@pytest.mark.parametrize(
    "oid_data, expected_detected",
    [
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": "Infoblox-NIOS 8.5.2",
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.7779.1.1402",
            },
            True,
            id="sysDescr contains infoblox",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": "NIOS 8.5.2",
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.7779.1.1402",
            },
            True,
            id="sysObjectID starts with Infoblox enterprise OID",
        ),
        pytest.param(
            {
                ".1.3.6.1.2.1.1.1.0": "Some other device",
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.123",
            },
            False,
            id="neither sysDescr nor sysObjectID match",
        ),
    ],
)
def test_infoblox_systeminfo_detection(
    oid_data: dict[str, str],
    expected_detected: bool,
) -> None:
    assert (
        evaluate_snmp_detection(
            detect_spec=ibsi.snmp_section_infoblox_systeminfo.detect,
            oid_value_getter=oid_data.get,
        )
        == expected_detected
    )
