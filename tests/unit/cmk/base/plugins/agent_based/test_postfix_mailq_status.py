#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.postfix_mailq_status import (
    check_postfix_mailq_status,
    inventory_postfix_mailq_status,
)
from cmk.base.plugins.agent_based.postfix_mailq_status import (
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


def test_inventory_postfix_mailq_status(section: Mapping[str, PostfixError | PostfixPid]) -> None:
    assert list(inventory_postfix_mailq_status(section)) == [
        ("", None),
        ("postfix-external", None),
        ("postfix-stopped", None),
        ("postfix-internal", None),
        ("postfix-uat-cdi", None),
        ("postfix-other", None),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "",  # default postfix
            [(0, "Status: the Postfix mail system is running"), (0, "PID: 12910")],
            id="Postfix running",
        ),
        pytest.param(
            "postfix-uat-cdi",
            [(2, "Status: the Postfix mail system is not running")],
            id="Postfix not running",
        ),
        pytest.param(
            "postfix-stopped",
            [(2, "Status: PID file exists but instance is not running!")],
            id="Postfix stopped",
        ),
        pytest.param(
            "postfix-other",
            [(2, "Status: PID file exists but is not readable")],
            id="Postfix process file not readable",
        ),
    ],
)
def test_check_postfix_mailq_status(
    section: Mapping[str, PostfixError | PostfixPid], item: str, expected_output: Sequence[object]
) -> None:
    assert list(check_postfix_mailq_status(item, None, section)) == expected_output
