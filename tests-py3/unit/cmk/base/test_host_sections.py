#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib.base import Scenario
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.host_sections import MultiHostSections
from cmk.base.data_sources.abstract import AgentHostSections

node1 = [
    ["node1 data 1"],
    ["node1 data 2"],
]

node2 = [
    ["node2 data 1"],
    ["node2 data 2"],
]


@pytest.mark.parametrize(
    "hostname,nodes,host_entries,cluster_mapping,service_descr,expected_result",
    [
        # No clusters
        ("heute", None, [
            ('heute', node1),
        ], {
            "heute": "heute"
        }, None, node1),
        ("heute", None, [
            ('heute', node1),
        ], {
            "heute": "heute"
        }, "FooBar", node1),
        # Clusters: host_of_clustered_service returns cluster name. That means that
        # the service is assigned to the cluster
        ("cluster", ["node1", "node2"], [
            ('node1', node1),
            ('node2', node2),
        ], {
            "node1": "cluster",
            "node2": "cluster"
        }, None, node1 + node2),
        ("cluster", ["node1", "node2"], [
            ('node1', node1),
            ('node2', node2),
        ], {
            "node1": "cluster",
            "node2": "cluster"
        }, "FooBar", node1 + node2),
        # host_of_clustered_service returns either the cluster or node name.
        # That means that the service is assigned to the cluster resp. not to the cluster
        ("cluster", ["node1", "node2"], [
            ('node1', node1),
            ('node2', node2),
        ], {
            "node1": "node1",
            "node2": "cluster"
        }, None, node1 + node2),
        ("cluster", ["node1", "node2"], [
            ('node1', node1),
            ('node2', node2),
        ], {
            "node1": "node1",
            "node2": "cluster"
        }, "FooBar", node2),
    ])
def test_get_section_content(monkeypatch, hostname, nodes, host_entries, cluster_mapping,
                             service_descr, expected_result):
    ts = Scenario()

    if nodes is None:
        ts.add_host(hostname)
    else:
        ts.add_cluster(hostname, nodes=nodes)

    for node in nodes or []:
        ts.add_host(node)

    config_cache = ts.apply(monkeypatch)

    def host_of_clustered_service(hostname, service_description):
        return cluster_mapping[hostname]

    multi_host_sections = MultiHostSections()
    for nodename, node_section_content in host_entries:
        multi_host_sections.add_or_get_host_sections(
            nodename, "127.0.0.1",
            AgentHostSections(sections={"check_plugin_name": node_section_content}))

    monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: "127.0.0.1")
    monkeypatch.setattr(config_cache, "host_of_clustered_service", host_of_clustered_service)

    section_content = multi_host_sections.get_section_content(hostname,
                                                              "127.0.0.1",
                                                              "check_plugin_name",
                                                              False,
                                                              service_description=service_descr)
    assert expected_result == section_content,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, section_content)
