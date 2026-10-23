#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.checkengine.specs.parameters import Parameters
from cmk.plugins.cisco.agent_based.cisco_cpu import check_cisco_cpu, Section


def test_check_cisco_cpu_applies_levels_from_rule_parameters() -> None:
    # The check engine passes the rule as an immutable Parameters mapping, not a dict.
    params = Parameters({"util": (80.0, 90.0)})

    assert list(check_cisco_cpu(params, Section(old_oid="", new_oid="85"))) == [
        Result(
            state=State.WARN,
            summary="Utilization in the last 5 minutes: 85.00% (warn/crit at 80.00%/90.00%)",
        ),
        Metric("util", 85.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]
