#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.ucd_cpu_util import parse_ucd_cpu_util


def test_parse_ucd_cpu_util_without_data() -> None:
    assert parse_ucd_cpu_util([]) is None
