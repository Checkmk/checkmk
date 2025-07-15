#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.plugins.collection.agent_based.apc_symmetra_power import snmp_section_apc_symmetra_power
from tests.unit.cmk.plugins.collection.agent_based.snmp import snmp_is_detected

# SUP-12323
DATA0 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.2.12
"""

# walks/usv-apc-symmetra-new
DATA1 = """
.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.318.1.3.28.33
"""


@pytest.mark.parametrize(
    "walk",
    [
        pytest.param(DATA0, id="data0"),
        pytest.param(DATA1, id="data1"),
    ],
)
def test_apc_symmetra_power_detect(walk: str, as_path: Callable[[str], Path]) -> None:
    assert snmp_is_detected(snmp_section_apc_symmetra_power, as_path(walk))
