#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.zorp.agent_based.zorp_connections import (
    agent_section_zorp_connections,
    check_plugin_zorp_connections,
    Section,
)


def _section() -> Section:
    assert (
        section := agent_section_zorp_connections.parse_function(
            [
                ["Instance", "scb_ssh:", "walking"],
                ["zorp.stats.active_connections:", "0"],
                ["Instance", "scb_rdp:", "walking"],
                ["zorp.stats.active_connections:", "15"],
                ["Instance", "scb_telnet:", "walking"],
                ["zorp.stats.active_connections:", "None"],
                ["Instance", "scb_vnc:", "walking"],
                ["zorp.stats.active_connections:", "None"],
                ["Instance", "scb_ica:", "walking"],
                ["zorp.stats.active_connections:", "None"],
                ["Instance", "scb_http:", "walking"],
                ["zorp.stats.active_connections:", "None"],
            ]
        )
    ) is not None
    return section


def test_discover_zorp_connections() -> None:
    assert list(check_plugin_zorp_connections.discovery_function(_section())) == [Service()]


def test_check_zorp_connections() -> None:
    assert list(
        check_plugin_zorp_connections.check_function(
            check_plugin_zorp_connections.check_default_parameters, _section()
        )
    ) == [
        Result(state=State.OK, summary="scb_ssh: 0"),
        Result(state=State.OK, summary="scb_rdp: 15"),
        Result(state=State.OK, summary="scb_telnet: 0"),
        Result(state=State.OK, summary="scb_vnc: 0"),
        Result(state=State.OK, summary="scb_ica: 0"),
        Result(state=State.OK, summary="scb_http: 0"),
        Result(state=State.WARN, summary="Total connections: 15 (warn/crit at 15/20)"),
        Metric("connections", 15, levels=(15.0, 20.0)),
    ]
