#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_logswitches import (
    check_oracle_logswitches,
    discover_oracle_logswitches,
    parse_oracle_logswitches,
)

_NORMAL = [["orcl", "42"]]
_FAILURE = [["orcl", "FAILURE", "ORA-00942: table or view does not exist"]]
_PARAMS = {"levels": (50, 100), "levels_lower": (-1, -1)}


def test_discover_normal() -> None:
    assert list(discover_oracle_logswitches(parse_oracle_logswitches(_NORMAL))) == [
        Service(item="orcl")
    ]


def test_discover_skips_error_row() -> None:
    error_info = [["orcl", "ORA-16000: database open for read-only access"]]
    assert not list(discover_oracle_logswitches(parse_oracle_logswitches(error_info)))


def test_discover_skips_failure_row() -> None:
    assert not list(discover_oracle_logswitches(parse_oracle_logswitches(_FAILURE)))


def test_check_normal() -> None:
    assert list(check_oracle_logswitches("orcl", _PARAMS, parse_oracle_logswitches(_NORMAL)))[
        0
    ] == Result(state=State.OK, summary="Log switches in the last 60 minutes: 42")


def test_check_surfaces_failure() -> None:
    assert list(check_oracle_logswitches("orcl", _PARAMS, parse_oracle_logswitches(_FAILURE))) == [
        Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")
    ]


def test_check_missing_goes_stale() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_oracle_logswitches("orcl", _PARAMS, parse_oracle_logswitches([])))
