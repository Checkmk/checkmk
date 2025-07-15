#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import typing
from pathlib import Path

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, SimpleSNMPSection, State
from cmk.plugins.collection.agent_based import mcafee_webgateway
from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

WALK_MCAFEE = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7
.1.3.6.1.4.1.1230.2.7.2.1.2.0 10
.1.3.6.1.4.1.1230.2.7.2.1.5.0 20
"""

WALK_MCAFEE_2 = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7
.1.3.6.1.4.1.1230.2.7.2.1.5.0 20
"""

WALK_SKYHIGH = """
.1.3.6.1.2.1.1.2.0 1.3.6.1.4.1.59732.2.7.1.1
.1.3.6.1.4.1.59732.2.7.2.1.2.0 10
.1.3.6.1.4.1.59732.2.7.2.1.5.0 20
"""

WALK_SKYHIGH_2 = """
.1.3.6.1.2.1.1.2.0 1.3.6.1.4.1.59732.2.7.1.1
.1.3.6.1.4.1.59732.2.7.2.1.5.0 20
"""


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (WALK_MCAFEE, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_MCAFEE_2, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_SKYHIGH, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
        (WALK_SKYHIGH_2, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
    ],
)
def test_detect(
    walk: str,
    detected_section: SimpleSNMPSection,
    as_path: typing.Callable[[str], Path],
) -> None:
    assert snmp_is_detected(detected_section, as_path(walk))


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (WALK_MCAFEE, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_MCAFEE_2, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_SKYHIGH, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
        (WALK_SKYHIGH_2, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
    ],
)
def test_parse(
    walk: str,
    detected_section: SimpleSNMPSection,
    as_path: typing.Callable[[str], Path],
) -> None:
    # Act
    section = get_parsed_snmp_section(detected_section, as_path(walk))

    # Assert
    assert section is not None


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (WALK_MCAFEE, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_MCAFEE_2, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (WALK_SKYHIGH, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
        (WALK_SKYHIGH_2, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
    ],
)
def test_discovery(
    walk: str,
    detected_section: SimpleSNMPSection,
    as_path: typing.Callable[[str], Path],
) -> None:
    # Assemble
    section = get_parsed_snmp_section(detected_section, as_path(walk))
    assert section is not None

    # Act
    services = list(mcafee_webgateway.discover_webgateway(section))

    # Assert
    assert services == [Service()]


@pytest.mark.parametrize(
    "walk, detected_section, params, expected_results",
    [
        pytest.param(
            WALK_MCAFEE,
            mcafee_webgateway.snmp_section_mcafee_webgateway,
            {},
            [
                Result(state=State.OK, summary="Infections: 8.0/s"),
                Metric(name="infections_rate", value=8.0),
                Result(state=State.OK, summary="Connections blocked: 18.0/s"),
                Metric(name="connections_blocked_rate", value=18.0),
            ],
            id="No levels",
        ),
        pytest.param(
            WALK_MCAFEE,
            mcafee_webgateway.snmp_section_mcafee_webgateway,
            {"infections": (5, 10), "connections_blocked": (10, 15)},
            [
                Result(
                    state=State.WARN,
                    summary="Infections: 8.0/s (warn/crit at 5.0/s/10.0/s)",
                ),
                Metric(name="infections_rate", value=8.0, levels=(5.0, 10.0)),
                Result(
                    state=State.CRIT,
                    summary="Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)",
                ),
                Metric(name="connections_blocked_rate", value=18.0, levels=(10.0, 15.0)),
            ],
            id="Warn and Crit",
        ),
        pytest.param(
            WALK_SKYHIGH,
            mcafee_webgateway.snmp_section_skyhigh_security_webgateway,
            {"infections": (5, 10), "connections_blocked": (10, 15)},
            [
                Result(
                    state=State.WARN,
                    summary="Infections: 8.0/s (warn/crit at 5.0/s/10.0/s)",
                ),
                Metric(name="infections_rate", value=8.0, levels=(5.0, 10.0)),
                Result(
                    state=State.CRIT,
                    summary="Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)",
                ),
                Metric(name="connections_blocked_rate", value=18.0, levels=(10.0, 15.0)),
            ],
            id="Warn and Crit",
        ),
        pytest.param(
            WALK_MCAFEE_2,
            mcafee_webgateway.snmp_section_mcafee_webgateway,
            {},
            [
                Result(state=State.OK, summary="Connections blocked: 18.0/s"),
                Metric(name="connections_blocked_rate", value=18.0),
            ],
            id="One missing",
        ),
    ],
)
def test_check_results(
    walk: str,
    detected_section: SimpleSNMPSection,
    params: mcafee_webgateway.Params,
    expected_results: list[object],
    as_path: typing.Callable[[str], Path],
) -> None:
    # Assemble
    section = get_parsed_snmp_section(detected_section, as_path(walk))
    assert section is not None
    now = 2.0
    value_store = {
        "check_mcafee_webgateway.infections": (now - 1.0, 2),
        "check_mcafee_webgateway.connections_blocked": (now - 1.0, 2),
    }

    # Act
    results = list(mcafee_webgateway._check_webgateway(now, value_store, params, section))

    # Assert
    assert results == expected_results
