#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import synology_fans
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State

SECTION_TABLE = [
    ["1", "0"],
]


def test_parsing() -> None:
    section = synology_fans.parse(SECTION_TABLE)
    assert section == {"System": 1, "CPU": 0}


def test_discovery() -> None:
    section = synology_fans.parse(SECTION_TABLE)
    assert section is not None
    services = list(synology_fans.discovery(section))
    assert {s.item for s in services} == {"System", "CPU"}


@pytest.mark.parametrize(
    "item, expected",
    [("System", State.CRIT), ("CPU", State.OK)],
)
def test_result_state(item: str, expected: State) -> None:
    section = synology_fans.parse(SECTION_TABLE)
    assert section is not None
    result = list(synology_fans.check(item=item, section=section))[0]
    assert isinstance(result, Result)
    assert result.state == expected
