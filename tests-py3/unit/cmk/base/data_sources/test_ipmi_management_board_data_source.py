#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import SourceType

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.abstract import management_board_ipaddress
from cmk.base.data_sources.ipmi import IPMIManagementBoardDataSource
from testlib.base import Scenario


def test_attribute_defaults(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(
        hostname,
        management_board_ipaddress(hostname),
    )

    assert source.source_type is SourceType.MANAGEMENT
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
    source = IPMIManagementBoardDataSource(
        hostname,
        management_board_ipaddress(hostname),
    )

    assert source._host_config.management_address == ipaddress
    assert source._ipaddress == ipaddress


def test_describe_with_ipaddress(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(hostname, "127.0.0.1")

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
    source._credentials = {"username": "Bobby"}

    assert source.describe() == "Management board - IPMI (Address: 127.0.0.1, User: Bobby)"
