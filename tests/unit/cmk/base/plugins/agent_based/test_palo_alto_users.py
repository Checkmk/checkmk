#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.palo_alto_users import (
    check,
    cluster_check,
    discover,
    parse,
    Section,
)


def test_parse() -> None:
    assert Section(num_users=40) == parse([["40"]])


def test_discover() -> None:
    assert [Service()] == list(discover(Section(num_users=41)))


def test_check() -> None:
    assert [
        Result(state=State.OK, summary="Number of logged in users: 42"),
        Metric("num_user", 42.0),
    ] == list(check(Section(num_users=42)))


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "cluster_a": Section(num_users=1),
                "cluster_b": Section(num_users=2),
            },
            [
                Result(state=State.OK, summary="Number of logged in users: 3"),
                Metric("num_user", 3.0),
            ],
        ),
        pytest.param(
            {"cluster_a": Section(num_users=1), "cluster_b": None},
            [
                Result(state=State.OK, summary="Number of logged in users: 1"),
                Metric("num_user", 1.0),
            ],
        ),
    ],
)
def test_cluster_check(
    section: Mapping[str, Optional[Section]], expected_result: CheckResult
) -> None:
    assert expected_result == list(cluster_check(section))
