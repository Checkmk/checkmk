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
    mcafee_webgateway_misc_section,
    mcafee_webgateway_time_consumed_by_rule_engine,
)

WALK_MCAFEE: dict[str, str] = {
    ".1.3.6.1.2.1.1.1.0": "McAfee Web Gateway 7",
    ".1.3.6.1.4.1.1230.2.7.2.5.1.0": "1",
    ".1.3.6.1.4.1.1230.2.7.2.5.2.0": "16",
    ".1.3.6.1.4.1.1230.2.7.2.5.3.0": "35",
    ".1.3.6.1.4.1.1230.2.7.2.5.4.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.5.0": "0",
    ".1.3.6.1.4.1.1230.2.7.2.5.6.0": "2",
    ".1.3.6.1.4.1.1230.2.7.2.5.7.0": "2000",
    ".1.3.6.1.4.1.1230.2.7.2.5.8.0": "177073",
    ".1.3.6.1.4.1.1230.2.7.2.5.9.0": "14",
    ".1.3.6.1.4.1.1230.2.7.2.5.10.0": "177073",
    ".1.3.6.1.4.1.1230.2.7.2.5.11.0": "177073",
    ".1.3.6.1.4.1.1230.2.7.2.5.12.0": "23",
    ".1.3.6.1.4.1.1230.2.7.2.5.13.0": "23",
    ".1.3.6.1.4.1.1230.2.7.2.5.14.0": "23",
    ".1.3.6.1.4.1.1230.2.7.2.5.15.0": "32",
}

WALK_SKYHIGH: dict[str, str] = {
    ".1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.59732.2.7.1.1",
    ".1.3.6.1.4.1.59732.2.7.2.5.1.0": "1",
    ".1.3.6.1.4.1.59732.2.7.2.5.2.0": "16",
    ".1.3.6.1.4.1.59732.2.7.2.5.3.0": "35",
    ".1.3.6.1.4.1.59732.2.7.2.5.4.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.5.0": "0",
    ".1.3.6.1.4.1.59732.2.7.2.5.6.0": "2",
    ".1.3.6.1.4.1.59732.2.7.2.5.7.0": "2000",
    ".1.3.6.1.4.1.59732.2.7.2.5.8.0": "177073",
    ".1.3.6.1.4.1.59732.2.7.2.5.9.0": "14",
    ".1.3.6.1.4.1.59732.2.7.2.5.10.0": "177073",
    ".1.3.6.1.4.1.59732.2.7.2.5.11.0": "177073",
    ".1.3.6.1.4.1.59732.2.7.2.5.12.0": "23",
    ".1.3.6.1.4.1.59732.2.7.2.5.13.0": "23",
    ".1.3.6.1.4.1.59732.2.7.2.5.14.0": "23",
    ".1.3.6.1.4.1.59732.2.7.2.5.15.0": "32",
}

TABLE_TCR: StringTable = [["16", "35", "2", "2000"]]


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (WALK_MCAFEE, mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc),
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
    section = detected_section.parse_function([TABLE_TCR])

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
    section = detected_section.parse_function([TABLE_TCR])
    assert section is not None

    # Act
    services = list(mcafee_webgateway_time_consumed_by_rule_engine.discovery(section=section))

    # Assert
    assert services == [Service()]


@pytest.mark.parametrize(
    "detected_section, params_misc, expected_results",
    [
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"time_consumed_by_rule_engine": None},
            [
                Result(state=State.OK, summary="2 seconds"),
            ],
            id="No levels",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
            {"time_consumed_by_rule_engine": None},
            [
                Result(state=State.OK, summary="2 seconds"),
            ],
            id="No levels",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"time_consumed_by_rule_engine": (3000, 3000)},
            [
                Result(state=State.OK, summary="2 seconds"),
            ],
            id="Levels, but OK",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"time_consumed_by_rule_engine": (2000, 3000)},
            [
                Result(state=State.WARN, summary="2 seconds (warn/crit at 2 seconds/3 seconds)"),
            ],
            id="Critical",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
            {"time_consumed_by_rule_engine": (2000, 3000)},
            [
                Result(state=State.WARN, summary="2 seconds (warn/crit at 2 seconds/3 seconds)"),
            ],
            id="Critical",
        ),
        pytest.param(
            mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
            {"time_consumed_by_rule_engine": (1000, 2000)},
            [
                Result(state=State.CRIT, summary="2 seconds (warn/crit at 1 second/2 seconds)"),
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
    params = typing.cast(libgateway.MiscParams, libgateway.MISC_DEFAULT_PARAMS | params_misc)
    section = detected_section.parse_function([TABLE_TCR])
    assert section is not None

    # Act
    results = [
        r
        for r in mcafee_webgateway_time_consumed_by_rule_engine.check(
            params=params, section=section
        )
        if isinstance(r, Result)
    ]

    # Assert
    assert results == expected_results


@pytest.mark.parametrize(
    "detected_section",
    [
        mcafee_webgateway_misc_section.snmp_section_mcafee_webgateway_misc,
        mcafee_webgateway_misc_section.snmp_section_skyhigh_security_webgateway_misc,
    ],
)
def test_check_metrics(detected_section: SimpleSNMPSection) -> None:
    # Assemble
    section = detected_section.parse_function([TABLE_TCR])
    assert section is not None

    # Act
    metrics = [
        r
        for r in mcafee_webgateway_time_consumed_by_rule_engine.check(
            params=libgateway.MISC_DEFAULT_PARAMS, section=section
        )
        if isinstance(r, Metric)
    ]

    # Assert
    assert metrics == [Metric("time_consumed_by_rule_engine", 2.0, levels=(1.5, 2.0))]
