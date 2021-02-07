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

from cmk.core_helpers.agent import AgentSummarizerDefault
from cmk.core_helpers.type_defs import Mode

from cmk.base.sources.tcp import TCPSource


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


@pytest.mark.parametrize("res,reported,rule", [
    (None, "127.0.0.1", None),
    (None, None, "127.0.0.1"),
    ((0, 'Allowed IP ranges: 1.2.3.4', []), "1.2.3.4", "1.2.3.4"),
    ((1, 'Unexpected allowed IP ranges (exceeding: 1.2.4.6 1.2.5.6)(!)', []), "1.2.{3,4,5}.6",
     "1.2.3.6"),
    ((1, 'Unexpected allowed IP ranges (missing: 1.2.3.4 1.2.3.5)(!)', []), "1.2.3.6",
     "1.2.3.{4,5,6}"),
])
def test_tcpdatasource_only_from(mode, monkeypatch, res, reported, rule):
    # TODO(ml): Not only is this white box testing but all these instantiations
    #           before the summarizer obscure the purpose of the test.  This is
    #           way too complicated.  Test the `AgentSummarizerDefault` directly
    #           in `tests.unit.cmk.core_helpers.test_summarizers` instead.
    ts = Scenario().add_host("hostname")
    ts.set_option("agent_config", {"only_from": [rule]} if rule else {})
    config_cache = ts.apply(monkeypatch)

    source = TCPSource("hostname", "ipaddress", mode=mode)
    monkeypatch.setattr(config_cache, "host_extra_conf", lambda host, ruleset: ruleset)

    summarizer = AgentSummarizerDefault(
        source.exit_spec,
        is_cluster=source.host_config.is_cluster,
        agent_min_version=0,
        agent_target_version=source.host_config.agent_target_version,
        only_from=source.host_config.only_from,
    )
    assert summarizer._check_only_from(reported) == res


@pytest.mark.parametrize("restricted_address_mismatch_state, only_from, rule, res", [
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
def test_tcpdatasource_restricted_address_mismatch(
    mode,
    monkeypatch,
    restricted_address_mismatch_state,
    only_from,
    rule,
    res,
):
    # TODO(ml): Not only is this white box testing but all these instantiations
    #           before the summarizer obscure the purpose of the test.  This is
    #           way too complicated.  Test the `AgentSummarizerDefault` directly
    #           in `tests.unit.cmk.core_helpers.test_summarizers` instead.
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

    summarizer = AgentSummarizerDefault(
        source.exit_spec,
        is_cluster=source.host_config.is_cluster,
        agent_min_version=0,
        agent_target_version=source.host_config.agent_target_version,
        only_from=source.host_config.only_from,
    )

    assert summarizer._check_only_from(only_from) == res


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
