#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName

from cmk.agent_based.v2 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.oracle.agent_based.libinstance import GeneralError, Instance, InvalidData
from cmk.plugins.oracle.agent_based.oracle_instance_section import parse_oracle_instance


def test_discover_oracle_instance_uptime(agent_based_plugins: AgentBasedPlugins) -> None:
    assert list(
        agent_based_plugins.check_plugins[
            CheckPluginName("oracle_instance_uptime")
        ].discovery_function(
            {
                "a": Instance(sid="a", version="", openmode="", logins="", up_seconds=1234),
                "b": Instance(sid="a", version="", openmode="", logins=""),
                "c": GeneralError("b", "whatever"),
                "d": InvalidData("c", "This is an error"),
            },
        )
    ) == [
        Service(item="a"),
    ]


def test_check_oracle_instance_uptime_normal(agent_based_plugins: AgentBasedPlugins) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1643360266, tz=ZoneInfo("UTC"))):
        assert list(
            agent_based_plugins.check_plugins[
                CheckPluginName("oracle_instance_uptime")
            ].check_function(
                item="IC731",
                params={},
                section=parse_oracle_instance(
                    [
                        [
                            "IC731",
                            "12.1.0.2.0",
                            "OPEN",
                            "ALLOWED",
                            "STARTED",
                            "2144847",
                            "3190399742",
                            "ARCHIVELOG",
                            "PRIMARY",
                            "YES",
                            "IC73",
                            "130920150251",
                        ]
                    ]
                ),
            )
        ) == [
            Result(state=State.OK, summary="Up since 2022-01-03 13:10:19"),
            Result(state=State.OK, summary="Uptime: 24 days 19 hours"),
            Metric("uptime", 2144847.0),
        ]


def test_check_oracle_instance_uptime_error(agent_based_plugins: AgentBasedPlugins) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            agent_based_plugins.check_plugins[
                CheckPluginName("oracle_instance_uptime")
            ].check_function(
                item="IC731",
                params={},
                section=parse_oracle_instance(
                    [
                        [
                            "IC731",
                            "FAILURE",
                            "ORA-99999 tnsping failed for IC731 ERROR: ORA-28002: the password "
                            "will expire within 1 days",
                        ]
                    ]
                ),
            )
        )


def test_check_oracle_instance_uptime_pdb_mounted(agent_based_plugins: AgentBasedPlugins) -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1643360266, tz=ZoneInfo("UTC"))):
        assert list(
            agent_based_plugins.check_plugins[
                CheckPluginName("oracle_instance_uptime")
            ].check_function(
                item="CPMOZD.PDB$SEED",
                params={},
                section=parse_oracle_instance(
                    [
                        [
                            "CPMOZD",
                            "19.25.0.0.0",
                            "MOUNTED",
                            "ALLOWED",
                            "STARTED",
                            "1988689",
                            "461957806",
                            "ARCHIVELOG",
                            "PHYSICAL STANDBY",
                            "YES",
                            "CPMOZ",
                            "190520200930",
                            "TRUE",
                            "2",
                            "PDB$SEED",
                            "2225282951",
                            "MOUNTED",
                            "",
                            "2897215488",
                            "ENABLED",
                            "-1",
                            "8192",
                            "gemhb-ol13.grit.local",
                        ]
                    ]
                ),
            )
        ) == [
            Result(state=State.OK, summary="PDB in mounted state has no uptime information"),
        ]
