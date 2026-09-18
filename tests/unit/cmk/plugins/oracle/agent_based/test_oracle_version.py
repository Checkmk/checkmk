#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_version import (
    check_oracle_version,
    discover_oracle_version,
)


def test_discover_skips_error_rows() -> None:
    section = [
        ["orcl", "FAILURE", "ORA-00942: table or view does not exist"],
        ["orcl2", "ORA-01017:", "invalid username/password"],
        ["XE", "Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production"],
    ]
    assert list(discover_oracle_version(section)) == [Service(item="XE")]


def test_check_failure_row_yields_only_the_error() -> None:
    section = [["orcl", "FAILURE", "ORA-00942: table or view does not exist"]]
    assert list(check_oracle_version("orcl", section)) == [
        Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")
    ]
