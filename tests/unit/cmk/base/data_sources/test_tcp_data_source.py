#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket

import pytest  # type: ignore[import]

from testlib.base import Scenario

from cmk.utils.type_defs import ServiceCheckResult

from cmk.base.data_sources.agent import AgentHostSections, Summarizer
from cmk.base.data_sources.tcp import TCPConfigurator, TCPDataSource


@pytest.mark.parametrize("result,reported,rule", [
    (None, "127.0.0.1", None),
    (None, None, "127.0.0.1"),
    ((0, 'Allowed IP ranges: 1.2.3.4', []), "1.2.3.4", "1.2.3.4"),
    ((1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)', []), "1.2.{3,4,5}.6",
     "1.2.3.6"),
    ((1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)', []), "1.2.3.6",
     "1.2.3.{4,5,6}"),
])
def test_tcpdatasource_only_from(monkeypatch, result, reported, rule):
    ts = Scenario().add_host("hostname")
    ts.set_option("agent_config", {"only_from": [rule]} if rule else {})
    config_cache = ts.apply(monkeypatch)

    configurator = TCPConfigurator("hostname", "ipaddress")
    monkeypatch.setattr(config_cache, "host_extra_conf", lambda host, ruleset: ruleset)

    summarizer = Summarizer(configurator.host_config)
    assert summarizer._sub_result_only_from({"onlyfrom": reported}) == result


def test_attribute_defaults(monkeypatch):
    ipaddress = "1.2.3.4"
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    configurator = TCPConfigurator(hostname, ipaddress)
    assert configurator.configure_fetcher() == {
        "family": socket.AF_INET,
        "address": (ipaddress, 6556),
        "timeout": 5.0,
        "encryption_settings": {
            "use_realtime": "enforce",
            "use_regular": "disable",
        },
    }
    assert configurator.description == "TCP: %s:%s" % (ipaddress, 6556)

    source = TCPDataSource(configurator=configurator)

    assert source.hostname == hostname
    assert source.ipaddress == ipaddress
    assert source.id == "agent"
    # From the base class
    assert source.is_agent_cache_disabled() is False
    assert source.get_may_use_cache_file() is False
    assert source.exception() is None


@pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
def test_get_summary_result_requires_host_sections(monkeypatch, ipaddress):
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)
    source = TCPDataSource(configurator=TCPConfigurator(hostname, ipaddress))

    with pytest.raises(TypeError):
        source.get_summary_result_for_discovery()
    with pytest.raises(TypeError):
        source.get_summary_result_for_inventory()
    with pytest.raises(TypeError):
        source.get_summary_result_for_checking()

    source._host_sections = AgentHostSections()

    defaults: ServiceCheckResult = (0, "Version: unknown, OS: unknown", [])
    assert source.get_summary_result_for_discovery() == defaults
    assert source.get_summary_result_for_inventory() == defaults
    assert source.get_summary_result_for_checking() == defaults
