#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.agent_based.statgrab_cpu import parse_statgrab_cpu
from cmk.plugins.lib.cpu_util import CPUInfo

STRING_TABLE = [
    ["idle", "100"],
    ["iowait", "200"],
    ["kernel", "300"],
    ["nice", "400"],
    ["swap", "0"],
    ["systime", "500"],
    ["total", "2100"],
    ["user", "600"],
]


def test_parse_statgrab_cpu() -> None:
    assert parse_statgrab_cpu(STRING_TABLE) == CPUInfo("cpu", 600, 400, 300, 100, 200)
