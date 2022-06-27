# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based import synology_status
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State

SECTION_TABLE = [["0", "1"]]


def test_parsing() -> None:
    section = synology_status.parse(SECTION_TABLE)
    assert section == synology_status.Section(system=0, power=1)


def test_discovery() -> None:
    section = synology_status.parse(SECTION_TABLE)
    assert section is not None
    services = list(synology_status.discovery(section))
    assert len(services) == 1


@pytest.mark.parametrize("state, expected", [(1, State.OK), (0, State.CRIT)])
def test_result_state(state, expected) -> None:
    section = synology_status.Section(system=state, power=state)
    assert section is not None
    results = list(synology_status.check(section=section))

    for result in results:
        assert isinstance(result, Result)
        assert result.state == expected
