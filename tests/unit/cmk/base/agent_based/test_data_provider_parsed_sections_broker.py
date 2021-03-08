#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import collections

import pytest  # type: ignore[import]

# No stub file
from testlib.base import Scenario  # type: ignore[import]

import cmk.utils.piggyback
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import AgentRawData, HostKey, ParsedSectionName, result, SectionName, SourceType

from cmk.core_helpers import (
    FetcherType,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    TCPFetcher,
)
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
from cmk.base.check_utils import HOST_PRECEDENCE, HOST_ONLY, MGMT_ONLY
from cmk.base.agent_based.checking._legacy_mode import _MultiHostSections
from cmk.core_helpers.host_sections import HostSections
from cmk.base.sources import make_nodes, make_sources, Source
from cmk.base.sources.agent import AgentHostSections
from cmk.base.agent_based.data_provider import ParsedSectionsBroker

from cmk.base.sources.piggyback import PiggybackSource
from cmk.base.sources.programs import ProgramSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource

_TestSection = collections.namedtuple(
    "_TestSection",
    "name, parsed_section_name, parse_function, supersedes",
)

SECTION_ONE = _TestSection(
    SectionName("one"),
    ParsedSectionName("parsed"),
    lambda x: {
        "parsed_by": "one",
        "node": x[0][0]
    },
    set(),
)

SECTION_TWO = _TestSection(
    SectionName("two"),
    ParsedSectionName("parsed"),
    lambda x: {
        "parsed_by": "two",
        "node": x[0][0]
    },
    {SectionName("one")},
)

SECTION_THREE = _TestSection(
    SectionName("three"),
    ParsedSectionName("parsed2"),
    lambda x: {
        "parsed_by": "three",
        "node": x[0][0]
    },
    set(),
)

SECTION_FOUR = _TestSection(
    SectionName("four"),
    ParsedSectionName("parsed_four"),
    lambda x: {
        "parsed_by": "four",
        "node": x[0][0]
    },
    {SectionName("one")},
)

MOCK_SECTIONS = {
    SECTION_ONE.name: SECTION_ONE,
    SECTION_TWO.name: SECTION_TWO,
    SECTION_THREE.name: SECTION_THREE,
    SECTION_FOUR.name: SECTION_FOUR,
}

NODE_1 = [
    ["node1", "data 1"],
    ["node1", "data 2"],
]

NODE_2 = [
    ["node2", "data 1"],
    ["node2", "data 2"],
]


@pytest.fixture(name="patch_register")
def _fixture_patch_register(monkeypatch):
    monkeypatch.setattr(agent_based_register._config, "get_section_plugin",
                        MOCK_SECTIONS.__getitem__)


@pytest.mark.parametrize("node_section_content,expected_result", [
    ({}, None),
    ({
        SectionName("one"): NODE_1
    }, {
        "parsed_by": "one",
        "node": "node1"
    }),
    ({
        SectionName("two"): NODE_1
    }, {
        "parsed_by": "two",
        "node": "node1"
    }),
    ({
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
    }, {
        "parsed_by": "two",
        "node": "node1",
    }),
])
def test_get_parsed_section(patch_register, node_section_content, expected_result):

    parsed_sections_broker = ParsedSectionsBroker({
        HostKey("node1", "127.0.0.1", SourceType.HOST):
            AgentHostSections(sections=node_section_content)
    })

    content = parsed_sections_broker.get_parsed_section(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        ParsedSectionName("parsed"),
    )

    assert expected_result == content,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, content)


@pytest.mark.parametrize("required_sections,expected_result", [
    (["nonexistent"], {}),
    (["parsed"], {
        "section": {
            "parsed_by": "two",
            "node": "node1"
        }
    }),
    (["parsed", "nonexistent"], {
        "section_parsed": {
            "parsed_by": "two",
            "node": "node1"
        },
        "section_nonexistent": None
    }),
    (["parsed", "parsed2"], {
        "section_parsed": {
            "parsed_by": "two",
            "node": "node1"
        },
        "section_parsed2": {
            "parsed_by": "three",
            "node": "node1"
        }
    }),
])
def test_get_section_kwargs(patch_register, required_sections, expected_result):

    node_section_content = {
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
        SectionName("three"): NODE_1
    }

    host_key = HostKey("node1", "127.0.0.1", SourceType.HOST)

    parsed_sections_broker = ParsedSectionsBroker(
        {host_key: AgentHostSections(sections=node_section_content)})

    kwargs = parsed_sections_broker.get_section_kwargs(
        host_key,
        [ParsedSectionName(n) for n in required_sections],
    )

    assert expected_result == kwargs,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, kwargs)


