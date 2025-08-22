#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.azure.agent_based.azure_redis import check_plugin_azure_redis
from cmk.plugins.lib.azure import Resource, Section


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            {
                "rickcmktest": Resource(
                    id=(
                        "/subscriptions/ba9f74ff-6a4c-41e0-ab55-15c7fe79632f/resourceGroups/gemdev/"
                        "providers/Microsoft.Cache/Redis/rickcmktest"
                    ),
                    name="rickcmktest",
                    type="Microsoft.Cache/Redis",
                    group="gemdev",
                    kind=None,
                    location="centralus",
                    tags={},
                    properties={},
                    specific_info={},
                    metrics={},
                    subscription="ba9f74ff-6a4c-41e0-ab55-15c7fe79632f",
                )
            },
            "rickcmktest",
            [
                Result(
                    state=State.OK,
                    summary="Location: centralus",
                ),
            ],
            id="generic service",
        ),
    ],
)
def test_check_azure_redis(
    section: Section,
    item: str,
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_plugin_azure_redis.check_function(item, section)) == expected_result
