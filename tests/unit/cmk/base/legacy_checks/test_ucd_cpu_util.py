#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.ucd_cpu_util import parse_ucd_cpu_util


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Crash group 3828 (CMK-39517), crash report "
        "d7ed83a0-3318-11f1-b0a0-0050569f5775: an empty section parses to an "
        "empty mapping instead of None"
    ),
)
def test_parse_ucd_cpu_util_without_data() -> None:
    assert parse_ucd_cpu_util([]) is None
