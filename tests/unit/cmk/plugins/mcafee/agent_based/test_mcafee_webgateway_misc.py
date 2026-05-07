#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

import typing

import pytest

from cmk.agent_based.internal import evaluate_snmp_detection
from cmk.agent_based.v2 import Metric, Result, Service, SimpleSNMPSection, State, StringTable
from cmk.plugins.mcafee import libgateway
from cmk.plugins.mcafee.agent_based import (
    mcafee_webgateway_misc,
    mcafee_webgateway_misc_section,
)

# SUP-13087
WALK_MCAFEE: dict[str, str] = {
    ".1.3.6.1.2.1.1.1.0": "McAfee Web Gateway 7;Hyper-V;Microsoft Corporation",
    ".1.3.6.1.4.1.1230.2.7.2.5.1.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.2.0": "2",
    ".1.3.6.1.4.1.1230.2.7.2.5.3.0": "2",
    ".1.3.6.1.4.1.1230.2.7.2.5.4.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.5.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.6.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.7.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.8.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.9.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.10.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.11.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.12.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.13.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.14.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.15.0": "41",
}

WALK_SKYHIGH: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.59732.2.7.1.1",
    ".1.3.6.1.4.1.59732.2.7.2.5.1.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.2.0": "2",
    ".1.3.6.1.4.1.59732.2.7.2.5.3.0": "2",
    ".1.3.6.1.4.1.59732.2.7.2.5.4.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.5.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.6.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.7.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.8.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.9.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.10.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.11.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.12.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.13.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.14.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.15.0": "41",
}

TABLE_MISC: StringTable = [["2", "2", "0", "0"]]
TABLE_MISC_INVALID: StringTable = [["", "", "", ""]]


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (
            WALK_MCAFEE,
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
        ),
        (
            WALK_SKYHIGH,
            mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
        ),
    ],
)
def test_detect(walk: dict[str, str], detected_section: SimpleSNMPSection) -> None:
    assert evaluate_snmp_detection(detect_spec=detected_section.detect, oid_value_getter=walk.get)


@pytest.mark.parametrize(
    "detected_section",
    [
        mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
        mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
    ],
)
def test_parse(detected_section: SimpleSNMPSection) -> None:
    # Act
    section = detected_section.parse_function([TABLE_MISC])

    # Assert
    assert section is not None


@pytest.mark.parametrize(
    "detected_section",
    [
        mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
        mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
    ],
)
def test_discovery(detected_section: SimpleSNMPSection) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_MISC])
    assert section is not None

    # Act
    services = list(mcafee_webgateway_misc.discovery_webgateway_misc(section=section))

    # Assert
    assert services == [Service()]


@pytest.mark.parametrize(
    "detected_section, params_misc, expected_results",
    [
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"clients": None, "network_sockets": None},
            [
                Result(state=State.OK, summary="Clients: 2"),
                Result(state=State.OK, summary="Open network sockets: 2"),
            ],
            id="No levels mcafee",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
            {"clients": None, "network_sockets": None},
            [
                Result(state=State.OK, summary="Clients: 2"),
                Result(state=State.OK, summary="Open network sockets: 2"),
            ],
            id="No levels skyhigh",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"clients": (3, 3), "network_sockets": (3, 3)},
            [
                Result(state=State.OK, summary="Clients: 2"),
                Result(state=State.OK, summary="Open network sockets: 2"),
            ],
            id="Levels, but OK",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"clients": (2, 3), "network_sockets": (2, 3)},
            [
                Result(state=State.WARN, summary="Clients: 2 (warn/crit at 2/3)"),
                Result(state=State.WARN, summary="Open network sockets: 2 (warn/crit at 2/3)"),
            ],
            id="Critical",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
            {"clients": (2, 3), "network_sockets": (2, 3)},
            [
                Result(state=State.WARN, summary="Clients: 2 (warn/crit at 2/3)"),
                Result(state=State.WARN, summary="Open network sockets: 2 (warn/crit at 2/3)"),
            ],
            id="Critical skyhigh",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"clients": (1, 2), "network_sockets": (1, 2)},
            [
                Result(state=State.CRIT, summary="Clients: 2 (warn/crit at 1/2)"),
                Result(state=State.CRIT, summary="Open network sockets: 2 (warn/crit at 1/2)"),
            ],
            id="Warning",
        ),
    ],
)
def test_check_results(
    detected_section: SimpleSNMPSection,
    params_misc: dict[str, object],
    expected_results: list[Result],
) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_MISC])
    assert section is not None
    params = typing.cast(libgateway.MiscParams, libgateway.MISC_DEFAULT_PARAMS | params_misc)

    # Act
    results = [
        r
        for r in mcafee_webgateway_misc.check_webgateway_misc(params=params, section=section)
        if isinstance(r, Result)
    ]

    # Assert
    assert results == expected_results


def test_check_metrics() -> None:
    # Assemble
    section = mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc.parse_function(
        [TABLE_MISC]
    )
    assert section is not None

    # Act
    metrics = [
        r
        for r in mcafee_webgateway_misc.check_webgateway_misc(
            params=libgateway.MISC_DEFAULT_PARAMS, section=section
        )
        if isinstance(r, Metric)
    ]

    # Assert
    assert metrics == [Metric("connections", 2.0), Metric("open_network_sockets", 2.0)]


def test_check_invalid_values() -> None:
    # Assemble
    # This walk is made up.
    section = mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc.parse_function(
        [TABLE_MISC_INVALID]
    )

    # Assume
    assert section is not None

    # Act
    results = list(
        mcafee_webgateway_misc.check_webgateway_misc(
            params=libgateway.MISC_DEFAULT_PARAMS,
            section=section,
        )
    )

    # Assert
    assert not results
