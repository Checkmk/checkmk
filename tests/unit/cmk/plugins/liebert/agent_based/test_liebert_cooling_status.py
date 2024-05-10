#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.liebert.agent_based.lib import SectionWithoutUnit
from cmk.plugins.liebert.agent_based.liebert_cooling_status import (
    check_plugin_liebert_cooling_status,
    snmp_section_liebert_cooling_status,
)


def _section() -> SectionWithoutUnit[str]:
    assert (
        section := snmp_section_liebert_cooling_status.parse_function(
            [
                [
                    ["Fancy cooling device", "awesome"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_cooling_status.discovery_function(_section())) == [
        Service(item="Fancy cooling device"),
    ]


def test_check() -> None:
    assert list(
        check_plugin_liebert_cooling_status.check_function("Fancy cooling device", _section())
    ) == [
        Result(state=State.OK, summary="awesome"),
    ]
