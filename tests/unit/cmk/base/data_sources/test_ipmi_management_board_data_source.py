#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# No stub
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import SourceType

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.ipmi import IPMIManagementBoardDataSource


def test_attribute_defaults(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = IPMIManagementBoardDataSource(
        hostname,
        ip_lookup.lookup_mgmt_board_ip_address(hostname),
    )

    assert source.source_type is SourceType.MANAGEMENT
    assert source.hostname == hostname
    # Address comes from management board.
    assert source.ipaddress is None
    assert source.id() == "mgmt_ipmi"
    assert source.title() == "Management board - IPMI"
    assert source._cpu_tracking_id() == source.id()
    assert source._summary_result(True) == (0, "Version: unknown", [])
    assert source._get_ipmi_version() == "unknown"


def test_ipmi_ipaddress_from_mgmt_board(monkeypatch):
    hostname = "testhost"
    ipaddress = "127.0.0.1"

    def fake_lookup_ip_address(hostname, family=None, for_mgmt_board=True):
        return ipaddress

    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(config, "host_attributes", {
        hostname: {
            "management_address": ipaddress
        },
    })
    source = IPMIManagementBoardDataSource(
        hostname,
        ip_lookup.lookup_mgmt_board_ip_address(hostname),
    )

    assert source._host_config.management_address == ipaddress
    assert source.ipaddress == ipaddress


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
