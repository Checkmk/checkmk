#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import synology_fans
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


@pytest.fixture(name="section")
def _section() -> synology_fans.Section:
    section = synology_fans.parse(
        [
            ["2", "1"],
        ]
    )
    assert section
    return section


def test_discovery(section: synology_fans.Section) -> None:
    services = list(synology_fans.discovery(section))
    assert {s.item for s in services} == {"System", "CPU"}


@pytest.mark.parametrize(
    "item, expected",
    [("System", State.CRIT), ("CPU", State.OK)],
)
def test_result_state(section: synology_fans.Section, item: str, expected: State) -> None:
    result = list(synology_fans.check(item=item, section=section))[0]
    assert isinstance(result, Result)
    assert result.state is expected
