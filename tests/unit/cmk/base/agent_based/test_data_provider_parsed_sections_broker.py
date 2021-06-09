#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Callable, Iterable

import pytest  # type: ignore[import]

from cmk.utils.type_defs import HostKey, ParsedSectionName, SectionName, SourceType

from cmk.core_helpers.type_defs import AgentRawDataSection

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.api.agent_based.register.section_plugins as section_plugins
from cmk.base.agent_based.checking._legacy_mode import _MultiHostSections
from cmk.base.agent_based.data_provider import ParsedSectionsBroker, SectionsParser
from cmk.base.check_utils import HOST_ONLY, HOST_PRECEDENCE, MGMT_ONLY
from cmk.base.sources.agent import AgentHostSections


def _test_section(
    *,
    section_name: str,
    parsed_section_name: str,
    parse_function: Callable,
    supersedes: Iterable[str],
) -> section_plugins.AgentSectionPlugin:
    return section_plugins.trivial_section_factory(SectionName(section_name))._replace(
        parsed_section_name=ParsedSectionName(parsed_section_name),
        parse_function=parse_function,
        supersedes={SectionName(n) for n in supersedes},
    )


SECTION_ONE = _test_section(
    section_name="one",
    parsed_section_name="parsed",
    parse_function=lambda x: {
        "parsed_by": "one",
        "node": x[0][0]
    },
    supersedes=(),
)

SECTION_TWO = _test_section(
    section_name="two",
    parsed_section_name="parsed",
    parse_function=lambda x: {
        "parsed_by": "two",
        "node": x[0][0]
    },
    supersedes={"one"},
)

SECTION_THREE = _test_section(
    section_name="three",
    parsed_section_name="parsed2",
    parse_function=lambda x: {
        "parsed_by": "three",
        "node": x[0][0]
    },
    supersedes=(),
)

SECTION_FOUR = _test_section(
    section_name="four",
    parsed_section_name="parsed_four",
    parse_function=lambda x: {
        "parsed_by": "four",
        "node": x[0][0]
    },
    supersedes={"one"},
)

MOCK_SECTIONS = {
    SECTION_ONE.name: SECTION_ONE,
    SECTION_TWO.name: SECTION_TWO,
    SECTION_THREE.name: SECTION_THREE,
    SECTION_FOUR.name: SECTION_FOUR,
}

NODE_1: AgentRawDataSection = [
    ["node1", "data 1"],
    ["node1", "data 2"],
]

NODE_2: AgentRawDataSection = [
    ["node2", "data 1"],
    ["node2", "data 2"],
]


@pytest.fixture(name="patch_register")
def _fixture_patch_register(monkeypatch):
    monkeypatch.setattr(agent_based_register._config, "get_section_plugin",
                        MOCK_SECTIONS.__getitem__)


@pytest.mark.parametrize("node_sections,expected_result", [
    (AgentHostSections(sections={}), None),
    (AgentHostSections(sections={SectionName("one"): NODE_1}), {
                                     "parsed_by": "one",
                                     "node": "node1"
                                 }),
    (AgentHostSections(sections={SectionName("two"): NODE_1}), {
                                     "parsed_by": "two",
                                     "node": "node1"
                                 }),
    (AgentHostSections(sections={
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
    }), {
        "parsed_by": "two",
        "node": "node1",
    }),
])
def test_get_parsed_section(patch_register, node_sections, expected_result):

    parsed_sections_broker = ParsedSectionsBroker({
        HostKey("node1", "127.0.0.1", SourceType.HOST): SectionsParser(host_sections=node_sections)
    })

    content = parsed_sections_broker.get_parsed_section(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        ParsedSectionName("parsed"),
    )

    assert expected_result == content


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

    node_sections = AgentHostSections(sections={
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
        SectionName("three"): NODE_1
    })

    host_key = HostKey("node1", "127.0.0.1", SourceType.HOST)

    parsed_sections_broker = ParsedSectionsBroker({
        host_key: SectionsParser(host_sections=node_sections),
    })

    kwargs = parsed_sections_broker.get_section_kwargs(
        host_key,
        [ParsedSectionName(n) for n in required_sections],
    )

    assert expected_result == kwargs


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

    node1_sections = AgentHostSections(sections={
        SectionName("one"): NODE_1,
        SectionName("two"): NODE_1,
        SectionName("three"): NODE_1
    })

    node2_sections = AgentHostSections(sections={
        SectionName("two"): NODE_2,
        SectionName("three"): NODE_2,
    })

    parsed_sections_broker = ParsedSectionsBroker({
        HostKey("node1", "127.0.0.1", SourceType.HOST): SectionsParser(host_sections=node1_sections
                                                                      ),
        HostKey("node2", "127.0.0.1", SourceType.HOST): SectionsParser(host_sections=node2_sections
                                                                      ),
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
    node_sections = AgentHostSections(sections={
        SectionName("one"): NODE_1,
        SectionName("four"): NODE_1,
    })

    host_key = HostKey("node1", "127.0.0.1", SourceType.HOST)

    broker = ParsedSectionsBroker({host_key: SectionsParser(host_sections=node_sections)})

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
        HostKey(nodename, "127.0.0.1",
                SourceType.HOST): SectionsParser(host_sections=AgentHostSections(
                    sections={SectionName("section_plugin_name"): node_section_content}))
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
