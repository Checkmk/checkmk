#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import OKResult, SourceType

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.checkers import Mode
from cmk.base.checkers.agent import AgentHostSections
from cmk.base.checkers.ipmi import IPMISource, IPMISummarizer


@pytest.fixture(name="mode", params=(mode for mode in Mode if mode is not Mode.NONE))
def mode_fixture(request):
    return request.param


def test_attribute_defaults(mode, monkeypatch):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    host_config = config.get_config_cache().get_host_config(hostname)
    ipaddress = ip_lookup.lookup_mgmt_board_ip_address(host_config)

    source = IPMISource(hostname, ipaddress, mode=mode)
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.mode is mode
    assert source.description == "Management board - IPMI"
    assert source.source_type is SourceType.MANAGEMENT
    assert source.summarize(OKResult(AgentHostSections())) == (0, "Version: unknown", [])
    assert source.id == "mgmt_ipmi"
    assert source.cpu_tracking_id == "mgmt_ipmi"


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

    source = IPMISource(hostname, ipaddress, mode=mode)
    assert source.host_config.management_address == ipaddress


def test_description_with_ipaddress(monkeypatch):
    assert IPMISource._make_description(
        "1.2.3.4",
        {},
    ) == "Management board - IPMI (Address: 1.2.3.4)"


def test_description_with_credentials(monkeypatch):
    assert IPMISource._make_description(
        None, {"username": "Bobby"}) == "Management board - IPMI (User: Bobby)"


def test_description_with_ipaddress_and_credentials(monkeypatch):
    assert IPMISource._make_description(
        "1.2.3.4",
        {"username": "Bobby"},
    ) == "Management board - IPMI (Address: 1.2.3.4, User: Bobby)"
