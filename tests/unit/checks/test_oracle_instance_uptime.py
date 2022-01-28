#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import on_time

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.item_state import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.oracle_instance import (
    GeneralError,
    Instance,
    InvalidData,
    parse_oracle_instance,
)


def test_discover_oracle_instance_uptime(fix_register: FixRegister) -> None:
    assert list(
        fix_register.check_plugins[CheckPluginName("oracle_instance_uptime")].discovery_function(
            {
                "a": Instance(sid="a"),
                "b": GeneralError(
                    sid="b",
                    err="whatever",
                ),
                "c": InvalidData(sid="c"),
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
            Result(
                state=State.OK,
                summary="Up since 2022-01-03 13:10:19, uptime: 24 days, 19:47:27",
            ),
            Metric(
                "uptime",
                2144847.0,
            ),
        ]


def test_check_oracle_instance_uptime_error(fix_register: FixRegister) -> None:
    with pytest.raises(MKCounterWrapped):
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
