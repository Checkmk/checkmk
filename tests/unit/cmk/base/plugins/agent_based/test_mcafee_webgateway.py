#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from pathlib import Path

import pytest

from tests.testlib.snmp import get_parsed_snmp_section, snmp_is_detected

from tests.unit.conftest import FixRegister

from cmk.utils.sectionname import SectionName

from cmk.base.plugins.agent_based import mcafee_webgateway
from cmk.base.plugins.agent_based.agent_based_api import v1

WALK = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7
.1.3.6.1.4.1.1230.2.7.2.1.2.0 10
.1.3.6.1.4.1.1230.2.7.2.1.5.0 20
"""

WALK_2 = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7
.1.3.6.1.4.1.1230.2.7.2.1.5.0 20
"""


@pytest.mark.parametrize("walk", [WALK, WALK_2])
def test_detect(
    walk: str, fix_register: FixRegister, as_path: typing.Callable[[str], Path]
) -> None:
    assert snmp_is_detected(SectionName("mcafee_webgateway"), as_path(walk))


@pytest.mark.parametrize("walk", [WALK, WALK_2])
def test_parse(walk: str, fix_register: FixRegister, as_path: typing.Callable[[str], Path]) -> None:
    # Act
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway"), as_path(walk))

    # Assert
    assert section is not None


@pytest.mark.parametrize("walk", [WALK, WALK_2])
def test_discovery(
    walk: str, fix_register: FixRegister, as_path: typing.Callable[[str], Path]
) -> None:
    # Assemble
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway"), as_path(walk))
    assert section is not None

    # Act
    services = list(mcafee_webgateway.discover_mcafee_gateway(section))

    # Assert
    assert services == [v1.Service()]


@pytest.mark.parametrize(
    "walk, params, expected_results",
    [
        pytest.param(
            WALK,
            {},
            [
                v1.Result(state=v1.State.OK, summary="Infections: 8.0/s"),
                v1.Metric(name="infections_rate", value=8.0),
                v1.Result(state=v1.State.OK, summary="Connections blocked: 18.0/s"),
                v1.Metric(name="connections_blocked_rate", value=18.0),
            ],
            id="No levels",
        ),
        pytest.param(
            WALK,
            {"infections": (5, 10), "connections_blocked": (10, 15)},
            [
                v1.Result(
                    state=v1.State.WARN,
                    summary="Infections: 8.0/s (warn/crit at 5.0/s/10.0/s)",
                ),
                v1.Metric(name="infections_rate", value=8.0, levels=(5.0, 10.0)),
                v1.Result(
                    state=v1.State.CRIT,
                    summary="Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)",
                ),
                v1.Metric(name="connections_blocked_rate", value=18.0, levels=(10.0, 15.0)),
            ],
            id="Warn and Crit",
        ),
        pytest.param(
            WALK_2,
            {},
            [
                v1.Result(state=v1.State.OK, summary="Connections blocked: 18.0/s"),
                v1.Metric(name="connections_blocked_rate", value=18.0),
            ],
            id="One missing",
        ),
    ],
)
def test_check_results(
    walk: str,
    fix_register: FixRegister,
    params: mcafee_webgateway.Params,
    expected_results: list[object],
    as_path: typing.Callable[[str], Path],
) -> None:
    # Assemble
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway"), as_path(walk))
    assert section is not None
    now = 2.0
    value_store = {
        "check_mcafee_webgateway.infections": (now - 1.0, 2),
        "check_mcafee_webgateway.connections_blocked": (now - 1.0, 2),
    }

    # Act
    results = list(mcafee_webgateway._check_mcafee_webgateway(now, value_store, params, section))

    # Assert
    assert results == expected_results
