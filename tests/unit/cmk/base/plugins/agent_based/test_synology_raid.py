# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based import synology_raid
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State

SECTION_TABLE = [[f"Volume {i}", f"{i}"] for i in range(1, 22)]


def test_parsing():
    section = synology_raid.parse(SECTION_TABLE)
    assert len(section) == len(SECTION_TABLE)


def test_discovery():
    section = synology_raid.parse(SECTION_TABLE)
    services = list(synology_raid.discovery(section))
    assert {s.item for s in services} == {i for i, _ in SECTION_TABLE}


@pytest.mark.parametrize(
    "state, expected",
    [
        (1, State.OK),
        (2, State.WARN),
        (3, State.WARN),
        (4, State.WARN),
        (5, State.WARN),
        (6, State.WARN),
        (7, State.OK),
        (8, State.OK),
        (9, State.WARN),
        (10, State.WARN),
        (11, State.CRIT),
        (12, State.CRIT),
        (13, State.OK),
        (14, State.OK),
        (15, State.OK),
        (16, State.OK),
        (17, State.OK),
        (18, State.WARN),
        (19, State.OK),
        (20, State.OK),
        (21, State.UNKNOWN),
    ],
)
def test_result_state(state, expected):
    section = {"Volume 1": synology_raid.Raid("Volume 1", state)}
    result = list(synology_raid.check(item="Volume 1", section=section))[0]
    assert isinstance(result, Result)
    assert result.state == expected
