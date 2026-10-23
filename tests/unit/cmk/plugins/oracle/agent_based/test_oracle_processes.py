#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.plugins.oracle.agent_based.liboracle import Ok
from cmk.plugins.oracle.agent_based.oracle_processes import (
    check_oracle_processes,
    discover_oracle_processes,
    OracleProcess,
    parse_oracle_processes,
    Section,
)

_FAILURE = [["FREE", "FAILURE", "ORA-00942: table or view does not exist"]]


def test_parse_oracle_processes() -> None:
    assert parse_oracle_processes([["DB1DEV2", "1152", "1500"]]) == {
        "DB1DEV2": Ok(OracleProcess(name="DB1DEV2", processes_count=1152, processes_limit=1500))
    }


def test_discover_oracle_processes() -> None:
    section = {
        "DB1DEV2": Ok(OracleProcess(name="DB1DEV2", processes_count=1152, processes_limit=1500))
    }
    assert list(discover_oracle_processes(section)) == [Service(item="DB1DEV2")]


def test_parse_drops_a_row_without_numbers() -> None:
    assert parse_oracle_processes([["DB1DEV2", "", "1500"]]) == {}


def test_discover_nothing_from_an_empty_section() -> None:
    assert not list(discover_oracle_processes({}))


def test_discover_failure_row() -> None:
    assert list(discover_oracle_processes(parse_oracle_processes(_FAILURE))) == [
        Service(item="FREE")
    ]


def test_discover_nothing_from_an_error_line_without_instance() -> None:
    # A connect warning of legacy mk_oracle, split at whitespace.
    string_table = [["ORA-28002:", "the", "password", "will", "expire", "within", "7", "days"]]
    assert not list(discover_oracle_processes(parse_oracle_processes(string_table)))


@pytest.mark.parametrize(
    "section, item, check_result",
    [
        pytest.param(
            {"FDMTST": Ok(OracleProcess(name="FDMTST", processes_count=50, processes_limit=300))},
            "FDMTST",
            [
                Result(
                    state=State.OK,
                    summary="50 of 300 processes are used: 16.67%",
                ),
                Metric(name="processes", value=50, levels=(210, 270)),
            ],
            id="Oracle process OK state",
        ),
        pytest.param(
            {
                "DB1DEV2": Ok(
                    OracleProcess(name="DB1DEV2", processes_count=1152, processes_limit=1500)
                )
            },
            "DB1DEV2",
            [
                Result(
                    state=State.WARN,
                    summary="1152 of 1500 processes are used: 76.80% (warn/crit at 70.00%/90.00%)",
                ),
                Metric(name="processes", value=1152, levels=(1050, 1350)),
            ],
            id="Oracle process state WARN",
        ),
        pytest.param(
            {
                "DB1DEV2": Ok(
                    OracleProcess(name="DB1DEV2", processes_count=1450, processes_limit=1500)
                )
            },
            "DB1DEV2",
            [
                Result(
                    state=State.CRIT,
                    summary="1450 of 1500 processes are used: 96.67% (warn/crit at 70.00%/90.00%)",
                ),
                Metric(name="processes", value=1450, levels=(1050, 1350)),
            ],
            id="Oracle process state CRIT",
        ),
    ],
)
def test_check_oracle_processes(
    section: Section,
    item: str,
    check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(check_oracle_processes(item=item, params={"levels": (70.0, 90.0)}, section=section))
        == check_result
    )


def test_check_surfaces_failure() -> None:
    assert list(
        check_oracle_processes(
            item="FREE", params={"levels": (70.0, 90.0)}, section=parse_oracle_processes(_FAILURE)
        )
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_failure_row_wins_over_data_row() -> None:
    section = parse_oracle_processes([["FREE", "50", "300"]] + _FAILURE)
    assert list(
        check_oracle_processes(item="FREE", params={"levels": (70.0, 90.0)}, section=section)
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_check_missing_goes_stale() -> None:
    with pytest.raises(IgnoreResultsError):
        list(check_oracle_processes(item="FREE", params={"levels": (70.0, 90.0)}, section={}))
