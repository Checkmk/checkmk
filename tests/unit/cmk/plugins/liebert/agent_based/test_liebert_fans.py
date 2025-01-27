#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_fans import (
    check_plugin_liebert_fans,
    snmp_section_liebert_fans,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_fans.parse_function([[["Fan Speed", "1.3", "%"]]])
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_fans.discovery_function(_section())) == [
        Service(item="Fan Speed"),
    ]


def test_check() -> None:
    assert list(
        check_plugin_liebert_fans.check_function(
            "Fan Speed", {"levels": (80, 90), "levels_lower": (2, 1)}, _section()
        )
    ) == [
        Result(
            state=State.WARN,
            summary="1.30 % (warn/crit below 2.00 %/1.00 %)",
        ),
        Metric("fan_perc", 1.3, levels=(80, 90)),
    ]
