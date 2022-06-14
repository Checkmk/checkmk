#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.base import Scenario

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.type_defs import HostName, result, SourceType

from cmk.core_helpers.host_sections import HostSections

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.sources.agent import AgentRawDataSection
from cmk.base.sources.ipmi import IPMISource


def test_attribute_defaults(monkeypatch) -> None:
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)

    host_config = config.get_config_cache().get_host_config(hostname)
    ipaddress = config.lookup_mgmt_board_ip_address(host_config)

    source = IPMISource(hostname, ipaddress)
    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.description == "Management board - IPMI"
    assert source.source_type is SourceType.MANAGEMENT
    assert source.summarize(result.OK(HostSections[AgentRawDataSection]())) == [
        ActiveCheckResult(0, "Success")
    ]
    assert source.id == "mgmt_ipmi"


def test_ipmi_ipaddress_from_mgmt_board(monkeypatch) -> None:
    hostname = HostName("testhost")
    ipaddress = "127.0.0.1"

    def fake_lookup_ip_address(host_config, *, family, for_mgmt_board=True):
        return ipaddress

    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)
    monkeypatch.setattr(ip_lookup, "lookup_ip_address", fake_lookup_ip_address)
    monkeypatch.setattr(
        config,
        "host_attributes",
        {
            hostname: {"management_address": ipaddress},
        },
    )

    source = IPMISource(hostname, ipaddress)
    assert source.host_config.management_address == ipaddress


def test_description_with_ipaddress(monkeypatch) -> None:
    assert (
        IPMISource._make_description(
            "1.2.3.4",
            {},
        )
        == "Management board - IPMI (Address: 1.2.3.4)"
    )


def test_description_with_credentials(monkeypatch) -> None:
    assert (
        IPMISource._make_description(None, {"username": "Bobby"})
        == "Management board - IPMI (User: Bobby)"
    )


def test_description_with_ipaddress_and_credentials(monkeypatch) -> None:
    assert (
        IPMISource._make_description(
            "1.2.3.4",
            {"username": "Bobby"},
        )
        == "Management board - IPMI (Address: 1.2.3.4, User: Bobby)"
    )
