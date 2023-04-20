#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.plugins.agent_based import hp_proliant_power
from cmk.base.plugins.agent_based.agent_based_api import v1


@pytest.fixture(name="section_present")
def fixure_section_present() -> hp_proliant_power.Section:
    section = hp_proliant_power.parse_hp_proliant_power(string_table=[["2", "268"]])
    assert section is not None
    assert section[0] == "present"
    return section


@pytest.fixture(name="section_absent")
def fixure_section_absent() -> hp_proliant_power.Section:
    section = hp_proliant_power.parse_hp_proliant_power(string_table=[["3", "268"]])
    assert section is not None
    assert section[0] == "absent"
    return section


def test_parse_other() -> None:
    section = hp_proliant_power.parse_hp_proliant_power(string_table=[["1", "268"]])
    assert section is not None
    assert section[0] == "other"


def test_discovery_present(section_present: hp_proliant_power.Section) -> None:
    services = list(hp_proliant_power.discover_hp_proliant_power(section_present))
    assert services == [v1.Service()]


def test_discovery_absent(section_absent: hp_proliant_power.Section) -> None:
    services = list(hp_proliant_power.discover_hp_proliant_power(section_absent))
    assert services == []


def test_check_present(section_present: hp_proliant_power.Section) -> None:
    results = list(
        hp_proliant_power.check_hp_proliant_power({"levels": (100, 200)}, section_present)
    )
    assert results == [
        v1.Result(
            state=v1.State.CRIT,
            summary="Current reading: 268 Watts (warn/crit at 100 Watts/200 Watts)",
        ),
        v1.Metric("watt", 268.0, levels=(100.0, 200.0)),
    ]


def test_check_absent(section_absent: hp_proliant_power.Section) -> None:
    results = list(
        hp_proliant_power.check_hp_proliant_power({"levels": (100, 200)}, section_absent)
    )
    assert results == [v1.Result(state=v1.State.CRIT, summary="Power Meter state: absent")]
