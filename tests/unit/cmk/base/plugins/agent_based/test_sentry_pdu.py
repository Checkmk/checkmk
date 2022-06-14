#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Union

import pytest

from cmk.base.api.agent_based.checking_classes import Metric
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.sentry_pdu import (
    check_sentry_pdu,
    check_sentry_pdu_v4,
    discovery_sentry_pdu,
    parse_sentry_pdu,
    PDU,
)

pytestmark = pytest.mark.checks

_SECTION = {
    "TowerA_InfeedA": PDU(state=1, power=1097),
    "TowerA_InfeedB": PDU(state=1, power=261),
    "TowerA_InfeedC": PDU(state=1, power=0),
    "TowerB_InfeedA": PDU(state=1, power=665),
    "TowerB_InfeedB": PDU(state=21, power=203),
    "TowerB_InfeedC": PDU(state=1, power=0),
}

_SECTION_V4 = {
    "TowerA_InfeedA": PDU(state=18, power=1097),
    "TowerA_InfeedB": PDU(state=33, power=261),
}


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        ([["PDU_A", "0", "250"]], {"PDU_A": PDU(state=0, power=250)}),
        (
            [["PDU_A", "0", "250"], ["PDU_B", "5", "150"]],
            {"PDU_A": PDU(state=0, power=250), "PDU_B": PDU(state=5, power=150)},
        ),
    ],
)
def test_parse_sentry_pdu(string_table, expected_section) -> None:
    section = parse_sentry_pdu(string_table)
    assert section == expected_section


def test_inventory_sentry_pdu() -> None:
    assert list(discovery_sentry_pdu(_SECTION)) == [
        Service(item="TowerA_InfeedA"),
        Service(item="TowerA_InfeedB"),
        Service(item="TowerA_InfeedC"),
        Service(item="TowerB_InfeedA"),
        Service(item="TowerB_InfeedB"),
        Service(item="TowerB_InfeedC"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "TowerA_InfeedA",
            {},
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.OK, summary="Power: 1097 Watt"),
                Metric(name="power", value=1097),
            ],
            id="discovered params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {
                "required_state": "on",
            },
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.OK, summary="Power: 1097 Watt"),
                Metric(name="power", value=1097),
            ],
            id="discovered and check params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {
                "required_state": "off",
            },
            [
                Result(state=State.CRIT, summary="Status: on"),
                Result(state=State.OK, summary="Power: 1097 Watt"),
                Metric(name="power", value=1097),
            ],
            id="discovered and check params, not ok",
        ),
        pytest.param(
            "TowerB_InfeedB",
            {},
            [
                Result(state=State.UNKNOWN, summary="Status: unknown"),
                Result(state=State.OK, summary="Power: 203 Watt"),
                Metric(name="power", value=203),
            ],
            id="unknown status",
        ),
        pytest.param(
            "TowerA_InfeedD",
            {},
            [],
            id="unknown item",
        ),
    ],
)
def test_check_sentry_pdu(
    item: str,
    params: Mapping[str, str],
    expected_result: Sequence[Union[Metric, Result]],
) -> None:
    assert (
        list(
            check_sentry_pdu(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "TowerA_InfeedA",
            [
                Result(state=State.CRIT, summary="Status: alarm"),
                Result(state=State.OK, summary="Power: 1097 Watt"),
                Metric(name="power", value=1097),
            ],
            id="known status",
        ),
        pytest.param(
            "TowerA_InfeedB",
            [
                Result(state=State.UNKNOWN, summary="Status: 33"),
                Result(state=State.OK, summary="Power: 261 Watt"),
                Metric(name="power", value=261),
            ],
            id="unknown status",
        ),
        pytest.param(
            "TowerA_InfeedD",
            [],
            id="unknown item",
        ),
    ],
)
def test_check_sentry_pdu_v4(
    item: str,
    expected_result: Sequence[Union[Metric, Result]],
) -> None:
    assert list(check_sentry_pdu_v4(item, _SECTION_V4)) == expected_result
