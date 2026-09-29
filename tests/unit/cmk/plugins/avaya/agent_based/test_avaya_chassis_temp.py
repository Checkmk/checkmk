#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

import pytest

from cmk.agent_based.v2 import Service
from cmk.plugins.avaya.agent_based.avaya_chassis_temp import (
    discover_avaya_chassis_temp,
    parse_avaya_chassis_temp,
)


@pytest.mark.xfail(
    strict=True,
    reason="Crash report d6512e0a-6962-11f0-846c-a4be2b056c05: IndexError in check_avaya_chassis_temp",
)
def test_parse_avaya_chassis_temp_without_data_yields_no_section() -> None:
    # The device answered the SNMP walk without any temperature value. The
    # check must not receive an empty section it cannot evaluate; the
    # monitoring core reports the missing data instead.
    assert parse_avaya_chassis_temp([]) is None


def test_discover_avaya_chassis_temp() -> None:
    section = parse_avaya_chassis_temp([["42"]])
    assert section is not None
    assert list(discover_avaya_chassis_temp(section)) == [Service(item="Chassis")]
