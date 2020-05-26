#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections

import pytest  # type: ignore[import]
from testlib.base import Scenario

import cmk.base.config as config
from cmk.base.api import PluginName
import cmk.base.ip_lookup as ip_lookup
from cmk.base.data_sources.host_sections import MultiHostSections
from cmk.base.data_sources.abstract import AgentHostSections

_TestSection = collections.namedtuple(
    "TestSection",
    "name, parsed_section_name, parse_function, supercedes",
)

SECTION_ONE = _TestSection(
    PluginName("one"),
    PluginName("parsed"),
    lambda x: {
        "parsed_by": "one",
        "node": x[0][0]
    },
    [],
)

SECTION_TWO = _TestSection(
    PluginName("two"),
    PluginName("parsed"),
    lambda x: {
        "parsed_by": "two",
        "node": x[0][0]
    },
    [PluginName("one")],
)

SECTION_THREE = _TestSection(
    PluginName("three"),
    PluginName("parsed2"),
    lambda x: {
        "parsed_by": "three",
        "node": x[0][0]
    },
    [],
)

MOCK_SECTIONS = {
    SECTION_ONE.name: SECTION_ONE,
    SECTION_TWO.name: SECTION_TWO,
    SECTION_THREE.name: SECTION_THREE,
}

NODE_1 = [
    ["node1", "data 1"],
    ["node1", "data 2"],
]

NODE_2 = [
    ["node2", "data 1"],
    ["node2", "data 2"],
]


def _set_up(monkeypatch, hostname, nodes, cluster_mapping):
    test_scen = Scenario()

    if nodes is None:
        test_scen.add_host(hostname)
    else:
        test_scen.add_cluster(hostname, nodes=nodes)

    for node in nodes or []:
        test_scen.add_host(node)

    config_cache = test_scen.apply(monkeypatch)

    def host_of_clustered_service(hostname, _service_description):
        return cluster_mapping[hostname]

    monkeypatch.setattr(ip_lookup, "lookup_ip_address", lambda h: "127.0.0.1")
    monkeypatch.setattr(config_cache, "host_of_clustered_service", host_of_clustered_service)
    monkeypatch.setattr(config, "get_registered_section_plugin", MOCK_SECTIONS.get)


@pytest.mark.parametrize(
    "node_section_content,expected_result",
    [
        ({}, None),
        ({
            "one": NODE_1
        }, {
            "parsed_by": "one",
            "node": "node1"
        }),
        ({
            "two": NODE_1
        }, {
            "parsed_by": "two",
            "node": "node1"
        }),
        # TODO (mo): CMK-4232 # ({"one": NODE_1, "two": NODE_1}, {"parsed_by": "two", "node": "node1"}),
    ])
def test_get_parsed_section(monkeypatch, node_section_content, expected_result):

    _set_up(monkeypatch, "node1", None, {})

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault_host_sections(
        ("node1", "127.0.0.1"),
        AgentHostSections(sections=node_section_content),
    )

    content = multi_host_sections.get_parsed_section(("node1", "127.0.0.1"), PluginName("parsed"))

    assert expected_result == content,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, content)


@pytest.mark.parametrize("required_sections,expected_result", [
    (["nonexistent"], {}),
    (["parsed"], {
        "section": {
            "parsed_by": "one",
            "node": "node1"
        }
    }),
    (["parsed", "nonexistent"], {
        "section_parsed": {
            "parsed_by": "one",
            "node": "node1"
        },
        "section_nonexistent": None
    }),
    (["parsed", "parsed2"], {
        "section_parsed": {
            "parsed_by": "one",
            "node": "node1"
        },
        "section_parsed2": {
            "parsed_by": "three",
            "node": "node1"
        }
    }),
])
def test_get_section_kwargs(monkeypatch, required_sections, expected_result):

    _set_up(monkeypatch, "node1", None, {})

    node_section_content = {
        "one": NODE_1,
        # TODO (mo): CMK-4232 # "two": NODE_1,
        "three": NODE_1
    }

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault_host_sections(
        ("node1", "127.0.0.1"),
        AgentHostSections(sections=node_section_content),
    )

    kwargs = multi_host_sections.get_section_kwargs(("node1", "127.0.0.1"),
                                                    [PluginName(n) for n in required_sections])

    assert expected_result == kwargs,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, kwargs)


