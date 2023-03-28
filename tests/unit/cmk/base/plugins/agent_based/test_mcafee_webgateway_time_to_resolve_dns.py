#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.testlib.snmp import get_parsed_snmp_section, snmp_is_detected

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import SectionName

from cmk.base.plugins.agent_based import mcafee_webgateway_time_to_resolve_dns
from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils import mcafee_gateway

WALK = """
.1.3.6.1.2.1.1.1.0 McAfee Web Gateway 7
.1.3.6.1.4.1.1230.2.7.2.5.1.0 1
.1.3.6.1.4.1.1230.2.7.2.5.2.0 16
.1.3.6.1.4.1.1230.2.7.2.5.3.0 35
.1.3.6.1.4.1.1230.2.7.2.5.4.0 0
.1.3.6.1.4.1.1230.2.7.2.5.5.0 0
.1.3.6.1.4.1.1230.2.7.2.5.6.0 2000
.1.3.6.1.4.1.1230.2.7.2.5.7.0 2
.1.3.6.1.4.1.1230.2.7.2.5.8.0 177073
.1.3.6.1.4.1.1230.2.7.2.5.9.0 14
.1.3.6.1.4.1.1230.2.7.2.5.10.0 177073
.1.3.6.1.4.1.1230.2.7.2.5.11.0 177073
.1.3.6.1.4.1.1230.2.7.2.5.12.0 23
.1.3.6.1.4.1.1230.2.7.2.5.13.0 23
.1.3.6.1.4.1.1230.2.7.2.5.14.0 23
.1.3.6.1.4.1.1230.2.7.2.5.15.0 32
"""


def test_detect(fix_register: FixRegister, as_path: Callable[[str], Path]) -> None:
    assert snmp_is_detected(SectionName("mcafee_webgateway_misc"), as_path(WALK))


def test_parse(fix_register: FixRegister, as_path: Callable[[str], Path]) -> None:
    # Act
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway_misc"), as_path(WALK))

    # Assert
    assert section is not None


def test_discovery(fix_register: FixRegister, as_path: Callable[[str], Path]) -> None:
    # Assemble
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway_misc"), as_path(WALK))
    assert section is not None

    # Act
    services = list(mcafee_webgateway_time_to_resolve_dns.discovery(section=section))

    # Assert
    assert services == [v1.Service()]


@pytest.mark.parametrize(
    "params_misc, expected_results",
    [
        pytest.param(
            {"time_to_resolve_dns": None},
            [
                v1.Result(state=v1.State.OK, summary="2 seconds"),
            ],
            id="No levels",
        ),
        pytest.param(
            {"time_to_resolve_dns": (3000, 3000)},
            [
                v1.Result(state=v1.State.OK, summary="2 seconds"),
            ],
            id="Levels, but OK",
        ),
        pytest.param(
            {"time_to_resolve_dns": (2000, 3000)},
            [
                v1.Result(
                    state=v1.State.WARN, summary="2 seconds (warn/crit at 2 seconds/3 seconds)"
                ),
            ],
            id="Critical",
        ),
        pytest.param(
            {"time_to_resolve_dns": (1000, 2000)},
            [
                v1.Result(
                    state=v1.State.CRIT, summary="2 seconds (warn/crit at 1 second/2 seconds)"
                ),
            ],
            id="Warning",
        ),
    ],
)
def test_check_results(
    fix_register: FixRegister,
    params_misc: dict[str, object],
    expected_results: list[v1.Result],
    as_path: Callable[[str], Path],
) -> None:
    # Assemble
    params = typing.cast(
        mcafee_gateway.MiscParams, mcafee_gateway.MISC_DEFAULT_PARAMS | params_misc
    )
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway_misc"), as_path(WALK))
    assert section is not None

    # Act
    results = [
        r
        for r in mcafee_webgateway_time_to_resolve_dns.check(params=params, section=section)
        if isinstance(r, v1.Result)
    ]

    # Assert
    assert results == expected_results


def test_check_metrics(fix_register: FixRegister, as_path: Callable[[str], Path]) -> None:
    # Assemble
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway_misc"), as_path(WALK))
    assert section is not None

    # Act
    metrics = [
        r
        for r in mcafee_webgateway_time_to_resolve_dns.check(
            params=mcafee_gateway.MISC_DEFAULT_PARAMS, section=section
        )
        if isinstance(r, v1.Metric)
    ]

    # Assert
    assert metrics == [v1.Metric("time_to_resolve_dns", 2.0, levels=(1.5, 2.0))]
