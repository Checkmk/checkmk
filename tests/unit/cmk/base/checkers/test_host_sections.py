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
from cmk.utils.type_defs import (
    OKResult,
    ParsedSectionName,
    SectionName,
    SourceType,
)

from cmk.fetchers import IPMIFetcher, PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.checkers import (
    _checkers,
    ABCHostSections,
    ABCSource,
    make_nodes,
    make_sources,
    Mode,
    update_host_sections,
)
from cmk.base.checkers.agent import AgentHostSections
from cmk.base.checkers.host_sections import HostKey, MultiHostSections
from cmk.base.checkers.piggyback import PiggybackSource
from cmk.base.checkers.programs import ProgramSource
from cmk.base.checkers.snmp import SNMPHostSections, SNMPSource
from cmk.base.checkers.tcp import TCPSource

_TestSection = collections.namedtuple(
    "TestSection",
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


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


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

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node_section_content),
    )

    content = multi_host_sections.get_parsed_section(
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

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault(
        host_key,
        AgentHostSections(sections=node_section_content),
    )

    kwargs = multi_host_sections.get_section_kwargs(
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

    multi_host_sections = MultiHostSections()
    multi_host_sections.setdefault(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node1_section_content),
    )
    multi_host_sections.setdefault(
        HostKey("node2", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node2_section_content),
    )

    kwargs = multi_host_sections.get_section_cluster_kwargs(
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

    mhs = MultiHostSections()
    mhs.setdefault(
        host_key,
        AgentHostSections(sections=node_section_content),
    )
    return host_key, mhs


def test_parse_sections_unsuperseded(monkeypatch):

    host_key, mhs = _get_host_section_for_parse_sections_test()

    monkeypatch.setattr(
        agent_based_register._config,
        "get_section_plugin",
        MOCK_SECTIONS.get,
    )

    assert mhs.determine_applicable_sections(
        {ParsedSectionName("parsed")},
        host_key.source_type,
    ) == [
        SECTION_ONE,
    ]
    assert mhs.get_parsed_section(host_key, ParsedSectionName("parsed")) is not None


def test_parse_sections_superseded(monkeypatch):

    host_key, mhs = _get_host_section_for_parse_sections_test()

    monkeypatch.setattr(
        agent_based_register._config,
        "get_section_plugin",
        MOCK_SECTIONS.get,
    )

    assert mhs.determine_applicable_sections(
        {ParsedSectionName("parsed"), ParsedSectionName("parsed_four")},
        host_key.source_type,
    ) == [
        SECTION_FOUR,
    ]
    assert mhs.get_parsed_section(host_key, ParsedSectionName("parsed")) is None


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

    multi_host_sections = MultiHostSections()
    for nodename, node_section_content in host_entries:
        multi_host_sections.setdefault(
            HostKey(nodename, "127.0.0.1", SourceType.HOST),
            AgentHostSections(sections={SectionName("section_plugin_name"): node_section_content}),
        )

    section_content = multi_host_sections.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        check_api_utils.HOST_ONLY,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = multi_host_sections.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        check_api_utils.HOST_PRECEDENCE,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = multi_host_sections.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.MANAGEMENT),
        check_api_utils.MGMT_ONLY,
        "section_plugin_name",
        False,
        cluster_node_keys=None if cluster_node_keys is None else
        [HostKey(hn, ip, SourceType.MANAGEMENT) for (hn, ip, _st) in cluster_node_keys],
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert section_content is None


def make_scenario(hostname, tags):
    ts = Scenario().add_host(hostname, tags=tags)
    ts.set_ruleset("datasource_programs", [
        ('echo 1', [], ['ds-host-14', 'all-agents-host', 'all-special-host'], {}),
    ])
    ts.set_option(
        "special_agents",
        {"jolokia": [({}, [], [
            'special-host-14',
            'all-agents-host',
            'all-special-host',
        ], {}),]})
    return ts


class TestMakeHostSectionsHosts:
    @pytest.fixture(autouse=False)
    def patch_fs(self, fs):
        # piggyback.store_piggyback_raw_data() writes to disk.
        pass

    @pytest.fixture(autouse=True)
    def patch_io(self, monkeypatch):
        class DummyHostSection(ABCHostSections):
            def _extend_section(self, section_name, section_content):
                pass

        for fetcher in (IPMIFetcher, PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher):
            monkeypatch.setattr(fetcher, "__enter__", lambda self: self)
            monkeypatch.setattr(
                fetcher,
                "fetch",
                lambda self, mode, fetcher=fetcher: {} if fetcher is SNMPFetcher else b"",
            )

        monkeypatch.setattr(
            ABCSource,
            "parse",
            lambda self, raw_data: OKResult(
                DummyHostSection(
                    sections=
                    {SectionName("section_name_%s" % self.hostname): [["section_content"]]},
                    cache_info={},
                    piggybacked_raw_data={},
                    persisted_sections="",
                ),),
        )

    @pytest.fixture
    def hostname(self):
        return "testhost"

    @pytest.fixture
    def ipaddress(self):
        return "1.2.3.4"

    @pytest.fixture
    def host_config(self, hostname):
        return config.HostConfig.make_host_config(hostname)

    @pytest.fixture
    def config_cache(self, hostname, ipaddress, monkeypatch):
        ts = Scenario().add_host(hostname)
        return ts.apply(monkeypatch)

    def test_no_sources(self, hostname, ipaddress, mode, config_cache, host_config):
        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=[],
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        # The length is not zero because the function always sets,
        # at least, a piggy back section.
        assert len(mhs) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in mhs

        section = mhs[key]
        assert isinstance(section, AgentHostSections)

        # Public attributes from ABCHostSections:
        assert not section.sections
        assert not section.cache_info
        assert not section.piggybacked_raw_data
        assert not section.persisted_sections

    def test_one_snmp_source(self, hostname, ipaddress, mode, config_cache, host_config):
        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=[
                    SNMPSource.snmp(
                        hostname,
                        ipaddress,
                        mode=mode,
                    ),
                ],
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        assert len(mhs) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in mhs

        section = mhs[key]
        assert isinstance(section, SNMPHostSections)

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    @pytest.mark.parametrize(
        "source",
        [
            lambda hostname, ipaddress, *, mode: PiggybackSource(
                hostname,
                ipaddress,
                mode=mode,
            ),
            lambda hostname, ipaddress, *, mode: ProgramSource.ds(
                hostname,
                ipaddress,
                mode=mode,
                template="",
            ),
            lambda hostname, ipaddress, *, mode: TCPSource(
                hostname,
                ipaddress,
                mode=mode,
            ),
        ],
    )
    def test_one_nonsnmp_source(self, hostname, ipaddress, mode, config_cache, host_config, source):
        source = source(hostname, ipaddress, mode=mode)
        assert source.source_type is SourceType.HOST

        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=[source],
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        assert len(mhs) == 1

        key = HostKey(hostname, ipaddress, source.source_type)
        assert key in mhs

        section = mhs[key]
        assert isinstance(section, AgentHostSections)

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    def test_multiple_sources_from_the_same_host(
        self,
        hostname,
        ipaddress,
        mode,
        config_cache,
        host_config,
    ):
        sources = [
            ProgramSource.ds(
                hostname,
                ipaddress,
                mode=mode,
                template="",
            ),
            TCPSource(
                hostname,
                ipaddress,
                mode=mode,
            ),
        ]

        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=sources,
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        assert len(mhs) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in mhs

        section = mhs[key]
        assert isinstance(section, AgentHostSections)

        assert len(section.sections) == 1
        # yapf: disable
        assert (section.sections[SectionName("section_name_%s" % hostname)]
                == len(sources) * [["section_content"]])

    def test_multiple_sources_from_different_hosts(self, hostname, ipaddress, mode, config_cache, host_config):
        sources = [
            ProgramSource.ds(hostname + "0", ipaddress,
                                                    mode=mode,
                                                   template="",),
            TCPSource(hostname + "1", ipaddress, mode=mode,),
            TCPSource(hostname + "2", ipaddress, mode=mode,),
        ]

        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=sources,
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        assert len(mhs) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in mhs

        section = mhs[key]
        assert isinstance(section, AgentHostSections)

        assert len(section.sections) == len(sources)
        for source in sources:
            # yapf: disable
            assert (
                section.sections[SectionName("section_name_%s" % source.hostname)]
                == [["section_content"]])


class TestMakeHostSectionsClusters:
    @pytest.fixture(autouse=False)
    def patch_fs(self, fs):
        # piggyback.store_piggyback_raw_data() writes to disk.
        pass

    @pytest.fixture(autouse=True)
    def patch_io(self, monkeypatch):
        class DummyHostSection(ABCHostSections):
            def _extend_section(self, section_name, section_content):
                pass

        for fetcher in (IPMIFetcher, PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher):
            monkeypatch.setattr(fetcher, "__enter__", lambda self: self)
            monkeypatch.setattr(fetcher, "fetch", lambda self, mode, fetcher=fetcher: {} if fetcher is SNMPFetcher else b"",)

        monkeypatch.setattr(
            ABCSource,
            "parse",
            lambda self, *args, **kwargs: OKResult(DummyHostSection(
                sections={SectionName("section_name_%s" % self.hostname): [["section_content"]]},
                cache_info={},
                piggybacked_raw_data={},
                persisted_sections="",
            ),
        ),
        )

    @pytest.fixture
    def cluster(self):
        return "testclu"

    @pytest.fixture
    def nodes(self):
        return {
            "node0": "10.0.0.10",
            "node1": "10.0.0.11",
            "node2": "10.0.0.12",
        }

    @pytest.fixture(autouse=True)
    def fake_lookup_ip_address(self, nodes, monkeypatch):
        monkeypatch.setattr(
            ip_lookup,
            "lookup_ip_address",
            lambda host_config, family=None, for_mgmt_board=False: nodes[host_config.hostname],
        )

    @pytest.fixture
    def host_config(self, cluster):
        return config.HostConfig.make_host_config(cluster)

    @pytest.fixture
    def config_cache(self, cluster, nodes, monkeypatch):
        ts = Scenario().add_cluster(cluster, nodes=nodes.keys())
        return ts.apply(monkeypatch)

    @pytest.mark.usefixtures("config_cache")
    def test_host_config_for_cluster(self, host_config):
        assert host_config.is_cluster is True
        assert host_config.nodes

    def test_no_sources(self, cluster, nodes, config_cache, host_config, mode):
        mhs = MultiHostSections()
        update_host_sections(
            mhs,
            make_nodes(
                config_cache,
                host_config,
                None,
                mode=mode,
                sources=[],
            ),
            max_cachefile_age=0,
            selected_raw_sections=None,
            host_config=host_config,
        )
        assert len(mhs) == len(nodes)

        key_clu = HostKey(cluster, None, SourceType.HOST)
        assert key_clu not in mhs

        for hostname, addr in nodes.items():
            key = HostKey(hostname, addr, SourceType.HOST)
            assert key in mhs

            section = mhs[key]
            # yapf: disable
            assert (section.sections[SectionName("section_name_%s" % hostname)]
                    == [["section_content"]])
            assert not section.cache_info
            assert not section.piggybacked_raw_data
            assert not section.persisted_sections


def test_get_host_sections_cluster(mode, monkeypatch, mocker):
    hostname = "testhost"
    hosts = {
        "host0": "10.0.0.0",
        "host1": "10.0.0.1",
        "host2": "10.0.0.2",
    }
    address = "1.2.3.4"
    tags = {"agent": "no-agent"}
    section_name = SectionName("test_section")
    config_cache = make_scenario(hostname, tags).apply(monkeypatch)
    host_config = config.HostConfig.make_host_config(hostname)

    def lookup_ip_address(host_config, family=None, for_mgmt_board=False):
        return hosts[host_config.hostname]

    def make_piggybacked_sections(hc):
        if hc.nodes == host_config.nodes:
            return {section_name: True}
        return {}

    def check(_, *args, **kwargs):
        return OKResult(AgentHostSections(sections={section_name: [[str(section_name)]]}))

    monkeypatch.setattr(
        ip_lookup,
        "lookup_ip_address",
        lookup_ip_address,
    )
    monkeypatch.setattr(
        _checkers,
        "_make_piggybacked_sections",
        make_piggybacked_sections,
    )
    monkeypatch.setattr(
        ABCSource,
        "parse",
        check,
    )
    mocker.patch.object(
        cmk.utils.piggyback,
        "remove_source_status_file",
        autospec=True,
    )
    mocker.patch.object(
        cmk.utils.piggyback,
        "_store_status_file_of",
        autospec=True,
    )

    # Create a cluster
    host_config.nodes = list(hosts.keys())

    mhs = MultiHostSections()
    update_host_sections(
        mhs,
        make_nodes(
            config_cache,
            host_config,
            address,
            mode=mode,
            sources=make_sources(host_config, address, mode=mode),
        ),
        max_cachefile_age=host_config.max_cachefile_age,
        selected_raw_sections=None,
        host_config=host_config,
    )
    assert len(mhs) == len(hosts) == 3
    cmk.utils.piggyback._store_status_file_of.assert_not_called()  # type: ignore[attr-defined]
    assert cmk.utils.piggyback.remove_source_status_file.call_count == 3  # type: ignore[attr-defined]

    for host, addr in hosts.items():
        remove_source_status_file = cmk.utils.piggyback.remove_source_status_file
        remove_source_status_file.assert_any_call(host)  # type: ignore[attr-defined]
        key = HostKey(host, addr, SourceType.HOST)
        assert key in mhs
        section = mhs[key]
        assert len(section.sections) == 1
        assert next(iter(section.sections)) == section_name
        assert not section.cache_info
        assert not section.piggybacked_raw_data
        assert not section.persisted_sections
