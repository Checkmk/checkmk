#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.oracle.agent_based.liboracle import OraErrors
from cmk.plugins.oracle.agent_based.oracle_processes import (
    check_oracle_processes,
    discover_oracle_processes,
    OracleProcess,
    parse_oracle_processes,
    SectionOracleProcesses,
)


@pytest.mark.parametrize(
    "info, parse_result",
    [
        pytest.param(
            [["DB1DEV2", "1152", "1500"]],
            SectionOracleProcesses(
                error_processes={},
                oracle_processes={
                    "DB1DEV2": OracleProcess(
                        name="DB1DEV2", processes_count=1152, processes_limit=1500
                    )
                },
            ),
            id="Parsing one valid Oracle process from the input",
        ),
    ],
)
def test_parse_oracle_processes(info: StringTable, parse_result: SectionOracleProcesses) -> None:
    assert parse_oracle_processes(info) == parse_result


@pytest.mark.parametrize(
    "info, parse_result",
    [
        pytest.param(
            [["Error", "Message:"]],
            SectionOracleProcesses(
                error_processes={"Error": OraErrors(["Error", "Message:"])},
                oracle_processes={},
            ),
            id="Parsing one error Oracle process from the input",
        ),
    ],
)
def test_parse_error_oracle_processes(
    info: StringTable, parse_result: SectionOracleProcesses
) -> None:
    process_name = info[0][0]
    parse_value = parse_oracle_processes(info).error_processes[process_name]
    error_parse_result = parse_result.error_processes[process_name]
    assert parse_value.has_error == error_parse_result.has_error
    assert parse_value.ignore == error_parse_result.ignore
    assert parse_value.error_text == error_parse_result.error_text
    assert parse_value.error_severity == error_parse_result.error_severity


@pytest.mark.parametrize(
    "section, discovered_item",
    [
        pytest.param(
            SectionOracleProcesses(
                error_processes={},
                oracle_processes={
                    "DB1DEV2": OracleProcess(
                        name="DB1DEV2", processes_count=1152, processes_limit=1500
                    ),
                },
            ),
            [
                Service(item="DB1DEV2"),
            ],
            id="One valid Oracle process is discovered",
        ),
        pytest.param(
            SectionOracleProcesses(
                error_processes={"Error": OraErrors(["Error", "Message:"])},
                oracle_processes={},
            ),
            [Service(item="Error")],
            id="One error Oracle process is discovered",
        ),
        pytest.param(
            SectionOracleProcesses(error_processes={}, oracle_processes={}),
            [],
            id="Empty section leads to no processes being discovered",
        ),
    ],
)
def test_discover_oracle_processes(
    section: SectionOracleProcesses, discovered_item: Sequence[Service]
) -> None:
    assert list(discover_oracle_processes(section)) == discovered_item


@pytest.mark.parametrize(
    "section, item, check_result",
    [
        pytest.param(
            SectionOracleProcesses(
                error_processes={},
                oracle_processes={
                    "FDMTST": OracleProcess(name="FDMTST", processes_count=50, processes_limit=300),
                },
            ),
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
            SectionOracleProcesses(
                error_processes={},
                oracle_processes={
                    "DB1DEV2": OracleProcess(
                        name="DB1DEV2", processes_count=1152, processes_limit=1500
                    ),
                },
            ),
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
            SectionOracleProcesses(
                error_processes={},
                oracle_processes={
                    "DB1DEV2": OracleProcess(
                        name="DB1DEV2", processes_count=1450, processes_limit=1500
                    ),
                },
            ),
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
        pytest.param(
            SectionOracleProcesses(
                error_processes={"Error": OraErrors(["Error", "Message:"])},
                oracle_processes={},
            ),
            "Error",
            [
                Result(
                    state=State.UNKNOWN,
                    summary='Found error in agent output "Message:"',
                )
            ],
            id="UNKNOWN on error from 1.6 solaris agent plug-in output",
        ),
    ],
)
def test_check_oracle_processes(
    section: SectionOracleProcesses,
    item: str,
    check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(check_oracle_processes(item=item, params={"levels": (70.0, 90.0)}, section=section))
        == check_result
    )
