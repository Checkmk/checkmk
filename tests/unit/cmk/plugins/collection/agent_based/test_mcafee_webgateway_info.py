#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.agent_based.v2 import Result, Service, SimpleSNMPSection, State
from cmk.plugins.collection.agent_based import mcafee_webgateway_info
from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)

WALK_MCAFEE = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7;Hyper-V;Microsoft Corporation
.1.3.6.1.2.1.1.2.0 1.3.6.1.4.1.1230.2.7.1.1
.1.3.6.1.4.1.1230.2.7.1.3.0 7.6.1.2.0
.1.3.6.1.4.1.1230.2.7.1.9.0 64221
"""

WALK_SKYHIGH = """
.1.3.6.1.2.1.1.2.0 1.3.6.1.4.1.59732.2.7.1.1
.1.3.6.1.4.1.59732.2.7.1.3.0 7.6.1.2.0
.1.3.6.1.4.1.59732.2.7.1.9.0 64221
"""


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (
            WALK_MCAFEE,
            mcafee_webgateway_info.snmp_section_mcafee_webgateway_info,
        ),
        (
            WALK_SKYHIGH,
            mcafee_webgateway_info.snmp_section_skyhigh_security_webgateway_info,
        ),
    ],
)
def test_detect(
    walk: str, detected_section: SimpleSNMPSection, as_path: Callable[[str], Path]
) -> None:
    assert snmp_is_detected(detected_section, as_path(walk))


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (
            WALK_MCAFEE,
            mcafee_webgateway_info.snmp_section_mcafee_webgateway_info,
        ),
        (
            WALK_SKYHIGH,
            mcafee_webgateway_info.snmp_section_skyhigh_security_webgateway_info,
        ),
    ],
)
def test_parse(
    walk: str, detected_section: SimpleSNMPSection, as_path: Callable[[str], Path]
) -> None:
    section = get_parsed_snmp_section(detected_section, as_path(walk))

    assert section is not None


@pytest.mark.parametrize(
    "walk, detected_section",
    [
        (
            WALK_MCAFEE,
            mcafee_webgateway_info.snmp_section_mcafee_webgateway_info,
        ),
        (
            WALK_SKYHIGH,
            mcafee_webgateway_info.snmp_section_skyhigh_security_webgateway_info,
        ),
    ],
)
def test_discovery(
    walk: str, detected_section: SimpleSNMPSection, as_path: Callable[[str], Path]
) -> None:
    section = get_parsed_snmp_section(detected_section, as_path(walk))
    assert section is not None

    services = list(mcafee_webgateway_info.discovery_webgateway_info(section=section))

    assert services == [Service()]


@pytest.mark.parametrize(
    "walk, detected_section, expected_results",
    [
        pytest.param(
            WALK_MCAFEE,
            mcafee_webgateway_info.snmp_section_mcafee_webgateway_info,
            [Result(state=State.OK, summary="Product version: 7.6.1.2.0, Revision: 64221")],
            id="Check mcafee",
        ),
        pytest.param(
            WALK_SKYHIGH,
            mcafee_webgateway_info.snmp_section_skyhigh_security_webgateway_info,
            [Result(state=State.OK, summary="Product version: 7.6.1.2.0, Revision: 64221")],
            id="Check skyhigh",
        ),
    ],
)
def test_check_results(
    walk: str,
    detected_section: SimpleSNMPSection,
    expected_results: list[Result],
    as_path: Callable[[str], Path],
) -> None:
    section = get_parsed_snmp_section(detected_section, as_path(walk))
    assert section is not None

    results = [
        r
        for r in mcafee_webgateway_info.check_webgateway_info(section=section)
        if isinstance(r, Result)
    ]

    assert results == expected_results
