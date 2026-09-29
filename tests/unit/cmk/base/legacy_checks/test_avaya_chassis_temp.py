#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.avaya_chassis_temp import (
    inventory_avaya_chassis_temp,
    parse_avaya_chassis_temp,
)


def test_parse_avaya_chassis_temp_without_data_yields_no_section() -> None:
    # The device answered the SNMP walk without any temperature value.
    assert parse_avaya_chassis_temp([]) is None


def test_inventory_avaya_chassis_temp() -> None:
    assert inventory_avaya_chassis_temp(parse_avaya_chassis_temp([["42"]])) == [("Chassis", {})]
