#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_remote_support import (
    check_prism_remote_support,
    discovery_prism_remote_support,
)

SECTION = {"enable": {"duration": 0, "enabled": False}}


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
def test_discovery_prism_remote_support(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_remote_support(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["params", "section", "expected_check_result"],
    [
        pytest.param(
            {"tunnel_state": False},
            SECTION,
            [
                Result(state=State.OK, summary="Remote Tunnel is disabled"),
            ],
            id="If tunnel is not active the service is OK.",
        ),
        pytest.param(
            {"tunnel_state": True},
            SECTION,
            [
                Result(state=State.WARN, summary="Remote Tunnel is disabled"),
            ],
            id="If tunnel state is different from expected state the check is WARN.",
        ),
    ],
)
def test_check_prism_remote_support(
    params: Mapping[str, Any],
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_prism_remote_support(
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
