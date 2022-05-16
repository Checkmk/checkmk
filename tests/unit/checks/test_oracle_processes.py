#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional, Sequence, Tuple, Union

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks


class OracleProcess(NamedTuple):
    name: str
    processes_count: int
    processes_limit: int


ErrorProcesses = Mapping[str, Optional[Tuple[int, str]]]
OracleProcesses = Mapping[str, OracleProcess]


class SectionOracleProcesses(NamedTuple):
    error_processes: ErrorProcesses
    oracle_processes: OracleProcesses


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
        pytest.param(
            [["Error", "Message:"]],
            SectionOracleProcesses(
                error_processes={"Error": (3, 'Found error in agent output "Message:"')},
                oracle_processes={},
            ),
            id="Parsing one error Oracle process from the input",
        ),
    ],
)
def test_parse_oracle_processes(
    info: StringTable,
    parse_result: SectionOracleProcesses,
    fix_register: FixRegister,
) -> None:
    check = fix_register.agent_sections[SectionName("oracle_processes")]
    assert check.parse_function(info) == parse_result


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
                error_processes={"Error": (3, 'Found error in agent output "Message:"')},
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
    section: SectionOracleProcesses,
    discovered_item: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("oracle_processes")]
    assert list(check.discovery_function(section)) == discovered_item


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
                    summary="1152 of 1500 processes are used: 76.8% (warn/crit at 70.0%/90.0%)",
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
                    summary="1450 of 1500 processes are used: 96.67% (warn/crit at 70.0%/90.0%)",
                ),
                Metric(name="processes", value=1450, levels=(1050, 1350)),
            ],
            id="Oracle process state CRIT",
        ),
        pytest.param(
            SectionOracleProcesses(
                error_processes={"Error": (3, 'Found error in agent output "Message:"')},
                oracle_processes={},
            ),
            "Error",
            [
                Result(
                    state=State.UNKNOWN,
                    summary='Found error in agent output "Message:"',
                )
            ],
            id="UNKNOWN on error from 1.6 solaris agent plugin output",
        ),
    ],
)
def test_check_oracle_processes(
    section: SectionOracleProcesses,
    item: str,
    check_result: Sequence[Union[Result, Metric]],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("oracle_processes")]
    assert (
        list(check.check_function(item=item, params={"levels": (70.0, 90.0)}, section=section))
        == check_result
    )
