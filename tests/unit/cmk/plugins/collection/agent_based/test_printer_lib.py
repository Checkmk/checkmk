#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import SNMPDetectSpecification
from cmk.fetchers._snmpscan import _evaluate_snmp_detection as evaluate_snmp_detection
from cmk.plugins.printer.lib import DETECT_PRINTER, DETECT_PRINTER_PAGES

_PRINTER_MIB = {
    ".1.3.6.1.2.1.43.*": "1",
    ".1.3.6.1.2.1.43.11.1.1.6.1.1": "Black Cartridge HP 151A",
    ".1.3.6.1.2.1.43.10.2.1.4.1.1": "12345",
}


@pytest.mark.parametrize(
    "detect_spec", [DETECT_PRINTER, DETECT_PRINTER_PAGES], ids=["printer", "printer_pages"]
)
def test_hp_jetdirect_printer_with_generic_sys_object_id_is_detected(
    detect_spec: SNMPDetectSpecification,
) -> None:
    oid_data = {
        ".1.3.6.1.2.1.1.1.0": "HP ETHERNET MULTI-ENVIRONMENT",
        ".1.3.6.1.2.1.1.2.0": ".0.0",
        **_PRINTER_MIB,
    }

    assert evaluate_snmp_detection(detect_spec=detect_spec, oid_value_getter=oid_data.get)


@pytest.mark.parametrize(
    "detect_spec", [DETECT_PRINTER, DETECT_PRINTER_PAGES], ids=["printer", "printer_pages"]
)
def test_unknown_device_with_generic_sys_object_id_is_not_detected(
    detect_spec: SNMPDetectSpecification,
) -> None:
    oid_data = {
        ".1.3.6.1.2.1.1.1.0": "Generic network device",
        ".1.3.6.1.2.1.1.2.0": ".0.0",
        **_PRINTER_MIB,
    }

    assert not evaluate_snmp_detection(detect_spec=detect_spec, oid_value_getter=oid_data.get)
