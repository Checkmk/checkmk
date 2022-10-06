#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import os
import socket
from pathlib import Path

import pytest

from tests.testlib.base import Scenario

import cmk.utils.piggyback
from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import AgentRawData, HostKey, HostName, result, SectionName, SourceType

from cmk.snmplib.type_defs import SNMPRawData

from cmk.core_helpers import (
    FetcherType,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    TCPFetcher,
)
from cmk.core_helpers.cache import FileCacheMode, MaxAge
from cmk.core_helpers.host_sections import HostSections
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.snmp import SNMPFileCache
from cmk.core_helpers.type_defs import Mode, NO_SELECTION

import cmk.base.config as config
from cmk.base.agent_based.data_provider import _collect_host_sections
from cmk.base.config import HostConfig
from cmk.base.sources import make_sources, Source
from cmk.base.sources.agent import AgentRawDataSection
from cmk.base.sources.piggyback import PiggybackSource
from cmk.base.sources.programs import DSProgramSource
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
        return HostConfig.make_host_config(hostname)

    @pytest.fixture
    def config_cache(self, hostname, ipaddress, monkeypatch):
        ts = Scenario()
        ts.add_host(hostname)
        return ts.apply(monkeypatch)

    def test_no_sources(  # type:ignore[no-untyped-def]
        self, hostname, ipaddress, config_cache, host_config
    ) -> None:
        host_sections = _collect_host_sections(
            fetched=(),
            selected_sections=NO_SELECTION,
        )[0]
        assert not host_sections

    def test_one_snmp_source(  # type:ignore[no-untyped-def]
        self, hostname, ipaddress, config_cache, host_config
    ) -> None:
        raw_data: SNMPRawData = {}
        host_sections = _collect_host_sections(
            fetched=[
                (
                    SNMPSource(
                        hostname,
                        ipaddress,
                        source_type=SourceType.HOST,
                        fetcher_type=FetcherType.SNMP,
                        id_="snmp",
                        persisted_section_dir=Path(os.devnull),
                        on_scan_error=OnError.RAISE,
                        missing_sys_description=False,
                        sections={},
                        check_intervals={},
                        snmp_config=host_config.snmp_config(ipaddress),
                        keep_outdated=False,
                        do_status_data_inventory=False,
                        cache=SNMPFileCache(
                            hostname=hostname,
                            base_path=Path(os.devnull),
                            max_age=MaxAge.none(),
                            use_outdated=True,
                            simulation=True,
                            use_only_cache=True,
                            file_cache_mode=FileCacheMode.DISABLED,
                        ),
                    ),
                    FetcherMessage.from_raw_data(
                        result.OK(raw_data),
                        Snapshot.null(),
                        FetcherType.SNMP,
                    ),
                )
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, SourceType.HOST)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    @pytest.mark.parametrize(
        "make_source",
        [
            lambda hostname, ipaddress: PiggybackSource(
                hostname,
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.PIGGYBACK,
                id_="piggyback",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                time_settings=(),
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                is_piggyback_host=True,
                file_cache_max_age=MaxAge.none(),
            ),
            lambda hostname, ipaddress: DSProgramSource(
                hostname,
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.PROGRAM,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                cmdline="",
                stdin=None,
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                is_cmc=False,
                file_cache_max_age=MaxAge.none(),
            ),
            lambda hostname, ipaddress: TCPSource(
                hostname,
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.TCP,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                address_family=socket.AF_INET,
                agent_port=0,
                tcp_connect_timeout=0,
                agent_encryption={},
                file_cache_max_age=MaxAge.none(),
            ),
        ],
    )
    def test_one_nonsnmp_source(  # type:ignore[no-untyped-def]
        self, hostname, ipaddress, config_cache, host_config, make_source
    ) -> None:
        source = make_source(hostname, ipaddress)
        assert source.source_type is SourceType.HOST

        host_sections = _collect_host_sections(
            fetched=[
                (
                    source,
                    FetcherMessage.from_raw_data(
                        result.OK(AgentRawData(b"")),
                        Snapshot.null(),
                        source.fetcher_type,
                    ),
                )
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, source.source_type)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == [["section_content"]]

    @pytest.mark.usefixtures("config_cache")
    def test_multiple_sources_from_the_same_host(self, hostname, ipaddress, host_config):
        sources = [
            DSProgramSource(
                hostname,
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.PROGRAM,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                cmdline="",
                stdin=None,
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                is_cmc=False,
                file_cache_max_age=MaxAge.none(),
            ),
            TCPSource(
                hostname,
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.TCP,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                address_family=socket.AF_INET,
                agent_port=0,
                tcp_connect_timeout=0,
                agent_encryption={},
                file_cache_max_age=MaxAge.none(),
            ),
        ]

        host_sections = _collect_host_sections(
            fetched=[
                (
                    source,
                    FetcherMessage.from_raw_data(
                        result.OK(AgentRawData(b"")),
                        Snapshot.null(),
                        source.fetcher_type,
                    ),
                )
                for source in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == 1

        key = HostKey(hostname, SourceType.HOST)
        assert key in host_sections

        section = host_sections[key]

        assert len(section.sections) == 1
        assert section.sections[SectionName("section_name_%s" % hostname)] == len(sources) * [
            ["section_content"]
        ]

    def test_multiple_sources_from_different_hosts(self, hostname, ipaddress, monkeypatch):
        ts = Scenario()
        ts.add_host(f"{hostname}0")
        ts.add_host(f"{hostname}1")
        ts.add_host(f"{hostname}2")
        ts.apply(monkeypatch)

        sources = [
            DSProgramSource(
                HostName(f"{hostname}0"),
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.PROGRAM,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                cmdline="",
                stdin=None,
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                is_cmc=False,
                file_cache_max_age=MaxAge.none(),
            ),
            TCPSource(
                HostName(f"{hostname}1"),
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.TCP,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                address_family=socket.AF_INET,
                agent_port=0,
                tcp_connect_timeout=0,
                agent_encryption={},
                file_cache_max_age=MaxAge.none(),
            ),
            TCPSource(
                HostName(f"{hostname}2"),
                ipaddress,
                source_type=SourceType.HOST,
                fetcher_type=FetcherType.TCP,
                id_="agent",
                persisted_section_dir=Path(os.devnull),
                cache_dir=Path(os.devnull),
                simulation_mode=True,
                agent_simulator=True,
                keep_outdated=False,
                translation={},
                encoding_fallback="ascii",
                check_interval=0,
                address_family=socket.AF_INET,
                agent_port=0,
                tcp_connect_timeout=0,
                agent_encryption={},
                file_cache_max_age=MaxAge.none(),
            ),
        ]

        host_sections = _collect_host_sections(
            fetched=[
                (
                    source,
                    FetcherMessage.from_raw_data(
                        result.OK(AgentRawData(b"")),
                        Snapshot.null(),
                        source.fetcher_type,
                    ),
                )
                for source in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]

        assert set(host_sections) == {
            HostKey(HostName(f"{hostname}0"), SourceType.HOST),
            HostKey(HostName(f"{hostname}1"), SourceType.HOST),
            HostKey(HostName(f"{hostname}2"), SourceType.HOST),
        }

        for source in sources:
            assert host_sections[HostKey(source.hostname, SourceType.HOST)].sections[
                SectionName(f"section_name_{source.hostname}")
            ] == [["section_content"]]


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
        return HostConfig.make_host_config(cluster)

    @pytest.fixture
    def config_cache(self, cluster, nodes, monkeypatch):
        ts = Scenario()
        ts.add_cluster(cluster, nodes=nodes.keys())
        return ts.apply(monkeypatch)

    @pytest.mark.usefixtures("config_cache")
    def test_host_config_for_cluster(self, host_config) -> None:  # type:ignore[no-untyped-def]
        assert host_config.is_cluster is True
        assert host_config.nodes

    def test_no_sources(  # type:ignore[no-untyped-def]
        self, cluster, nodes, config_cache, host_config
    ) -> None:
        sources = make_sources(
            host_config,
            None,
            ip_lookup=lambda _: None,
            selected_sections=NO_SELECTION,
            on_scan_error=OnError.RAISE,
            force_snmp_cache_refresh=False,
            simulation_mode=True,
            agent_simulator=True,
            keep_outdated=False,
            translation={},
            encoding_fallback="ascii",
            missing_sys_description=True,
            file_cache_max_age=MaxAge.none(),
        )

        host_sections = _collect_host_sections(
            fetched=[
                (
                    source,
                    FetcherMessage.from_raw_data(
                        result.OK(AgentRawData(b"")),
                        Snapshot.null(),
                        FetcherType.PIGGYBACK,
                    ),
                )
                for source in sources
            ],
            selected_sections=NO_SELECTION,
        )[0]
        assert len(host_sections) == len(nodes)

        key_clu = HostKey(cluster, SourceType.HOST)
        assert key_clu not in host_sections

        for hostname in nodes:
            key = HostKey(hostname, SourceType.HOST)
            assert key in host_sections

            section = host_sections[key]
            assert section.sections[SectionName("section_name_%s" % hostname)] == [
                ["section_content_%s" % hostname]
            ]
            assert not section.cache_info
            assert not section.piggybacked_raw_data


def test_get_host_sections_cluster(monkeypatch, mocker) -> None:  # type:ignore[no-untyped-def]
    hostname = HostName("testhost")
    hosts = {
        HostName("host0"): "10.0.0.0",
        HostName("host1"): "10.0.0.1",
        HostName("host2"): "10.0.0.2",
    }
    tags = {"agent": "no-agent"}
    section_name = SectionName("test_section")
    make_scenario(hostname, tags).apply(monkeypatch)
    host_config = HostConfig.make_host_config(hostname)

    def check(_, *args, **kwargs):
        return result.OK(
            HostSections[AgentRawDataSection](sections={section_name: [[str(section_name)]]})
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

    sources = make_sources(
        host_config,
        None,
        ip_lookup=lambda host_name: hosts[host_name],
        selected_sections=NO_SELECTION,
        on_scan_error=OnError.RAISE,
        force_snmp_cache_refresh=False,
        simulation_mode=True,
        agent_simulator=True,
        keep_outdated=False,
        translation={},
        encoding_fallback="ascii",
        missing_sys_description=True,
        file_cache_max_age=MaxAge.none(),
    )

    host_sections = _collect_host_sections(
        fetched=[
            (
                source,
                FetcherMessage.from_raw_data(
                    result.OK(AgentRawData(b"")),
                    Snapshot.null(),
                    source.fetcher_type,
                ),
            )
            for source in sources
        ],
        selected_sections=NO_SELECTION,
    )[0]
    assert len(host_sections) == len(hosts) == 3
    cmk.utils.piggyback._store_status_file_of.assert_not_called()  # type: ignore[attr-defined]
    assert cmk.utils.piggyback.remove_source_status_file.call_count == 3  # type: ignore[attr-defined]

    for host in hosts:
        remove_source_status_file = cmk.utils.piggyback.remove_source_status_file
        remove_source_status_file.assert_any_call(host)  # type: ignore[attr-defined]
        key = HostKey(host, SourceType.HOST)
        assert key in host_sections
        section = host_sections[key]
        assert len(section.sections) == 1
        assert next(iter(section.sections)) == section_name
        assert not section.cache_info
        assert not section.piggybacked_raw_data
