#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.snmp import snmp_is_detected

from cmk.utils.type_defs import SectionName

# walks/usv-liebert
DATA0 = """
.1.3.6.1.2.1.1.2.0  .1.3.6.1.4.1.476.1.42
"""


@pytest.mark.usefixtures("fix_register")
def test_ups_power_detect() -> None:
    assert snmp_is_detected(SectionName("ups_power"), DATA0)
