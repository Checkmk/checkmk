#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

from tests.unit.conftest import FixRegister


def test_check_pdu_gude(
    fix_register: FixRegister,
) -> None:
    assert list(
        fix_register.check_plugins[CheckPluginName("pdu_gude_8310")].check_function(
            item=1,
            params={
                "V": (250, 210),
                "A": (15, 16),
                "W": (3500, 3600),
            },
            section=[
                ["13478", "4010", "0", "228", "0"],
                ["8", "0", "0", "0", "0"],
            ],
        )
    ) == [
        Result(state=State.OK, summary="13.48 kWh"),
        Metric("kWh", 13.478),
        Result(state=State.CRIT, summary="4010.00 W"),
        Metric("W", 4010.0, levels=(3500.0, 3600.0)),
        Result(state=State.OK, summary="0.00 A"),
        Metric("A", 0.0, levels=(15.0, 16.0)),
        Result(state=State.WARN, summary="228.00 V"),
        Metric("V", 228.0, levels=(250.0, 210.0)),
        Result(state=State.OK, summary="0.00 VA"),
        Metric("VA", 0.0),
    ]
