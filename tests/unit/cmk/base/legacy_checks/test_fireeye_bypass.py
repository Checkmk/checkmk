#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.fireeye_bypass import parse_fireeye_bypass


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Crash report c01ed1c2-c9df-11f0-9139-e43d1a36903c: IndexError on an empty section",
)
def test_empty_snmp_table_is_a_missing_section() -> None:
    section: object = parse_fireeye_bypass([])
    assert section is None
