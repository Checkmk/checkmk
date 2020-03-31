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


def test_parse_sensor_reading_standard_case():
    reading = SensorReading(  #
        ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
    assert IPMIManagementBoardDataSource._parse_sensor_reading(
        0, reading) == [b"0", "Hugo", "hugo-type", b"N/A", "", b"WARNING"]


def test_parse_sensor_reading_false_positive():
    reading = SensorReading(  #
        ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
    assert IPMIManagementBoardDataSource._parse_sensor_reading(
        0, reading) == [b"0", "Dingeling", "FancyDevice", b"3.14", b"C", b"Present"]


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    # NOTE: pylint is quite buggy when it comes to class hierarchies and abstract methods!
    source = IPMIManagementBoardDataSource(hostname, ipaddress)  # pylint: disable=abstract-class-instantiated

    assert source.id() == "mgmt_ipmi"
    assert source.title() == "Management board - IPMI"
    assert source._cpu_tracking_id() == source.id()
    assert source._gather_check_plugin_names() == {"mgmt_ipmi_sensors"}
    assert source._summary_result("anything will do") == (0, "Version: unknown", [])
    assert source._get_ipmi_version() == "unknown"


def test_describe_with_ipaddress(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    # NOTE: pylint is quite buggy when it comes to class hierarchies and abstract methods!
    source = IPMIManagementBoardDataSource(hostname, None)  # pylint: disable=abstract-class-instantiated
    source._ipaddress = "127.0.0.1"  # The API is lying.

    assert source.describe() == "Management board - IPMI (Address: 127.0.0.1)"


def test_describe_with_credentials(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    # NOTE: pylint is quite buggy when it comes to class hierarchies and abstract methods!
    source = IPMIManagementBoardDataSource(hostname, None)  # pylint: disable=abstract-class-instantiated
    source._credentials = {"username": "Bobby"}

    assert source.describe() == "Management board - IPMI (User: Bobby)"


def test_describe_with_ipaddress_and_credentials(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    # NOTE: pylint is quite buggy when it comes to class hierarchies and abstract methods!
    source = IPMIManagementBoardDataSource(hostname, "127.0.0.1")  # pylint: disable=abstract-class-instantiated
    source._ipaddress = "127.0.0.1"  # The API is lying.
    source._credentials = {"username": "Bobby"}

    assert source.describe() == "Management board - IPMI (Address: 127.0.0.1, User: Bobby)"
