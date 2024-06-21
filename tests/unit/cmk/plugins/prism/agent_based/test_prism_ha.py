#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_ha import check_prism_ha, discovery_prism_ha

SECTION = {
    "failover_enabled": True,
    "failover_in_progress_host_uuids": None,
    "ha_state": "BestEffort",
    "logical_timestamp": 0,
    "num_host_failures_to_tolerate": 0,
    "reservation_type": "NoReservations",
    "reserved_host_uuids": None,
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(),
            ],
            id="The service is discovered if data exists.",
        ),
        pytest.param({}, [], id="No services is discovered if no data exists."),
    ],
)
def test_discovery_prism_ha(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_ha(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["section", "expected_check_result"],
    [
        pytest.param(
            SECTION,
            [
                Result(state=State.OK, summary="State: BestEffort"),
            ],
            id="If state is as expected, service is OK.",
        ),
        pytest.param(
            {},
            [],
            id="No data",
        ),
    ],
)
def test_check_prism_ha(
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_ha(
                section=section,
            )
        )
        == expected_check_result
    )
