#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.db2.agent_based.db2_tablespaces import (
    check_db2_tablespaces,
    discover_db2_tablespaces,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

_HEADER = [
    "TBSP_NAME",
    "TBSP_TYPE",
    "TBSP_STATE",
    "TBSP_USABLE_SIZE_KB",
    "TBSP_TOTAL_SIZE_KB",
    "TBSP_USED_SIZE_KB",
    "TBSP_FREE_SIZE_KB",
]

SECTION = parse_db2_dbs(
    [
        ["[[[db2taddm:CMDBS1]]]"],
        _HEADER,
        ["SYSCATSPACE", "DMS", "NORMAL", "1000", "1024", "100", "900"],
        ["USERSPACE1", "DMS", "NORMAL", "1000", "1024", "950", "50"],
        ["TEMPSPACE1", "SMS", "NORMAL", "32", "32", "32", "968"],
        ["OFFLINESPACE", "DMS", "OFFLINE", "1000", "1024", "100", "900"],
        ["[[[db2taddm:LOGINFAILED]]]"],
    ]
)

_PARAMS = {"levels": (10.0, 5.0), "magic_normsize": 1000}


def test_every_tablespace_is_discovered() -> None:
    assert list(discover_db2_tablespaces(SECTION)) == [
        Service(item="db2taddm:CMDBS1.SYSCATSPACE"),
        Service(item="db2taddm:CMDBS1.USERSPACE1"),
        Service(item="db2taddm:CMDBS1.TEMPSPACE1"),
        Service(item="db2taddm:CMDBS1.OFFLINESPACE"),
    ]


def test_tablespace_with_enough_free_space_is_ok() -> None:
    assert list(check_db2_tablespaces("db2taddm:CMDBS1.SYSCATSPACE", _PARAMS, SECTION)) == [
        Result(state=State.OK, summary="102 kB of 1.02 MB used"),
        Metric("tablespace_size", 1024000.0, levels=(946176.0, 997376.0)),
        Metric("tablespace_used", 102400.0),
        Metric("tablespace_max_size", 1048576.0),
        Result(state=State.OK, summary="90.00% free"),
        Result(state=State.OK, summary="State: NORMAL"),
        Result(state=State.OK, summary="Type: DMS"),
    ]


def test_tablespace_below_crit_free_space_is_crit() -> None:
    results = list(check_db2_tablespaces("db2taddm:CMDBS1.USERSPACE1", _PARAMS, SECTION))

    assert results[4] == Result(
        state=State.CRIT, summary="only 5.00% left  (warn/crit at 10.0%/5.0%)"
    )


def test_absolute_levels_report_free_bytes() -> None:
    results = list(
        check_db2_tablespaces("db2taddm:CMDBS1.SYSCATSPACE", {"levels": (1, 0)}, SECTION)
    )

    assert results[4] == Result(
        state=State.WARN, summary="only 922 kB left  (warn/crit at 1.00 MiB/0 B)"
    )


def test_sms_tablespace_uses_free_size_as_usable_size() -> None:
    results = list(check_db2_tablespaces("db2taddm:CMDBS1.TEMPSPACE1", _PARAMS, SECTION))

    assert results[0] == Result(state=State.OK, summary="32.8 kB of 991 kB used")


def test_tablespace_not_in_normal_state_is_warn() -> None:
    results = list(check_db2_tablespaces("db2taddm:CMDBS1.OFFLINESPACE", _PARAMS, SECTION))

    assert results[5] == Result(state=State.WARN, summary="State: OFFLINE")


def test_unknown_tablespace_yields_nothing() -> None:
    assert not list(check_db2_tablespaces("db2taddm:CMDBS1.VANISHED", _PARAMS, SECTION))


def test_item_without_instance_separator_is_unknown() -> None:
    assert list(check_db2_tablespaces("NODOT", _PARAMS, SECTION)) == [
        Result(
            state=State.UNKNOWN,
            summary="Invalid check item given (must be <instance>.<tablespace>)",
        )
    ]


def test_instance_without_data_is_ignored() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_db2_tablespaces("db2taddm:LOGINFAILED.SYSCATSPACE", _PARAMS, SECTION))
