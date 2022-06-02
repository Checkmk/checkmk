#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Sequence, Union

import pytest

from cmk.base.api.agent_based.checking_classes import Metric
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.sentry_pdu import check_sentry_pdu, discovery_sentry_pdu, PDU

pytestmark = pytest.mark.checks

_SECTION = {
    "TowerA_InfeedA": PDU(state="on", power=1097),
    "TowerA_InfeedB": PDU(state="on", power=261),
    "TowerA_InfeedC": PDU(state="on", power=0),
    "TowerB_InfeedA": PDU(state="on", power=665),
    "TowerB_InfeedB": PDU(state="unknown", power=203),
    "TowerB_InfeedC": PDU(state="on", power=0),
}


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
            id="unknown status",
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
