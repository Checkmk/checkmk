#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.oracle.agent_based.oracle_undostat import (
    check_oracle_undostat,
    discover_oracle_undostat,
    parse_oracle_undostat,
)

_PARAMS = {"levels": (600, 300), "nospaceerrcnt_state": 2}
_DATA = [["TUX2", "160", "0", "1081", "300", "0"]]
_FAILURE = [["TUX2", "FAILURE", "ORA-00942: table or view does not exist"]]


def test_discover_normal() -> None:
    assert list(discover_oracle_undostat(parse_oracle_undostat(_DATA))) == [Service(item="TUX2")]


def test_discover_skips_failure_row() -> None:
    assert not list(discover_oracle_undostat(parse_oracle_undostat(_FAILURE)))


def test_check_normal() -> None:
    assert list(check_oracle_undostat("TUX2", _PARAMS, parse_oracle_undostat(_DATA))) == [
        Result(state=State.OK, summary="Undo retention: 18 minutes 1 second"),
        Result(state=State.OK, summary="Active undo blocks: 160"),
        Result(state=State.OK, summary="Max concurrent transactions: 0"),
        Result(state=State.OK, summary="Max querylen: 5 minutes 0 seconds"),
        Result(state=State.OK, summary="Space errors: 0"),
        Metric("activeblk", 160.0),
        Metric("transconcurrent", 0.0),
        Metric("tunedretention", 1081.0, levels=(600.0, 300.0)),
        Metric("querylen", 300.0),
        Metric("nonspaceerrcount", 0.0),
    ]


def test_check_legacy_row_without_tuned_retention() -> None:
    # Oracle 9.2 agents send -1 for ACTIVEBLKS and TUNED_UNDORETENTION
    section = parse_oracle_undostat([["TUX2", "-1", "3", "-1", "300", "0"]])
    results = list(check_oracle_undostat("TUX2", _PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="Undo retention: -1")
    assert Result(state=State.OK, summary="Max concurrent transactions: 3") in results


def test_check_surfaces_failure() -> None:
    assert list(check_oracle_undostat("TUX2", _PARAMS, parse_oracle_undostat(_FAILURE))) == [
        Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")
    ]


def test_failure_row_wins_over_data_row() -> None:
    assert list(
        check_oracle_undostat("TUX2", _PARAMS, parse_oracle_undostat(_DATA + _FAILURE))
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_row_without_numbers_is_dropped() -> None:
    assert parse_oracle_undostat([["TUX2", "160", "0", "n/a", "300", "0"]]) == {}


def test_rows_of_other_length_are_dropped() -> None:
    assert parse_oracle_undostat([["TUX2", "160", "0"]]) == {}


def test_check_missing_goes_stale() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_oracle_undostat("TUX2", _PARAMS, parse_oracle_undostat([])))
