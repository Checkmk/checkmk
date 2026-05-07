#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, SimpleSNMPSection, State, StringTable
from cmk.plugins.mcafee.agent_based import mcafee_webgateway

WALK_MCAFEE: dict[str, str] = {
    ".1.3.6.1.2.1.1.1.0": "McAfee Web Gateway 7",
    ".1.3.6.1.4.1.1230.2.7.2.1.2.0": "10",
    ".1.3.6.1.4.1.1230.2.7.2.1.5.0": "20",
}

WALK_MCAFEE_2: dict[str, str] = {
    ".1.3.6.1.2.1.1.1.0": "McAfee Web Gateway 7",
    ".1.3.6.1.4.1.1230.2.7.2.1.5.0": "20",
}

WALK_SKYHIGH: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.59732.2.7.1.1",
    ".1.3.6.1.4.1.59732.2.7.2.1.2.0": "10",
    ".1.3.6.1.4.1.59732.2.7.2.1.5.0": "20",
}

WALK_SKYHIGH_2: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.59732.2.7.1.1",
    ".1.3.6.1.4.1.59732.2.7.2.1.5.0": "20",
}

TABLE_MCAFEE: StringTable = [["10", "20"]]
TABLE_MCAFEE_2: StringTable = [["", "20"]]
TABLE_SKYHIGH: StringTable = [["10", "20"]]
TABLE_SKYHIGH_2: StringTable = [["", "20"]]


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
    walk: dict[str, str],
    detected_section: SimpleSNMPSection,
) -> None:
    assert evaluate_snmp_detection(detect_spec=detected_section.detect, oid_value_getter=walk.get)


@pytest.mark.parametrize(
    "table, detected_section",
    [
        (TABLE_MCAFEE, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (TABLE_MCAFEE_2, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (TABLE_SKYHIGH, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
        (TABLE_SKYHIGH_2, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
    ],
)
def test_parse(
    table: StringTable,
    detected_section: SimpleSNMPSection,
) -> None:
    # Act
    section = detected_section.parse_function([table])

    # Assert
    assert section is not None


@pytest.mark.parametrize(
    "table, detected_section",
    [
        (TABLE_MCAFEE, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (TABLE_MCAFEE_2, mcafee_webgateway.snmp_section_mcafee_webgateway),
        (TABLE_SKYHIGH, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
        (TABLE_SKYHIGH_2, mcafee_webgateway.snmp_section_skyhigh_security_webgateway),
    ],
)
def test_discovery(
    table: StringTable,
    detected_section: SimpleSNMPSection,
) -> None:
    # Assemble
    section = detected_section.parse_function([table])
    assert section is not None

    # Act
    services = list(mcafee_webgateway.discover_webgateway(section))

    # Assert
    assert services == [Service()]


@pytest.mark.parametrize(
    "table, detected_section, params, expected_results",
    [
        pytest.param(
            TABLE_MCAFEE,
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
            TABLE_MCAFEE,
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
            TABLE_SKYHIGH,
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
            TABLE_MCAFEE_2,
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
    table: StringTable,
    detected_section: SimpleSNMPSection,
    params: mcafee_webgateway.Params,
    expected_results: list[object],
) -> None:
    # Assemble
    section = detected_section.parse_function([table])
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
