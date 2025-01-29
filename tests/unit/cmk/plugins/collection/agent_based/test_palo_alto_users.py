#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.collection.agent_based.palo_alto_users import (
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


@pytest.mark.parametrize(
    "params, section, expected_result",
    [
        pytest.param(
            {"levels": "ignore"},
            Section(num_users=1000, max_users=2000),
            [
                Result(state=State.OK, summary="Number of logged in users: 50.00% - 1000 of 2000"),
                Result(state=State.OK, notice="Absolute number of users: 1000"),
                Metric("num_user", 1000.0),
                Result(state=State.OK, notice="Relative number of users: 50.00%"),
                Metric("max_user", 2000.0),
            ],
            id="no_levels",
        ),
        pytest.param(
            {"levels": ("perc_user", (80, 90))},
            Section(num_users=1000, max_users=2000),
            [
                Result(state=State.OK, summary="Number of logged in users: 50.00% - 1000 of 2000"),
                Result(state=State.OK, notice="Absolute number of users: 1000"),
                Metric("num_user", 1000.0),
                Result(state=State.OK, notice="Relative number of users: 50.00%"),
                Metric("max_user", 2000.0),
            ],
            id="relative_levels_ok",
        ),
        pytest.param(
            {"levels": ("perc_user", (80, 90))},
            Section(num_users=1900, max_users=2000),
            [
                Result(state=State.OK, summary="Number of logged in users: 95.00% - 1900 of 2000"),
                Result(state=State.OK, notice="Absolute number of users: 1900"),
                Metric("num_user", 1900.0),
                Result(
                    state=State.CRIT,
                    summary="Relative number of users: 95.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("max_user", 2000.0),
            ],
            id="relative_levels_crit",
        ),
        pytest.param(
            {"levels": ("abs_user", (1600, 1800))},
            Section(num_users=1000, max_users=2000),
            [
                Result(state=State.OK, summary="Number of logged in users: 50.00% - 1000 of 2000"),
                Result(state=State.OK, notice="Absolute number of users: 1000"),
                Metric("num_user", 1000.0, levels=(1600.0, 1800.0)),
                Result(state=State.OK, notice="Relative number of users: 50.00%"),
                Metric("max_user", 2000.0),
            ],
            id="absolute_levels_ok",
        ),
        pytest.param(
            {"levels": ("abs_user", (1600, 1800))},
            Section(num_users=1900, max_users=2000),
            [
                Result(state=State.OK, summary="Number of logged in users: 95.00% - 1900 of 2000"),
                Result(
                    state=State.CRIT,
                    summary="Absolute number of users: 1900 (warn/crit at 1600/1800)",
                ),
                Metric("num_user", 1900.0, levels=(1600.0, 1800.0)),
                Result(state=State.OK, notice="Relative number of users: 95.00%"),
                Metric("max_user", 2000.0),
            ],
            id="absolute_levels_crit",
        ),
    ],
)
def test_check(
    params: Mapping[str, Any],
    section: Section,
    expected_result: CheckResult,
) -> None:
    assert expected_result == list(check(params, section))


@pytest.mark.parametrize(
    "params, section, expected_result",
    [
        pytest.param(
            {"levels": "ignore"},
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
        ),
        pytest.param(
            {"levels": "ignore"},
            {"cluster_a": Section(num_users=1, max_users=5), "cluster_b": None},
            [
                Result(state=State.OK, summary="Number of logged in users: 20.00% - 1 of 5"),
                Result(state=State.OK, notice="Absolute number of users: 1"),
                Metric("num_user", 1.0),
                Result(state=State.OK, notice="Relative number of users: 20.00%"),
                Metric("max_user", 5.0),
            ],
        ),
    ],
)
def test_cluster_check(
    params: Mapping[str, Any],
    section: Mapping[str, Section | None],
    expected_result: CheckResult,
) -> None:
    assert expected_result == list(cluster_check(params, section))