@pytest.mark.parametrize("required_sections,expected_result", [
    (["nonexistent"], {}),
    (["parsed"], {
        "section": {
            "node1": {
                "parsed_by": "one",
                "node": "node1"
            },
            "node2": {
                "parsed_by": "two",
                "node": "node2"
            },
        }
    }),
    (["parsed", "nonexistent"], {
        "section_parsed": {
            "node1": {
                "parsed_by": "one",
                "node": "node1"
            },
            "node2": {
                "parsed_by": "two",
                "node": "node2"
            },
        },
        "section_nonexistent": {
            "node1": None,
            "node2": None
        }
    }),
    (["parsed", "parsed2"], {
        "section_parsed": {
            "node1": {
                "parsed_by": "one",
                "node": "node1"
            },
            "node2": {
                "parsed_by": "two",
                "node": "node2"
            },
        },
        "section_parsed2": {
            "node1": {
                "parsed_by": "three",
                "node": "node1"
            },
            "node2": {
                "parsed_by": "three",
                "node": "node2"
            },
        }
    }),
])
def test_get_section_cluster_kwargs(monkeypatch, required_sections, expected_result):

    _set_up(monkeypatch, "cluster", ["node2", "node1"], {"node1": "cluster", "node2": "cluster"})

    node1_section_content = {
        "one": NODE_1,
        # TODO (mo): CMK-4232 # "two": NODE_1,
        "three": NODE_1
    }

    node2_section_content = {"two": NODE_2, "three": NODE_2}

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault_host_sections(
        ("node1", "127.0.0.1"),
        AgentHostSections(sections=node1_section_content),
    )
    multi_host_sections.setdefault_host_sections(
        ("node2", "127.0.0.1"),
        AgentHostSections(sections=node2_section_content),
    )

    kwargs = multi_host_sections.get_section_cluster_kwargs(
        "cluster", [PluginName(n) for n in required_sections], "_service_description")

    assert expected_result == kwargs,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, kwargs)


@pytest.mark.parametrize(
    "hostname,nodes,host_entries,cluster_mapping,service_descr,expected_result",
    [
        # No clusters
        ("heute", None, [
            ('heute', NODE_1),
        ], {
            "heute": "heute"
        }, None, NODE_1),
        ("heute", None, [
            ('heute', NODE_1),
        ], {
            "heute": "heute"
        }, "FooBar", NODE_1),
        # Clusters: host_of_clustered_service returns cluster name. That means that
        # the service is assigned to the cluster
        ("cluster", ["node1", "node2"], [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], {
            "node1": "cluster",
            "node2": "cluster"
        }, None, NODE_1 + NODE_2),
        ("cluster", ["node1", "node2"], [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], {
            "node1": "cluster",
            "node2": "cluster"
        }, "FooBar", NODE_1 + NODE_2),
        # host_of_clustered_service returns either the cluster or node name.
        # That means that the service is assigned to the cluster resp. not to the cluster
        ("cluster", ["node1", "node2"], [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], {
            "node1": "node1",
            "node2": "cluster"
        }, None, NODE_1 + NODE_2),
        ("cluster", ["node1", "node2"], [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], {
            "node1": "node1",
            "node2": "cluster"
        }, "FooBar", NODE_2),
    ])
def test_get_section_content(monkeypatch, hostname, nodes, host_entries, cluster_mapping,
                             service_descr, expected_result):

    _set_up(monkeypatch, hostname, nodes, cluster_mapping)

    multi_host_sections = MultiHostSections()
    for nodename, node_section_content in host_entries:
        multi_host_sections.setdefault_host_sections(
            (nodename, "127.0.0.1"),
            AgentHostSections(sections={"check_plugin_name": node_section_content}),
        )

    section_content = multi_host_sections.get_section_content(hostname,
                                                              "127.0.0.1",
                                                              "check_plugin_name",
                                                              False,
                                                              service_description=service_descr)
    assert expected_result == section_content,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, section_content)