@pytest.mark.parametrize("required_sections,expected_result", [
    (["nonexistent"], {}),
    (["parsed"], {
        "section": {
            "node1": {
                "parsed_by": "two",
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
                "parsed_by": "two",
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
                "parsed_by": "two",
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
def test_get_section_cluster_kwargs(patch_register, required_sections, expected_result):

    node1_section_content = {
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
        SectionName("three"): NODE_1
    }

    node2_section_content = {
        SectionName("two"): NODE_2,
        SectionName("three"): NODE_2,
    }

    parsed_sections_broker = ParsedSectionsBroker({
        HostKey("node1", "127.0.0.1", SourceType.HOST):
            AgentHostSections(sections=node1_section_content),
        HostKey("node2", "127.0.0.1", SourceType.HOST):
            AgentHostSections(sections=node2_section_content),
    })

    kwargs = parsed_sections_broker.get_section_cluster_kwargs(
        [
            HostKey("node1", "127.0.0.1", SourceType.HOST),
            HostKey("node2", "127.0.0.1", SourceType.HOST),
        ],
        [ParsedSectionName(n) for n in required_sections],
    )

    assert expected_result == kwargs,\
           "Section content: Expected '%s' but got '%s'" % (expected_result, kwargs)


def _get_host_section_for_parse_sections_test():
    node_section_content = {
        SectionName("one"): NODE_1,
        SectionName("four"): NODE_1,
    }

    host_key = HostKey("node1", "127.0.0.1", SourceType.HOST)

    broker = ParsedSectionsBroker({host_key: AgentHostSections(sections=node_section_content)})

    return host_key, broker


def test_parse_sections_unsuperseded(monkeypatch):

    host_key, broker = _get_host_section_for_parse_sections_test()

    monkeypatch.setattr(
        agent_based_register._config,
        "get_section_plugin",
        MOCK_SECTIONS.get,
    )

    assert broker.determine_applicable_sections(
        {ParsedSectionName("parsed")},
        host_key.source_type,
    ) == [
        SECTION_ONE,
    ]
    assert broker.get_parsed_section(host_key, ParsedSectionName("parsed")) is not None


def test_parse_sections_superseded(monkeypatch):

    host_key, broker = _get_host_section_for_parse_sections_test()

    monkeypatch.setattr(
        agent_based_register._config,
        "get_section_plugin",
        MOCK_SECTIONS.get,
    )

    assert broker.determine_applicable_sections(
        {ParsedSectionName("parsed"), ParsedSectionName("parsed_four")},
        host_key.source_type,
    ) == [
        SECTION_FOUR,
    ]
    assert broker.get_parsed_section(host_key, ParsedSectionName("parsed")) is None


@pytest.mark.parametrize(
    "hostname,host_entries,cluster_node_keys,expected_result",
    [
        # No clusters
        ("heute", [
            ('heute', NODE_1),
        ], None, NODE_1),
        # Clusters: host_of_clustered_service returns cluster name. That means that
        # the service is assigned to the cluster
        ("cluster", [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], [
            HostKey("node1", "127.0.0.1", SourceType.HOST),
            HostKey("node2", "127.0.0.1", SourceType.HOST),
        ], NODE_1 + NODE_2),
        # host_of_clustered_service returns either the cluster or node name.
        # That means that the service is assigned to the cluster resp. not to the cluster
        ("cluster", [
            ('node1', NODE_1),
            ('node2', NODE_2),
        ], [
            HostKey("node2", "127.0.0.1", SourceType.HOST),
        ], NODE_2),
    ])
def test_get_section_content(hostname, host_entries, cluster_node_keys, expected_result):

    parsed_sections_broker = ParsedSectionsBroker({
        HostKey(nodename, "127.0.0.1", SourceType.HOST):
        AgentHostSections(sections={SectionName("section_plugin_name"): node_section_content})
        for nodename, node_section_content in host_entries
    })

    mhs = _MultiHostSections(parsed_sections_broker)

    section_content = mhs.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        HOST_ONLY,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = mhs.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        HOST_PRECEDENCE,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = mhs.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.MANAGEMENT),
        MGMT_ONLY,
        "section_plugin_name",
        False,
        cluster_node_keys=None if cluster_node_keys is None else
        [HostKey(hn, ip, SourceType.MANAGEMENT) for (hn, ip, _st) in cluster_node_keys],
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert section_content is None
