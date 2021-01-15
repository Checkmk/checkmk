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
from cmk.utils.type_defs import AgentRawData, ParsedSectionName, result, SectionName, SourceType

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
import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.sources import make_nodes, make_sources, Source, update_host_sections
from cmk.base.sources.agent import AgentHostSections
from cmk.base.sources.host_sections import (
    HostKey,
    HostSections,
    MultiHostSections,
    ParsedSectionsBroker,
)
from cmk.base.sources.piggyback import PiggybackSource
from cmk.base.sources.programs import ProgramSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource

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

    parsed_sections_broker = ParsedSectionsBroker()
    parsed_sections_broker.setdefault(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node_section_content),
    )

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

    parsed_sections_broker = ParsedSectionsBroker()
    parsed_sections_broker.setdefault(
        host_key,
        AgentHostSections(sections=node_section_content),
    )

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

    parsed_sections_broker = ParsedSectionsBroker()
    parsed_sections_broker.setdefault(
        HostKey("node1", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node1_section_content),
    )
    parsed_sections_broker.setdefault(
        HostKey("node2", "127.0.0.1", SourceType.HOST),
        AgentHostSections(sections=node2_section_content),
    )

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

    broker = ParsedSectionsBroker()
    broker.setdefault(
        host_key,
        AgentHostSections(sections=node_section_content),
    )
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

    parsed_sections_broker = ParsedSectionsBroker()
    for nodename, node_section_content in host_entries:
        parsed_sections_broker.setdefault(
            HostKey(nodename, "127.0.0.1", SourceType.HOST),
            AgentHostSections(sections={SectionName("section_plugin_name"): node_section_content}),
        )

    mhs = MultiHostSections(parsed_sections_broker)

    section_content = mhs.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        check_api_utils.HOST_ONLY,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = mhs.get_section_content(
        HostKey(hostname, "127.0.0.1", SourceType.HOST),
        check_api_utils.HOST_PRECEDENCE,
        "section_plugin_name",
        False,
        cluster_node_keys=cluster_node_keys,
        check_legacy_info={},  # only for parse_function lookup, not needed in this test
    )
    assert expected_result == section_content

    section_content = mhs.get_section_content(
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
        class DummyHostSection(HostSections):
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
            Source,
            "parse",
            lambda self, raw_data, *, selection: result.OK(
                DummyHostSection(
                    sections=
                    {SectionName("section_name_%s" % self.hostname): [["section_content"]]},
                    cache_info={},
                    piggybacked_raw_data={},
                )),
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
        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=(),
            ),
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=(),
            selected_sections=NO_SELECTION,
        )
        # The length is not zero because the function always sets,
        # at least, a piggy back section.
        assert len(broker) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in broker

        section = broker[key]

        # Public attributes from HostSections:
        assert not section.sections
        assert not section.cache_info
        assert not section.piggybacked_raw_data

    def test_one_snmp_source(self, hostname, ipaddress, mode, config_cache, host_config):
        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
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
                        selected_sections=NO_SELECTION,
                        on_scan_error="raise",
                    ),
                ],
            ),
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK({}),
                    Snapshot.null(),
                    FetcherType.SNMP,
                ),
            ],
            selected_sections=NO_SELECTION,
        )
        assert len(broker) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in broker

        section = broker[key]

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

        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=[source],
            ),
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                ),
            ],
            selected_sections=NO_SELECTION,
        )
        assert len(broker) == 1

        key = HostKey(hostname, ipaddress, source.source_type)
        assert key in broker

        section = broker[key]

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

        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
            make_nodes(
                config_cache,
                host_config,
                ipaddress,
                mode=mode,
                sources=sources,
            ),
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                ) for source in sources
            ],
            selected_sections=NO_SELECTION,
        )
        assert len(broker) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in broker

        section = broker[key]

        assert len(section.sections) == 1
        # yapf: disable
        assert (section.sections[SectionName("section_name_%s" % hostname)]
                == len(sources) * [["section_content"]])

    # shouldn't this be tested for a cluster?
    def test_multiple_sources_from_different_hosts(self, hostname, ipaddress, mode, config_cache, host_config):
        sources = [
            ProgramSource.ds(hostname + "0", ipaddress, mode=mode, template=""),
            TCPSource(hostname + "1", ipaddress, mode=mode),
            TCPSource(hostname + "2", ipaddress, mode=mode),
        ]

        nodes = make_nodes(
            config_cache,
            host_config,
            ipaddress,
            mode=mode,
            sources=sources,
        )

        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
            nodes,
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                )
                for _h, _i, sources in nodes for source in sources
            ],
            selected_sections=NO_SELECTION,
        )
        assert len(broker) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in broker

        section = broker[key]

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
        class DummyHostSection(HostSections):
            def _extend_section(self, section_name, section_content):
                pass

        for fetcher in (IPMIFetcher, PiggybackFetcher, ProgramFetcher, SNMPFetcher, TCPFetcher):
            monkeypatch.setattr(fetcher, "__enter__", lambda self: self)
            monkeypatch.setattr(fetcher, "fetch", lambda self, mode, fetcher=fetcher: {} if fetcher is SNMPFetcher else b"",)

        monkeypatch.setattr(
            Source,
            "parse",
            lambda self, *args, **kwargs: result.OK(DummyHostSection(
                sections={SectionName("section_name_%s" % self.hostname): [["section_content_%s" % self.hostname]]},
                cache_info={},
                piggybacked_raw_data={},
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
        made_nodes = make_nodes(
            config_cache,
            host_config,
            None,
            mode=mode,
            sources=(),
        )

        broker = ParsedSectionsBroker()
        update_host_sections(
            broker,
            made_nodes,
            max_cachefile_age=0,
            host_config=host_config,
            fetcher_messages=[
                # We do not pass sources explicitly but still append Piggyback.
                FetcherMessage.from_raw_data(
                    result.OK(AgentRawData(b"")),
                    Snapshot.null(),
                    FetcherType.PIGGYBACK,
                ) for _n in made_nodes
            ],
            selected_sections=NO_SELECTION,
        )
        assert len(broker) == len(nodes)

        key_clu = HostKey(cluster, None, SourceType.HOST)
        assert key_clu not in broker

        for hostname, addr in nodes.items():
            key = HostKey(hostname, addr, SourceType.HOST)
            assert key in broker

            section = broker[key]
            # yapf: disable
            assert (section.sections[SectionName("section_name_%s" % hostname)]
                    == [["section_content_%s" % hostname]])
            assert not section.cache_info
            assert not section.piggybacked_raw_data


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

    def check(_, *args, **kwargs):
        return result.OK(AgentHostSections(sections={section_name: [[str(section_name)]]}))

    monkeypatch.setattr(
        ip_lookup,
        "lookup_ip_address",
        lookup_ip_address,
    )
    monkeypatch.setattr(
        Source,
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

    nodes = make_nodes(
        config_cache,
        host_config,
        address,
        mode=mode,
        sources=make_sources(host_config, address, mode=mode)
    )

    broker = ParsedSectionsBroker()
    update_host_sections(
        broker,
        nodes,
        max_cachefile_age=host_config.max_cachefile_age,
        host_config=host_config,
        fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                )
                for _h, _i, sources in nodes for source in sources
            ],
        selected_sections=NO_SELECTION,
    )
    assert len(broker) == len(hosts) == 3
    cmk.utils.piggyback._store_status_file_of.assert_not_called()  # type: ignore[attr-defined]
    assert cmk.utils.piggyback.remove_source_status_file.call_count == 3  # type: ignore[attr-defined]

    for host, addr in hosts.items():
        remove_source_status_file = cmk.utils.piggyback.remove_source_status_file
        remove_source_status_file.assert_any_call(host)  # type: ignore[attr-defined]
        key = HostKey(host, addr, SourceType.HOST)
        assert key in broker
        section = broker[key]
        assert len(section.sections) == 1
        assert next(iter(section.sections)) == section_name
        assert not section.cache_info
        assert not section.piggybacked_raw_data
