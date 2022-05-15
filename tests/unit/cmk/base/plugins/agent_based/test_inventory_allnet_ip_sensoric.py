#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.base.plugins.agent_based import allnet_ip_sensoric as ais
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

RAW_OUTPUT: Final = """
sensor0.alarm0;0
sensor0.all4000_typ;0
sensor0.function;1
sensor0.limit_high;50.00
sensor0.limit_low;10.00
sensor0.maximum;28.56
sensor0.minimum;27.50
sensor0.name;Temperatur intern
sensor0.value_float;27.50
sensor0.value_int;2750
sensor0.value_string;27.50
sensor1.alarm1;0
sensor1.all4000_typ;0
sensor1.function;3
sensor1.limit_high;50.00
sensor1.limit_low;-0.50
sensor1.maximum;0.00
sensor1.minimum;2048000.00
sensor1.name;ADC 0
sensor1.value_float;0.00
sensor1.value_int;0
sensor1.value_string;0.00
sensor9.alarm9;1
sensor9.all4000_typ;101
sensor9.function;12
sensor9.limit_high;85.00
sensor9.limit_low;10.00
sensor9.maximum;100.00
sensor9.minimum;2048000.02
sensor9.name;USV Spannung
sensor9.value_float;100.00
sensor9.value_int;100
sensor9.value_string;100
system.alarmcount;4
system.date;30.06.2014
system.devicename;all5000
system.devicetype;ALL5000
system.sys;114854
system.time;16:08:48"""


@pytest.fixture(name="section")
def _get_section() -> ais.Section:
    return ais.parse_allnet_ip_sensoric([line.split(";") for line in RAW_OUTPUT[1:].splitlines()])


def test_allnet_ip_sensoric(section: ais.Section) -> None:
    assert list(ais.inventory_allnet_ip_sensoric(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "model": "ALL5000",
            },
        ),
    ]
