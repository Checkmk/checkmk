#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from pathlib import Path

import freezegun
import pytest

from tests.testlib.snmp import get_parsed_snmp_section, snmp_is_detected

from tests.unit.conftest import FixRegister

from cmk.utils.sectionname import SectionName

from cmk.base import item_state
from cmk.base.legacy_checks import mcafee_webgateway

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
    services = list(mcafee_webgateway.inventory_mcafee_gateway_generic(section))

    # Assert
    assert services == [(None, {})]


@freezegun.freeze_time("2019-05-27T05:30:07")
@pytest.mark.parametrize(
    "walk, params, expected_results",
    [
        pytest.param(
            WALK,
            {},
            [
                (
                    0,
                    "Infections: 8.0/s",
                    [("infections_rate", 8.0, None, None)],
                ),
                (
                    0,
                    "Connections blocked: 18.0/s",
                    [("connections_blocked_rate", 18.0, None, None)],
                ),
            ],
            id="No levels",
        ),
        pytest.param(
            WALK,
            {"infections": (5, 10), "connections_blocked": (10, 15)},
            [
                (
                    1,
                    "Infections: 8.0/s (warn/crit at 5.0/s/10.0/s)",
                    [("infections_rate", 8.0, 5.0, 10.0)],
                ),
                (
                    2,
                    "Connections blocked: 18.0/s (warn/crit at 10.0/s/15.0/s)",
                    [("connections_blocked_rate", 18.0, 10.0, 15.0)],
                ),
            ],
            id="Warn and Crit",
        ),
        pytest.param(
            WALK_2,
            {},
            [
                (
                    0,
                    "Connections blocked: 18.0/s",
                    [("connections_blocked_rate", 18.0, None, None)],
                ),
            ],
            id="One missing",
        ),
    ],
)
def test_check_results(
    walk: str,
    monkeypatch: pytest.MonkeyPatch,
    fix_register: FixRegister,
    params: dict[str, object],
    expected_results: list[typing.Any],
    as_path: typing.Callable[[str], Path],
) -> None:
    # Assemble
    section = get_parsed_snmp_section(SectionName("mcafee_webgateway"), as_path(walk))
    assert section is not None

    value_store = {
        "check_mcafee_webgateway.infections": (1558935006.0, 2),
        "check_mcafee_webgateway.connections_blocked": (1558935006.0, 2),
    }
    # Act
    monkeypatch.setattr(item_state, "get_value_store", lambda: value_store)
    results = list(mcafee_webgateway.check_mcafee_webgateway(None, params, section))

    # Assert
    assert results == expected_results
