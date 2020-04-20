#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections import namedtuple

import pytest  # type: ignore[import]
from pyghmi.exceptions import IpmiException  # type: ignore[import]

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.ipmi import (IPMIDataFetcher, IPMIManagementBoardDataSource,
                                        MKAgentError, _parse_sensor_reading)
from testlib.base import Scenario

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


def test_parse_sensor_reading_standard_case():
    reading = SensorReading(  #
        ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
    assert _parse_sensor_reading(  #
        0, reading) == [b"0", b"Hugo", b"hugo-type", b"N/A", b"", b"WARNING"]


def test_parse_sensor_reading_false_positive():
    reading = SensorReading(  #
        ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
    assert _parse_sensor_reading(  #
        0, reading) == [b"0", b"Dingeling", b"FancyDevice", b"3.14", b"C", b"Present"]


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_attribute_defaults(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, ipaddress)

    assert source._for_mgmt_board is True
    assert source._hostname == hostname
    # Address comes from management board.
    assert source._ipaddress is None
    assert source.id() == "mgmt_ipmi"
    assert source.title() == "Management board - IPMI"
    assert source._cpu_tracking_id() == source.id()
    assert source._gather_check_plugin_names() == {"mgmt_ipmi_sensors"}
    assert source._summary_result(True) == (0, "Version: unknown", [])
    assert source._get_ipmi_version() == "unknown"


def test_ipmi_ipaddress_from_mgmt_board(monkeypatch):
    hostname = "testhost"
    ipaddress = "127.0.0.1"
    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: ipaddress)
    monkeypatch.setattr(config, "host_attributes", {
        hostname: {
            "management_address": ipaddress
        },
    })
    source = IPMIManagementBoardDataSource(hostname, None)

    assert source._host_config.management_address == ipaddress
    assert source._ipaddress == ipaddress


def test_describe_with_ipaddress(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, None)
    source._ipaddress = "127.0.0.1"  # The API is lying.

    assert source.describe() == "Management board - IPMI (Address: 127.0.0.1)"


def test_describe_with_credentials(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, None)
    source._credentials = {"username": "Bobby"}

    assert source.describe() == "Management board - IPMI (User: Bobby)"


def test_describe_with_ipaddress_and_credentials(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, "127.0.0.1")
    source._ipaddress = "127.0.0.1"  # The API is lying.
    source._credentials = {"username": "Bobby"}

    assert source.describe() == "Management board - IPMI (Address: 127.0.0.1, User: Bobby)"


class TestIPMIDataFetcher:
    def test_command_raises_IpmiException_handling(self, monkeypatch):
        monkeypatch.setattr(IPMIDataFetcher, "open", lambda self: None)

        with pytest.raises(MKAgentError):
            with IPMIDataFetcher("127.0.0.1", "", "", logging.getLogger("tests")):
                raise IpmiException()
