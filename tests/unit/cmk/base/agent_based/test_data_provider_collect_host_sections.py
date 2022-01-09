#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from tests.testlib.base import Scenario

import cmk.utils.piggyback
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import AgentRawData, HostKey, HostName, result, SectionName, SourceType

from cmk.snmplib.type_defs import SNMPRawData

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import (
    FetcherType,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    TCPFetcher,
)
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import Mode, NO_SELECTION

import cmk.base.config as config
from cmk.base.agent_based.data_provider import _collect_host_sections
from cmk.base.sources import make_cluster_sources, Source
from cmk.base.sources.agent import AgentRawDataSection
from cmk.base.sources.piggyback import PiggybackSource
from cmk.base.sources.programs import ProgramSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource


@pytest.fixture(name="mode", params=Mode)
def mode_fixture(request):
    return request.param


def make_scenario(hostname, tags):
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_ruleset(
        "datasource_programs",
        [
            ("echo 1", [], ["ds-host-14", "all-agents-host", "all-special-host"], {}),
        ],
    )
    ts.set_option(
        "special_agents",
        {
            "jolokia": [
                (
                    {},
                    [],
                    [
                        "special-host-14",
                        "all-agents-host",
                        "all-special-host",
                    ],
                    {},
                ),
            ]
        },
    )
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
                    sections={
                        SectionName("section_name_%s" % self.hostname): [["section_content"]]
                    },
                    cache_info={},
                    piggybacked_raw_data={},
                )
            ),
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
        ts = Scenario()
        ts.add_host(hostname)
        return ts.apply(monkeypatch)

    def test_no_sources(self, hostname, ipaddress, config_cache, host_config):
        host_sections = _collect_host_sections(
            sources=(),
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=(),
            selected_sections=NO_SELECTION,
        )[0]
        assert not host_sections

    def test_one_snmp_source(self, hostname, ipaddress, config_cache, host_config):
        raw_data: SNMPRawData = {}
        host_sections = _collect_host_sections(
            sources=[
                SNMPSource.snmp(
                    hostname,
                    ipaddress,
                    selected_sections=NO_SELECTION,
                    force_cache_refresh=False,
                    on_scan_error=OnError.RAISE,
                ),
            ],
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(raw_data),
                    Snapshot.null(),
                    FetcherType.SNMP,
                ),
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    @pytest.mark.parametrize(
        "source",
        [
            PiggybackSource,
            lambda hostname, ipaddress: ProgramSource.ds(
                hostname,
                ipaddress,
                template="",
            ),
            TCPSource,
        ],
    )
    def test_one_nonsnmp_source(self, hostname, ipaddress, config_cache, host_config, source):
        source = source(hostname, ipaddress)
        assert source.source_type is SourceType.HOST

        host_sections = _collect_host_sections(
            sources=[source],
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                ),
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, ipaddress, source.source_type)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    def test_multiple_sources_from_the_same_host(
        self,
        hostname,
        ipaddress,
        config_cache,
        host_config,
    ):
        sources = [
            ProgramSource.ds(hostname, ipaddress, template=""),
            TCPSource(hostname, ipaddress),
        ]

        host_sections = _collect_host_sections(
            sources=sources,
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                )
                for source in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, ipaddress, SourceType.HOST)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == len(sources) * [
            ["section_content"]
        ]

    def test_multiple_sources_from_different_hosts(
        self, hostname, ipaddress, config_cache, host_config
    ):
        sources = [
            ProgramSource.ds(HostName(f"{hostname}0"), ipaddress, template=""),
            TCPSource(HostName(f"{hostname}1"), ipaddress),
            TCPSource(HostName(f"{hostname}2"), ipaddress),
        ]

        host_sections = _collect_host_sections(
            sources=sources,
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=[
                FetcherMessage.from_raw_data(
                    result.OK(source.default_raw_data),
                    Snapshot.null(),
                    source.fetcher_type,
                )
                for source in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]

        assert set(host_sections) == {
            HostKey(HostName(f"{hostname}0"), ipaddress, SourceType.HOST),
            HostKey(HostName(f"{hostname}1"), ipaddress, SourceType.HOST),
            HostKey(HostName(f"{hostname}2"), ipaddress, SourceType.HOST),
        }

        for source in sources:
            assert host_sections[
                HostKey(source.hostname, source.ipaddress, SourceType.HOST)
            ].sections[SectionName(f"section_name_{source.hostname}")] == [["section_content"]]


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
            monkeypatch.setattr(
                fetcher,
                "fetch",
                lambda self, mode, fetcher=fetcher: {} if fetcher is SNMPFetcher else b"",
            )

        monkeypatch.setattr(
            Source,
            "parse",
            lambda self, *args, **kwargs: result.OK(
                DummyHostSection(
                    sections={
                        SectionName("section_name_%s" % self.hostname): [
                            ["section_content_%s" % self.hostname]
                        ]
                    },
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
            config,
            "lookup_ip_address",
            lambda host_config, family=None: nodes[host_config.hostname],
        )

    @pytest.fixture
    def host_config(self, cluster):
        return config.HostConfig.make_host_config(cluster)

    @pytest.fixture
    def config_cache(self, cluster, nodes, monkeypatch):
        ts = Scenario()
        ts.add_cluster(cluster, nodes=nodes.keys())
        return ts.apply(monkeypatch)

    @pytest.mark.usefixtures("config_cache")
    def test_host_config_for_cluster(self, host_config):
        assert host_config.is_cluster is True
        assert host_config.nodes

    def test_no_sources(self, cluster, nodes, config_cache, host_config):
        sources = make_cluster_sources(config_cache, host_config)

        host_sections = _collect_host_sections(
            sources=sources,
            file_cache_max_age=file_cache.MaxAge.none(),
            fetcher_messages=[
                # We do not pass sources explicitly but still append Piggyback.
                FetcherMessage.from_raw_data(
                    result.OK(AgentRawData(b"")),
                    Snapshot.null(),
                    FetcherType.PIGGYBACK,
                )
                for _s in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == len(nodes)

        key_clu = HostKey(cluster, None, SourceType.HOST)
        assert key_clu not in host_sections

        for hostname, addr in nodes.items():
            key = HostKey(hostname, addr, SourceType.HOST)
            assert key in host_sections

            section = host_sections[key]
            assert section.sections[SectionName("section_name_%s" % hostname)] == [
                ["section_content_%s" % hostname]
            ]
            assert not section.cache_info
            assert not section.piggybacked_raw_data


def test_get_host_sections_cluster(monkeypatch, mocker):
    hostname = HostName("testhost")
    hosts = {
        HostName("host0"): "10.0.0.0",
        HostName("host1"): "10.0.0.1",
        HostName("host2"): "10.0.0.2",
    }
    tags = {"agent": "no-agent"}
    section_name = SectionName("test_section")
    config_cache = make_scenario(hostname, tags).apply(monkeypatch)
    host_config = config.HostConfig.make_host_config(hostname)

    def fake_lookup_ip_address(host_config, family=None):
        return hosts[host_config.hostname]

    def check(_, *args, **kwargs):
        return result.OK(
            HostSections[AgentRawDataSection](sections={section_name: [[str(section_name)]]})
        )

    monkeypatch.setattr(
        config,
        "lookup_ip_address",
        fake_lookup_ip_address,
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

    sources = make_cluster_sources(config_cache, host_config)

    host_sections = _collect_host_sections(
        sources=sources,
        file_cache_max_age=host_config.max_cachefile_age,
        fetcher_messages=[
            FetcherMessage.from_raw_data(
                result.OK(source.default_raw_data),
                Snapshot.null(),
                source.fetcher_type,
            )
            for source in sources
        ],
        selected_sections=NO_SELECTION,
    )[0]
    assert len(host_sections) == len(hosts) == 3
    cmk.utils.piggyback._store_status_file_of.assert_not_called()  # type: ignore[attr-defined]
    assert cmk.utils.piggyback.remove_source_status_file.call_count == 3  # type: ignore[attr-defined]

    for host, addr in hosts.items():
        remove_source_status_file = cmk.utils.piggyback.remove_source_status_file
        remove_source_status_file.assert_any_call(host)  # type: ignore[attr-defined]
        key = HostKey(host, addr, SourceType.HOST)
        assert key in host_sections
        section = host_sections[key]
        assert len(section.sections) == 1
        assert next(iter(section.sections)) == section_name
        assert not section.cache_info
        assert not section.piggybacked_raw_data
