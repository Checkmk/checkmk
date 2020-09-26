#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from pathlib import Path

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

from cmk.utils.type_defs import OKResult

from cmk.base.checkers._abstract import Mode
from cmk.base.checkers.agent import AgentHostSections, AgentSummarizerDefault
from cmk.base.checkers.tcp import TCPSource


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


@pytest.mark.parametrize("result,reported,rule", [
    (None, "127.0.0.1", None),
    (None, None, "127.0.0.1"),
    ((0, 'Allowed IP ranges: 1.2.3.4', []), "1.2.3.4", "1.2.3.4"),
    ((1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)', []), "1.2.{3,4,5}.6",
     "1.2.3.6"),
    ((1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)', []), "1.2.3.6",
     "1.2.3.{4,5,6}"),
])
def test_tcpdatasource_only_from(mode, monkeypatch, result, reported, rule):
    ts = Scenario().add_host("hostname")
    ts.set_option("agent_config", {"only_from": [rule]} if rule else {})
    config_cache = ts.apply(monkeypatch)

    source = TCPSource("hostname", "ipaddress", mode=mode)
    monkeypatch.setattr(config_cache, "host_extra_conf", lambda host, ruleset: ruleset)

    summarizer = AgentSummarizerDefault(source.exit_spec, source)
    assert summarizer._sub_result_only_from({"onlyfrom": reported}) == result


@pytest.mark.parametrize("restricted_address_mismatch_state, only_from, rule, result", [
    (None, "1.2.{3,4,5}.6", "1.2.3.6",
     (1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)', [])),
    (None, "1.2.3.6", "1.2.3.{4,5,6}",
     (1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)', [])),
    (1, "1.2.{3,4,5}.6", "1.2.3.6",
     (1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)', [])),
    (1, "1.2.3.6", "1.2.3.{4,5,6}",
     (1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)', [])),
    (0, "1.2.{3,4,5}.6", "1.2.3.6",
     (0, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)', [])),
    (0, "1.2.3.6", "1.2.3.{4,5,6}",
     (0, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)', [])),
    (2, "1.2.{3,4,5}.6", "1.2.3.6",
     (2, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!!)', [])),
    (2, "1.2.3.6", "1.2.3.{4,5,6}",
     (2, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!!)', [])),
    (3, "1.2.{3,4,5}.6", "1.2.3.6",
     (3, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(?)', [])),
    (3, "1.2.3.6", "1.2.3.{4,5,6}",
     (3, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(?)', [])),
])
def test_tcpdatasource_restricted_address_mismatch(mode, monkeypatch,
                                                   restricted_address_mismatch_state, only_from,
                                                   rule, result):
    hostname = "hostname"
    ts = Scenario().add_host(hostname)
    ts.set_option("agent_config", {"only_from": [(rule, [], [hostname], {})]})

    if restricted_address_mismatch_state is not None:
        ts.set_ruleset("check_mk_exit_status", [
            ({
                "restricted_address_mismatch": restricted_address_mismatch_state,
            }, [], [hostname], {}),
        ])

    ts.apply(monkeypatch)
    source = TCPSource(hostname, "ipaddress", mode=mode)
    summarizer = AgentSummarizerDefault(source.exit_spec, source)

    assert summarizer._sub_result_only_from({"onlyfrom": only_from}) == result


def test_attribute_defaults(mode, monkeypatch):
    ipaddress = "1.2.3.4"
    hostname = "testhost"
    Scenario().add_host(hostname).apply(monkeypatch)

    source = TCPSource(hostname, ipaddress, mode=mode)
    monkeypatch.setattr(source, "file_cache_path", Path("/my/path/"))
    assert source.fetcher_configuration == {
        "file_cache": {
            "disabled": False,
            "max_age": 0,
            "path": "/my/path",
            "simulation": False,
            "use_outdated": False,
        },
        "family": socket.AF_INET,
        "address": (ipaddress, 6556),
        "timeout": 5.0,
        "encryption_settings": {
            "use_realtime": "enforce",
            "use_regular": "disable",
        },
        "use_only_cache": False,
    }
    assert source.description == "TCP: %s:%s" % (ipaddress, 6556)
    assert source.id == "agent"


class TestSummaryResult:
    @pytest.fixture(params=(mode for mode in Mode if mode is not Mode.NONE))
    def mode(self, request):
        return request.param

    @pytest.mark.parametrize("ipaddress", [None, "127.0.0.1"])
    def test_defaults(self, ipaddress, mode, monkeypatch):
        hostname = "testhost"
        Scenario().add_host(hostname).apply(monkeypatch)
        source = TCPSource(
            hostname,
            ipaddress,
            mode=mode,
        )

        assert source.summarize(OKResult(AgentHostSections())) == (
            0,
            "Version: unknown, OS: unknown",
            [],
        )
