#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_fans_condenser import (
    check_plugin_liebert_fans_condenser,
    snmp_section_liebert_fans_condenser,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_fans_condenser.parse_function(
            [[["How funny is this", "4.2", "out of 10 clowns"]]]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_fans_condenser.discovery_function(_section())) == [
        Service(item="How funny is this"),
    ]


def test_check() -> None:
    assert list(
        check_plugin_liebert_fans_condenser.check_function(
            "How funny is this", {"levels_lower": (8, 9), "levels": (80, 90)}, _section()
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="4.20 out of 10 clowns (warn/crit below 8.00 out of 10 clowns/9.00 out of 10 clowns)",
        ),
        Metric("fan_perc", 4.2, levels=(80, 90)),
    ]
