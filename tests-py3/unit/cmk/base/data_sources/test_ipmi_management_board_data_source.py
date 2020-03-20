#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import namedtuple

import pytest  # type: ignore[import]

from cmk.base.data_sources.ipmi import IPMIManagementBoardDataSource
from testlib.base import Scenario

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


@pytest.mark.parametrize(
    "reading, parsed",
    [
        # standard case
        (SensorReading(['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type",
                       None, 0), [b"0", "Hugo", "hugo-type", b"N/A", "", b"WARNING"]),
        # false positive (no non-critical state): let state come through
        (SensorReading(['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice",
                       3.14159265,
                       1), [b"0", "Dingeling", "FancyDevice", b"3.14", b"C", b"Present"]),
    ])
def test_ipmi_parse_sensor_reading(reading, parsed):
    assert IPMIManagementBoardDataSource._parse_sensor_reading(0, reading) == parsed


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, ipaddress)

    assert source.id() == "mgmt_ipmi"
    assert source.title() == "Management board - IPMI"
    assert source._cpu_tracking_id() == source.id()
    assert source._gather_check_plugin_names() == {"mgmt_ipmi_sensors"}
    assert source._summary_result("anything will do") == (0, "Version: unknown", [])
    assert source._get_ipmi_version() == "unknown"
