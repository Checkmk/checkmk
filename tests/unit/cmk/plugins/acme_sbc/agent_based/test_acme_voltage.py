#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.acme.agent_based.acme_voltage import discover_acme_voltage, parse_acme_voltage


@pytest.mark.xfail(
    strict=True,
    reason="Crash report 88b0e00e-9b4e-11f1-90fa-005056a8b5b9: ValueError in discover_acme_voltage",
)
def test_discover_acme_voltage_skips_sensors_not_present() -> None:
    section = parse_acme_voltage(
        [
            ["MAIN 1.20V", "1199", "2"],
            ["PHY 3.30V", "3318", "2"],
            ["MAIN 3.30V AUX", "0", "7"],
        ]
    )
    assert section is not None
    assert list(discover_acme_voltage(section)) == [  # type: ignore[arg-type]
        Service(item="MAIN 1.20V"),
        Service(item="PHY 3.30V"),
    ]
