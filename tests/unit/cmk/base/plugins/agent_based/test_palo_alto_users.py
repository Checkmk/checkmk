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
    assert Section(num_users=40, max_users=2048) == parse([["2048", "40"]])


def test_discover() -> None:
    assert [Service()] == list(discover(Section(num_users=41, max_users=2048)))


def test_check() -> None:
    assert [
        Result(state=State.OK, summary="Number of logged in users: 50.00% - 1000 of 2000"),
        Result(state=State.OK, notice="Absolute number of users: 1000"),
        Metric("num_user", 1000.0),
        Result(state=State.OK, notice="Relative number of users: 50.00%"),
        Metric("max_user", 2000.0),
    ] == list(check(Section(num_users=1000, max_users=2000)))


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            {
                "cluster_a": Section(num_users=1, max_users=5),
                "cluster_b": Section(num_users=2, max_users=5),
            },
            [
                Result(state=State.OK, summary="Number of logged in users: 30.00% - 3 of 10"),
                Result(state=State.OK, notice="Absolute number of users: 3"),
                Metric("num_user", 3.0),
                Result(state=State.OK, notice="Relative number of users: 30.00%"),
                Metric("max_user", 10.0),
            ],
            id="both_clusters_active",
        ),
        pytest.param(
            {"cluster_a": Section(num_users=1, max_users=5), "cluster_b": None},
            [
                Result(state=State.OK, summary="Number of logged in users: 20.00% - 1 of 5"),
                Result(state=State.OK, notice="Absolute number of users: 1"),
                Metric("num_user", 1.0),
                Result(state=State.OK, notice="Relative number of users: 20.00%"),
                Metric("max_user", 5.0),
            ],
            id="single_cluster_active",
        ),
    ],
)
def test_cluster_check(
    section: Mapping[str, Optional[Section]], expected_result: CheckResult
) -> None:
    assert expected_result == list(cluster_check(section))
