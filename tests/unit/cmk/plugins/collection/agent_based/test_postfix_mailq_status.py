#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.postfix_mailq_status import (
    check_postfix_mailq_status,
    discovery_postfix_mailq_status,
    parse_postfix_mailq_status,
    PostfixError,
    PostfixPid,
)


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, PostfixError | PostfixPid]:
    return parse_postfix_mailq_status(
        [
            ["postfix", " the Postfix mail system is running", " PID", " 12910"],
            [
                "postfix-external/postfix-script",
                " the Postfix mail system is running",
                " PID",
                " 12982",
            ],
            [
                "postfix-stopped/postfix-script",
                " PID file exists but instance is not running!",
            ],
            [
                "postfix-internal/postfix-script",
                " the Postfix mail system is running",
                " PID",
                " 13051",
            ],
            ["postfix-uat-cdi/postfix-script", " the Postfix mail system is not running"],
            ["postfix-other/postfix-script", " PID file exists but is not readable"],
        ]
    )


def test_discovery_postfix_mailq_status(section: Mapping[str, PostfixError | PostfixPid]) -> None:
    assert list(discovery_postfix_mailq_status(section)) == [
        Service(item="default"),
        Service(item="postfix-external"),
        Service(item="postfix-stopped"),
        Service(item="postfix-internal"),
        Service(item="postfix-other"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "default",
            [
                Result(state=State.OK, summary="Status: the Postfix mail system is running"),
                Result(state=State.OK, summary="PID: 12910"),
            ],
            id="Postfix running",
        ),
        pytest.param(
            "postfix-uat-cdi",
            [Result(state=State.CRIT, summary="Status: the Postfix mail system is not running")],
            id="Postfix not running",
        ),
        pytest.param(
            "postfix-stopped",
            [
                Result(
                    state=State.CRIT, summary="Status: PID file exists but instance is not running!"
                )
            ],
            id="Postfix stopped",
        ),
        pytest.param(
            "postfix-other",
            [Result(state=State.CRIT, summary="Status: PID file exists but is not readable")],
            id="Postfix process file not readable",
        ),
    ],
)
def test_check_postfix_mailq_status(
    section: Mapping[str, PostfixError | PostfixPid], item: str, expected_output: Sequence[object]
) -> None:
    assert list(check_postfix_mailq_status(item, section)) == expected_output
