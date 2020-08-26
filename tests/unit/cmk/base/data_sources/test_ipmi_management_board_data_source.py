#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import SourceType

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources import Mode
from cmk.base.data_sources.agent import AgentHostSections
from cmk.base.data_sources.ipmi import (
    IPMIConfigurator,
    IPMISummarizer,
)


@pytest.fixture(name="mode", params=(mode for mode in Mode if mode is not Mode.NONE))
def mode_fixture(request):
    return request.param


def test_attribute_defaults(mode, monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    host_config = config.get_config_cache().get_host_config(hostname)
    ipaddress = ip_lookup.lookup_mgmt_board_ip_address(host_config)

    configurator = IPMIConfigurator(hostname, ipaddress, mode=mode)
    assert configurator.hostname == hostname
    assert configurator.ipaddress == ipaddress
    assert configurator.mode is mode
    assert configurator.description == "Management board - IPMI"
    assert configurator.source_type is SourceType.MANAGEMENT

    summarizer = configurator.make_summarizer()
    assert summarizer.summarize(AgentHostSections()) == (0, "Version: unknown", [])

    checker = configurator.make_checker()
    assert checker.id == "mgmt_ipmi"
    assert checker._cpu_tracking_id == checker.id


def test_summarizer():
    assert IPMISummarizer._get_ipmi_version(None) == "unknown"


def test_ipmi_ipaddress_from_mgmt_board(mode, monkeypatch):
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

    configurator = IPMIConfigurator(hostname, ipaddress, mode=mode)
    assert configurator.host_config.management_address == ipaddress


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
