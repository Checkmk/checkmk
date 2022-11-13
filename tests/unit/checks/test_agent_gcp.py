#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest
from freezegun import freeze_time

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


@freeze_time("2022-01-12")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "project": "test",
                "credentials": "definitely some json",
                "services": ["gcs", "run"],
                "health": False,
            },
            [
                "--project",
                "test",
                "--credentials",
                "definitely some json",
                "--date",
                "2022-01-12",
                "--services",
                "gcs",
                "run",
                "--piggy-back-prefix",
                "test",
            ],
            id="minimal case",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": "definitely some json",
                "cost": {"tableid": "checkmk"},
                "services": [],
                "health": False,
            },
            [
                "--project",
                "test",
                "--credentials",
                "definitely some json",
                "--date",
                "2022-01-12",
                "--cost_table",
                "checkmk",
                "--piggy-back-prefix",
                "test",
            ],
            id="cost monitoring only",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": "definitely some json",
                "cost": {"tableid": "checkmk"},
                "services": ["gcs"],
                "health": True,
            },
            [
                "--project",
                "test",
                "--credentials",
                "definitely some json",
                "--date",
                "2022-01-12",
                "--cost_table",
                "checkmk",
                "--monitor_health",
                "--services",
                "gcs",
                "--piggy-back-prefix",
                "test",
            ],
            id="cost monitoring and checks",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": "definitely some json",
                "services": [],
                "health": False,
                "piggyback": {"prefix": "custom-prefix", "piggyback_services": ["gce"]},
            },
            [
                "--project",
                "test",
                "--credentials",
                "definitely some json",
                "--date",
                "2022-01-12",
                "--services",
                "gce",
                "--piggy-back-prefix",
                "custom-prefix",
            ],
            id="piggyback prefix and services",
        ),
    ],
)
def test_gcp_argument_parsing(
    params: Mapping[str, Any],
    expected_result: Sequence[str],
) -> None:
    assert (
        SpecialAgent("agent_gcp").argument_func(
            params,
            "testhost",
            "address",
        )
        == expected_result
    )
