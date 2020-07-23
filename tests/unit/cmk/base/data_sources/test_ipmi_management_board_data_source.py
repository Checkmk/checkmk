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
from cmk.base.data_sources.ipmi import IPMIConfigurator, IPMIManagementBoardDataSource


def test_attribute_defaults(monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    host_config = config.get_config_cache().get_host_config(hostname)
    ipaddress = ip_lookup.lookup_mgmt_board_ip_address(host_config)

    configurator = IPMIConfigurator(hostname, ipaddress)
    assert configurator.description == "Management board - IPMI"
    assert configurator.source_type is SourceType.MANAGEMENT

    source = IPMIManagementBoardDataSource(configurator=configurator)
    assert source.hostname == hostname
    # Address comes from management board.
    assert source.ipaddress is None
    assert source.id == "mgmt_ipmi"
    assert source._cpu_tracking_id == source.id
    assert source._summary_result(True) == (0, "Version: unknown", [])
    assert source._get_ipmi_version(None) == "unknown"


def test_ipmi_ipaddress_from_mgmt_board(monkeypatch):
    hostname = "testhost"
    ipaddress = "127.0.0.1"

    def fake_lookup_ip_address(host_config, family=None, for_mgmt_board=True):
        return ipaddress

    Scenario().add_host(hostname).apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(config, "host_attributes", {
        hostname: {
            "management_address": ipaddress
        },
    })

    configurator = IPMIConfigurator(hostname, ipaddress)
    assert configurator.host_config.management_address == ipaddress

    source = IPMIManagementBoardDataSource(configurator=configurator)
    assert source.ipaddress == ipaddress


def test_description_with_ipaddress(monkeypatch):
    assert IPMIConfigurator._make_description(
        "1.2.3.4",
        {},
    ) == "Management board - IPMI (Address: 1.2.3.4)"


def test_description_with_credentials(monkeypatch):
    assert IPMIConfigurator._make_description(
        None, {"username": "Bobby"}) == "Management board - IPMI (User: Bobby)"


def test_description_with_ipaddress_and_credentials(monkeypatch):
    assert IPMIConfigurator._make_description(
        "1.2.3.4",
        {"username": "Bobby"},
    ) == "Management board - IPMI (Address: 1.2.3.4, User: Bobby)"
