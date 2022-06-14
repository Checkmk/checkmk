#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State


def test_check_netapp_api_temp_missing_value(fix_register) -> None:
    result = list(
        fix_register.check_plugins[CheckPluginName("netapp_api_temp")].check_function(
            item="Ambient Shelf 70",
            params={},
            section={
                "70.1": {
                    "temp-sensor-list": "70",
                    "temp-sensor-current-condition": "normal_temperature_range",
                    # 'temp-sensor-current-temperature': '28',  # missing for this test
                    "temp-sensor-element-no": "1",
                    "temp-sensor-hi-critical": "42",
                    "temp-sensor-hi-warning": "40",
                    "temp-sensor-is-ambient": "true",
                    "temp-sensor-is-error": "false",
                    "temp-sensor-low-critical": "0",
                    "temp-sensor-low-warning": "5",
                }
            },
        )
    )
    assert result == [
        Result(state=State.OK, summary="No temperature sensors assigned to this filer")
    ]
