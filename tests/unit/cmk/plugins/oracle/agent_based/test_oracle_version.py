#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.oracle.agent_based.oracle_version import discover_oracle_version


def test_failure_row_does_not_abort_discovery() -> None:
    section = [
        ["orcl", "FAILURE", "ORA-00942: table or view does not exist"],
        ["XE", "Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production"],
    ]
    assert list(discover_oracle_version(section)) == [Service(item="orcl"), Service(item="XE")]
