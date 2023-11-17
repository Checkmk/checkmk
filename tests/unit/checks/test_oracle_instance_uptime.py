#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from tests.unit.conftest import FixRegister

from cmk.checkengine.checking import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.oracle_instance_section import parse_oracle_instance

from cmk.plugins.lib.oracle_instance import GeneralError, Instance, InvalidData


def test_discover_oracle_instance_uptime(fix_register: FixRegister) -> None:
    assert list(
        fix_register.check_plugins[CheckPluginName("oracle_instance_uptime")].discovery_function(
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


def test_check_oracle_instance_uptime_normal(fix_register: FixRegister) -> None:
    with on_time(1643360266, "UTC"):
        assert list(
            fix_register.check_plugins[CheckPluginName("oracle_instance_uptime")].check_function(
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
            Result(state=State.OK, summary="Up since Jan 03 2022 13:10:19"),
            Result(state=State.OK, summary="Uptime: 24 days 19 hours"),
            Metric(
                "uptime",
                2144847.0,
            ),
        ]


def test_check_oracle_instance_uptime_error(fix_register: FixRegister) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            fix_register.check_plugins[CheckPluginName("oracle_instance_uptime")].check_function(
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
