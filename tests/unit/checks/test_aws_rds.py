#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "section, discovery_result",
    [
        pytest.param(
            {"disk": {"DatabaseConnections": 10.0}},
            [Service(item="disk")],
            id="For every disk in the section a Service with no item is discovered.",
        ),
        pytest.param(
            {},
            [],
            id="If the section is empty, no Services are discovered.",
        ),
    ],
)
def test_aws_rds_connections_discovery(
    section: Mapping[str, Mapping[str, float]],
    discovery_result: Sequence[Service],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_connections")]
    assert list(check.discovery_function(section)) == discovery_result


def test_check_aws_rds_connections_item_not_found(
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_connections")]
    assert (
        list(
            check.check_function(
                item="disk",
                params={},
                section={},
            )
        )
        == []
    )


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"disk": {"DatabaseConnections": 10.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.OK, summary="In use: 10.00"),
                Metric("aws_rds_connections", 10.0, levels=(90.0, 95.0)),
            ],
            id="If the levels are below the warn/crit levels, the check state will be OK with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"DatabaseConnections": 92.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.WARN, summary="In use: 92.00 (warn/crit at 90.00/95.00)"),
                Metric("aws_rds_connections", 92.00, levels=(90.0, 95.0)),
            ],
            id="If the levels are above the warn levels, the check state will be WARN with a appropriate description.",
        ),
        pytest.param(
            {"disk": {"DatabaseConnections": 97.0}},
            {"levels": (90, 95)},
            [
                Result(state=State.CRIT, summary="In use: 97.00 (warn/crit at 90.00/95.00)"),
                Metric("aws_rds_connections", 97.0, levels=(90.0, 95.0)),
            ],
            id="If the levels are above the crit levels, the check state will be CRIT with a appropriate description.",
        ),
    ],
)
def test_check_aws_rds_connections(
    section: Mapping[str, Mapping[str, float]],
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result | Metric],
    fix_register: FixRegister,
) -> None:
    check = fix_register.check_plugins[CheckPluginName("aws_rds_connections")]

    check_result = list(
        check.check_function(
            item="disk",
            params=params,
            section=section,
        )
    )
    assert check_result == expected_check_result
