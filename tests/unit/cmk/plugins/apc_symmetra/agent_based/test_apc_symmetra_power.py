#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.plugins.apc_symmetra.agent_based.apc_symmetra_power import snmp_section_apc_symmetra_power

# SUP-12323
DATA0: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.318.1.3.2.12",
}

# walks/usv-apc-symmetra-new
DATA1: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.318.1.3.28.33",
}


@pytest.mark.parametrize(
    "walk",
    [
        pytest.param(DATA0, id="data0"),
        pytest.param(DATA1, id="data1"),
    ],
)
def test_apc_symmetra_power_detect(walk: dict[str, str]) -> None:
    assert evaluate_snmp_detection(
        detect_spec=snmp_section_apc_symmetra_power.detect, oid_value_getter=walk.get
    )
