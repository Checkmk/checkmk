#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.checkpoint.agent_based import checkpoint_connections

# .1.3.6.1.4.1.2620.1.1.25.3 -- fwNumConn
STRING_TABLE: StringTable = [["19190"]]

PARAMS = {"levels": (40000, 50000)}


def test_parse_reads_the_current_connection_count() -> None:
    assert checkpoint_connections.parse_checkpoint_connections(STRING_TABLE) == (
        checkpoint_connections.Section(current=19190)
    )


def test_parse_of_an_empty_section() -> None:
    assert checkpoint_connections.parse_checkpoint_connections([]) is None


def test_discover_always_yields_one_service() -> None:
    section = checkpoint_connections.parse_checkpoint_connections(STRING_TABLE)
    assert section is not None
    assert list(checkpoint_connections.discover_checkpoint_connections(section)) == [Service()]


@pytest.mark.parametrize(
    "connections,expected_result",
    [
        pytest.param(
            "19190",
            Result(state=State.OK, summary="Current connections: 19190"),
            id="below_the_levels",
        ),
        pytest.param(
            "40000",
            Result(
                state=State.WARN,
                summary="Current connections: 40000 (warn/crit at 40000/50000)",
            ),
            id="at_the_warn_level",
        ),
        pytest.param(
            "50000",
            Result(
                state=State.CRIT,
                summary="Current connections: 50000 (warn/crit at 40000/50000)",
            ),
            id="at_the_crit_level",
        ),
    ],
)
def test_check_applies_the_upper_levels(connections: str, expected_result: Result) -> None:
    section = checkpoint_connections.parse_checkpoint_connections([[connections]])
    assert section is not None

    assert list(checkpoint_connections.check_checkpoint_connections(PARAMS, section)) == [
        expected_result,
        Metric("connections", float(connections), levels=(40000.0, 50000.0)),
    ]
