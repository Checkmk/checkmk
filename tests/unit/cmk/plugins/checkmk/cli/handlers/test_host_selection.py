#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pytest import MonkeyPatch

from cmk.ccc.hostaddress import HostName
from cmk.plugins.checkmk.cli.handlers.host_selection import monitored_hosts
from cmk.ruleset_matcher.tags import TagGroupID, TagID
from tests.testlib.unit.base_configuration_scenario import Scenario


def _monitored_hosts(ts: Scenario, monkeypatch: MonkeyPatch) -> set[HostName]:
    loading_result = ts.apply(monkeypatch)
    return monitored_hosts(loading_result.hosts_config, loading_result.config_cache)


def test_monitored_hosts_include_clusters(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("node1"))
    ts.add_cluster(HostName("cluster1"), nodes=[HostName("node1")])

    assert _monitored_hosts(ts, monkeypatch) == {HostName("node1"), HostName("cluster1")}


def test_monitored_hosts_exclude_other_sites_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("local"))
    ts.add_host(HostName("foreign"), tags={TagGroupID("site"): TagID("site2")})
    ts.add_cluster(
        HostName("foreign-cluster"),
        tags={TagGroupID("site"): TagID("site2")},
        nodes=[HostName("foreign")],
    )

    assert _monitored_hosts(ts, monkeypatch) == {HostName("local")}


def test_monitored_hosts_exclude_offline_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.set_ruleset(
        "only_hosts",
        [
            {
                "id": "01",
                "condition": {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("offline")}}},
                "value": True,
            },
        ],
    )
    ts.add_host(HostName("online"))
    ts.add_host(HostName("offline"), tags={TagGroupID("criticality"): TagID("offline")})

    assert _monitored_hosts(ts, monkeypatch) == {HostName("online")}
