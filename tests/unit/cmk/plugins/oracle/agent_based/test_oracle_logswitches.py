#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.oracle.agent_based.oracle_logswitches import discover_oracle_logswitches


def test_failure_row_does_not_abort_discovery() -> None:
    section = [
        ["orcl", "FAILURE", "ORA-00942: table or view does not exist"],
        ["XE", "12"],
    ]
    assert list(discover_oracle_logswitches(section)) == [Service(item="XE")]
