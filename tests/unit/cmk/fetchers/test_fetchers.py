#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import socket
from abc import ABC, abstractmethod
from collections import namedtuple
from pathlib import Path
from typing import Optional

import pytest  # type: ignore[import]
from pyghmi.exceptions import IpmiException  # type: ignore[import]

import cmk.utils.version as cmk_version
from cmk.utils.type_defs import AgentRawData, result, SectionName

from cmk.snmplib import snmp_table
from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackend,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPTable,
)

from cmk.fetchers import FetcherType, MaxAge, MKFetcherError, snmp
from cmk.fetchers.agent import DefaultAgentFileCache, NoCache
from cmk.fetchers.ipmi import IPMIFetcher
from cmk.fetchers.piggyback import PiggybackFetcher
from cmk.fetchers.program import ProgramFetcher
from cmk.fetchers.snmp import (
    SectionMeta,
    SNMPFetcher,
    SNMPFileCache,
    SNMPPluginStore,
    SNMPPluginStoreItem,
)
from cmk.fetchers.tcp import TCPFetcher
from cmk.fetchers.type_defs import Mode

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


def json_identity(data):
    return json.loads(json.dumps(data))


def clone_file_cache(file_cache):
    return type(file_cache)(
        base_path=file_cache.base_path,
        max_age=file_cache.max_age,
        disabled=file_cache.disabled,
        use_outdated=file_cache.use_outdated,
        simulation=file_cache.simulation,
    )


class TestFileCache:
    @pytest.fixture(params=[DefaultAgentFileCache, NoCache, SNMPFileCache])
    def file_cache(self, request):
        return request.param(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=False,
            simulation=True,
        )

    def test_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))


class TestNoCache:
    @pytest.fixture
    def path(self, tmp_path):
        return tmp_path / "database"

    @pytest.fixture
    def file_cache(self, path):
        return NoCache(
            base_path=path,
            max_age=MaxAge(discovery=999, checking=0, inventory=0),
            disabled=False,
            use_outdated=False,
            simulation=False,
        )

    @pytest.fixture
    def agent_raw_data(self):
        return AgentRawData(b"<<<check_mk>>>\nagent raw data")

    def test_write_and_read_is_noop(self, file_cache, agent_raw_data):
        mode = Mode.DISCOVERY

        assert not file_cache.disabled
        assert file_cache.make_path(mode) == Path(os.devnull)

        file_cache.write(agent_raw_data, mode)

        assert file_cache.make_path(mode) == Path(os.devnull)
        assert file_cache.read(mode) is None

    def test_disabled_write_and_read(self, file_cache, agent_raw_data):
        mode = Mode.DISCOVERY

        file_cache.disabled = True
        assert file_cache.disabled is True
        assert file_cache.make_path(mode) == Path(os.devnull)

        file_cache.write(agent_raw_data, mode)

        assert file_cache.make_path(mode) == Path(os.devnull)
        assert file_cache.read(mode) is None


class TestDefaultFileCache_and_SNMPFileCache:
    @pytest.fixture
    def path(self, tmp_path):
        return tmp_path / "database"

    @pytest.fixture(params=[DefaultAgentFileCache, SNMPFileCache])
    def file_cache(self, path, request):
        return request.param(
            base_path=path,
            max_age=MaxAge(discovery=999, checking=0, inventory=0),
            disabled=False,
            use_outdated=False,
            simulation=False,
        )

    @pytest.fixture
    def raw_data(self, file_cache):
        if isinstance(file_cache, DefaultAgentFileCache):
            return AgentRawData(b"<<<check_mk>>>\nagent raw data")
        assert isinstance(file_cache, SNMPFileCache)
        table: SNMPTable = []
        raw_data = SNMPRawData({SectionName("X"): table})
        return raw_data

    def test_write_and_read(self, file_cache, raw_data):
        mode = Mode.DISCOVERY

        assert not file_cache.disabled
        assert not file_cache.make_path(mode).exists()

        file_cache.write(raw_data, mode)

        assert file_cache.make_path(mode).exists()
        assert file_cache.read(mode) == raw_data

        # Now with another instance
        clone = clone_file_cache(file_cache)
        assert clone.make_path(mode).exists()
        assert clone.read(mode) == raw_data

    def test_disabled_write(self, file_cache, raw_data):
        mode = Mode.DISCOVERY

        file_cache.disabled = True
        assert file_cache.disabled is True
        assert not file_cache.make_path(mode).exists()

        file_cache.write(raw_data, mode)

        assert not file_cache.make_path(mode).exists()
        assert file_cache.read(mode) is None

    def test_disabled_read(self, file_cache, raw_data):
        mode = Mode.DISCOVERY

        file_cache.write(raw_data, mode)
        assert file_cache.make_path(mode).exists()
        assert file_cache.read(mode) == raw_data

        file_cache.disabled = True
        assert file_cache.make_path(mode).exists()
        assert file_cache.read(mode) is None


class StubFileCache(DefaultAgentFileCache):
    """Holds the data to be cached in-memory for testing"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Optional[AgentRawData] = None

    def write(self, raw_data: AgentRawData, mode: Mode) -> None:
        if not self.cache_write(mode):
            return None

        self.cache = raw_data

    def read(self, mode: Mode) -> Optional[AgentRawData]:
        if not self.cache_read(mode):
            return None

        return self.cache


class TestIPMIFetcher:
    @pytest.fixture
    def file_cache(self):
        return StubFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=False,
        )

    @pytest.fixture
    def fetcher(self, file_cache):
        return IPMIFetcher(
            file_cache,
            address="1.2.3.4",
            username="us3r",
            password="secret",
        )

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.file_cache == fetcher.file_cache
        assert other.address == fetcher.address
        assert other.username == fetcher.username
        assert other.password == fetcher.password

    def test_with_cached_does_not_open(self, file_cache, monkeypatch) -> None:
        def open_(*args):
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)
        with IPMIFetcher(
                file_cache,
                address="127.0.0.1",
                username="",
                password="",
        ) as fetcher:
            fetched = fetcher.fetch(Mode.CHECKING)

        assert fetched.is_ok()

    def test_command_raises_IpmiException_handling(self, file_cache, monkeypatch):
        def open_(*args):
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        with IPMIFetcher(
                file_cache,
                address="127.0.0.1",
                username="",
                password="",
        ) as fetcher:
            fetched = fetcher.fetch(Mode.CHECKING)

        assert isinstance(fetched.error, MKFetcherError)

    def test_parse_sensor_reading_standard_case(self, fetcher):
        reading = SensorReading(  #
            ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
        assert fetcher._parse_sensor_reading(  #
            0,
            reading) == [b"0", b"Hugo", b"hugo-type", b"N/A", b"", b"lower non-critical threshold"]

    def test_parse_sensor_reading_false_positive(self, fetcher):
        reading = SensorReading(  #
            ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
        assert fetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Dingeling", b"FancyDevice", b"3.14", b"C", b"Present"]


class TestPiggybackFetcher:
    @pytest.fixture
    def file_cache(self):
        return NoCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, file_cache):
        return PiggybackFetcher(
            file_cache,
            hostname="host",
            address="1.2.3.4",
            time_settings=[],
        )

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.hostname == fetcher.hostname
        assert other.address == fetcher.address
        assert other.time_settings == fetcher.time_settings


class TestProgramFetcher:
    @pytest.fixture
    def file_cache(self):
        return DefaultAgentFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, file_cache):
        return ProgramFetcher(
            file_cache,
            cmdline="/bin/true",
            stdin=None,
            is_cmc=False,
        )

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, ProgramFetcher)
        assert other.cmdline == fetcher.cmdline
        assert other.stdin == fetcher.stdin
        assert other.is_cmc == fetcher.is_cmc


class TestSNMPPluginStore:
    @pytest.fixture
    def store(self):
        return SNMPPluginStore({
            SectionName("section0"): SNMPPluginStoreItem(
                [
                    BackendSNMPTree(base=".1.2.3",
                                    oids=[
                                        BackendOIDSpec("4.5", "string", False),
                                        BackendOIDSpec("9.7", "string", False)
                                    ]),
                    BackendSNMPTree(base=".8.9.0",
                                    oids=[
                                        BackendOIDSpec("1.2", "string", False),
                                        BackendOIDSpec("3.4", "string", False)
                                    ]),
                ],
                SNMPDetectSpec([[
                    ("oid0", "regex0", True),
                    ("oid1", "regex1", True),
                    ("oid2", "regex2", False),
                ]]),
                False,
            ),
            SectionName("section1"): SNMPPluginStoreItem(
                [
                    BackendSNMPTree(base=".1.2.3",
                                    oids=[
                                        BackendOIDSpec("4.5", "string", False),
                                        BackendOIDSpec("6.7.8", "string", False)
                                    ])
                ],
                SNMPDetectSpec([[
                    ("oid3", "regex3", True),
                    ("oid4", "regex4", False),
                ]]),
                False,
            ),
        })

    def test_serialization(self, store):
        assert SNMPPluginStore.deserialize(store.serialize()) == store


class ABCTestSNMPFetcher(ABC):
    @abstractmethod
    @pytest.fixture
    def file_cache(self):
        raise NotImplementedError()

    @pytest.fixture(autouse=True)
    def snmp_plugin_fixture(self):
        SNMPFetcher.plugin_store = SNMPPluginStore({
            SectionName("pim"): SNMPPluginStoreItem(
                trees=[
                    BackendSNMPTree(base=".1.1.1",
                                    oids=[
                                        BackendOIDSpec("1.2", "string", False),
                                        BackendOIDSpec("3.4", "string", False)
                                    ])
                ],
                detect_spec=SNMPDetectSpec([[("1.2.3.4", "pim device", True)]]),
                inventory=False,
            ),
            SectionName("pam"): SNMPPluginStoreItem(
                trees=[
                    BackendSNMPTree(
                        base=".1.2.3",
                        oids=[
                            BackendOIDSpec("4.5", "string", False),
                            BackendOIDSpec("6.7", "string", False),
                            BackendOIDSpec("8.9", "string", False)
                        ],
                    ),
                ],
                detect_spec=SNMPDetectSpec([[("1.2.3.4", "pam device", True)]]),
                inventory=False,
            ),
            SectionName("pum"): SNMPPluginStoreItem(
                trees=[
                    BackendSNMPTree(base=".2.2.2", oids=[BackendOIDSpec("2.2", "string", False)]),
                    BackendSNMPTree(base=".3.3.3", oids=[BackendOIDSpec("2.2", "string", False)]),
                ],
                detect_spec=SNMPDetectSpec([[]]),
                inventory=False,
            ),
        })

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, file_cache):
        return SNMPFetcher(
            file_cache,
            sections={},
            on_error="raise",
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname="bob",
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits=[],
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
                snmp_backend=SNMPBackend.classic,
            ),
        )

    @pytest.fixture(name="fetcher_inline")
    def fetcher_inline_fixture(self, file_cache):
        return SNMPFetcher(
            file_cache,
            sections={},
            on_error="raise",
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname="bob",
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits=[],
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
                snmp_backend=SNMPBackend.inline
                if not cmk_version.is_raw_edition() else SNMPBackend.classic,
            ),
        )

    @pytest.fixture(name="fetcher_pysnmp")
    def fetcher_pysnmp_fixture(self, file_cache):
        return SNMPFetcher(
            file_cache,
            sections={},
            on_error="raise",
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname="bob",
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits=[],
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
                snmp_backend=SNMPBackend.pysnmp
                if not cmk_version.is_raw_edition() else SNMPBackend.classic,
            ),
        )


class TestSNMPFetcherDeserialization(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return SNMPFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    def test_fetcher_inline_backend_deserialization(self, fetcher_inline):
        other = type(fetcher_inline).from_json(json_identity(fetcher_inline.to_json()))
        assert other.snmp_config.snmp_backend == (
            SNMPBackend.inline if not cmk_version.is_raw_edition() else SNMPBackend.classic)

    def test_fetcher_pysnmp_backend_deserialization(self, fetcher_pysnmp):
        other = type(fetcher_pysnmp).from_json(json_identity(fetcher_pysnmp.to_json()))
        assert other.snmp_config.snmp_backend == (
            SNMPBackend.pysnmp if not cmk_version.is_raw_edition() else SNMPBackend.classic)

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, SNMPFetcher)
        assert other.plugin_store == fetcher.plugin_store
        assert other.checking_sections == fetcher.checking_sections
        assert other.on_error == fetcher.on_error
        assert other.missing_sys_description == fetcher.missing_sys_description
        assert other.snmp_config == fetcher.snmp_config
        assert other.snmp_config.snmp_backend == SNMPBackend.classic

    def test_fetcher_deserialization_snmpv3_credentials(self, fetcher):
        fetcher.snmp_config = fetcher.snmp_config._replace(credentials=("authNoPriv", "md5", "md5",
                                                                        "abc"))
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert other.snmp_config.credentials == fetcher.snmp_config.credentials


class TestSNMPFetcherFetch(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return SNMPFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=False,
        )

    def test_fetch_from_io_non_empty(self, monkeypatch, fetcher):
        table = [['1']]
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda *_, **__: table,
        )
        section_name = SectionName('pim')
        monkeypatch.setattr(
            fetcher, "sections", {
                section_name: SectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                    fetch_interval=None,
                ),
            })

        assert fetcher.fetch(Mode.INVENTORY) == result.OK({})  # 'pim' is not an inventory section
        assert fetcher.fetch(Mode.CHECKING) == result.OK({section_name: [table]})

        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: {SectionName('pim')},
        )
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK({section_name: [table]})

    def test_fetch_from_io_partially_empty(self, monkeypatch, fetcher):
        section_name = SectionName('pum')
        monkeypatch.setattr(
            fetcher, "sections", {
                section_name: SectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                    fetch_interval=None,
                ),
            })
        table = [['1']]
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda tree, **__: table
            if tree.base == fetcher.plugin_store[section_name].trees[0].base else [],
        )
        assert fetcher.fetch(Mode.CHECKING) == result.OK({section_name: [table, []]})

    def test_fetch_from_io_empty(self, monkeypatch, fetcher):
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda *_, **__: [],
        )
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: {SectionName('pam')},
        )
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK({SectionName('pam'): [[]]})

    @pytest.fixture(name="set_sections")
    def _set_sections(self, monkeypatch):
        table = [['1']]
        monkeypatch.setattr(snmp_table, "get_snmp_table", lambda tree, **__: table)
        monkeypatch.setattr(SNMPFetcher, "disabled_sections",
                            property(lambda self: {SectionName("pam")}))
        monkeypatch.setattr(
            SNMPFetcher, "inventory_sections",
            property(lambda self: {SectionName("pim"), SectionName("pam")}))
        return table

    def test_mode_inventory_do_status_data_inventory(self, set_sections, monkeypatch, fetcher):
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", True)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        assert fetcher.fetch(Mode.INVENTORY) == result.OK({SectionName('pim'): [table]})

    def test_mode_inventory_not_do_status_data_inventory(self, set_sections, monkeypatch, fetcher):
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", False)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        assert fetcher.fetch(Mode.INVENTORY) == result.OK({SectionName('pim'): [table]})

    def test_mode_checking_do_status_data_inventory(self, set_sections, monkeypatch, fetcher):
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", True)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        assert fetcher.fetch(Mode.CHECKING) == result.OK({SectionName('pim'): [table]})

    def test_mode_checking_not_do_status_data_inventory(self, set_sections, monkeypatch, fetcher):
        monkeypatch.setattr(fetcher, "do_status_data_inventory", False)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        assert fetcher.fetch(Mode.CHECKING) == result.OK({})


class TestSNMPFetcherFetchCache(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return StubFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=False,
        )

    @pytest.fixture(autouse=True)
    def populate_cache(self, fetcher):
        assert isinstance(fetcher.file_cache, StubFileCache)
        fetcher.file_cache.cache = AgentRawData(b"cached_section")

    @pytest.fixture(autouse=True)
    def patch_io(self, fetcher, monkeypatch):
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")

    def test_fetch_reading_cache_in_discovery_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK(b"cached_section")


class TestSNMPSectionMeta:
    @pytest.mark.parametrize("meta", [
        SectionMeta(checking=False, disabled=False, redetect=False, fetch_interval=None),
        SectionMeta(checking=True, disabled=False, redetect=False, fetch_interval=None),
    ])
    def test_serialize(self, meta):
        assert SectionMeta.deserialize(meta.serialize()) == meta


class TestTCPFetcher:
    @pytest.fixture
    def file_cache(self):
        return StubFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, file_cache):
        return TCPFetcher(
            file_cache,
            family=socket.AF_INET,
            address=("1.2.3.4", 6556),
            timeout=0.1,
            encryption_settings={"encryption": "settings"},
            use_only_cache=False,
        )

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.family == fetcher.family
        assert other.address == fetcher.address
        assert other.timeout == fetcher.timeout
        assert other.encryption_settings == fetcher.encryption_settings
        assert other.use_only_cache == fetcher.use_only_cache

    def test_with_cached_does_not_open(self, file_cache, monkeypatch) -> None:
        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)
        with TCPFetcher(
                file_cache,
                family=socket.AF_INET,
                address=("This is not an IP address. Connecting would fail.", 6556),
                timeout=0.1,
                encryption_settings={"use_regular": "allow"},
                use_only_cache=False,
        ) as fetcher:
            fetched = fetcher.fetch(Mode.CHECKING)

        assert fetched.is_ok()

    def test_open_exception_becomes_fetche_rerror(self, file_cache, monkeypatch) -> None:
        with TCPFetcher(
                file_cache,
                family=socket.AF_INET,
                address=("This is not an IP address. Connecting fails.", 6556),
                timeout=0.1,
                encryption_settings={"use_regular": "allow"},
                use_only_cache=False,
        ) as fetcher:
            fetched = fetcher.fetch(Mode.CHECKING)

        assert isinstance(fetched.error, MKFetcherError)

    def test_decrypt_plaintext_is_noop(self, file_cache):
        settings = {"use_regular": "allow"}
        output = AgentRawData(b"<<<section:sep(0)>>>\nbody\n")
        fetcher = TCPFetcher(
            file_cache,
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            timeout=0.0,
            encryption_settings=settings,
            use_only_cache=False,
        )
        assert fetcher._decrypt(output) == output

    def test_decrypt_plaintext_with_enforce_raises_MKFetcherError(self, file_cache):
        settings = {"use_regular": "enforce"}
        output = AgentRawData(b"<<<section:sep(0)>>>\nbody\n")
        fetcher = TCPFetcher(
            file_cache,
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            timeout=0.0,
            encryption_settings=settings,
            use_only_cache=False,
        )

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)

    def test_decrypt_payload_with_wrong_protocol_raises_MKFetcherError(self, file_cache):
        settings = {"use_regular": "enforce"}
        output = AgentRawData(b"the first two bytes are not a number")
        fetcher = TCPFetcher(
            file_cache,
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            timeout=0.0,
            encryption_settings=settings,
            use_only_cache=False,
        )

        with pytest.raises(MKFetcherError):
            fetcher._decrypt(output)


class TestFetcherCaching:
    @pytest.fixture
    def file_cache(self):
        return DefaultAgentFileCache(
            base_path=Path(os.devnull),
            max_age=MaxAge.none(),
            disabled=True,
            use_outdated=True,
            simulation=False,
        )

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, monkeypatch, file_cache):
        # We use the TCPFetcher to test a general feature of the fetchers.
        return TCPFetcher(
            StubFileCache.from_json(file_cache.to_json()),
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            timeout=0.0,
            encryption_settings={},
            use_only_cache=False,
        )

    @pytest.fixture(autouse=True)
    def populate_cache(self, fetcher):
        assert isinstance(fetcher.file_cache, StubFileCache)
        fetcher.file_cache.cache = AgentRawData(b"cached_section")

    @pytest.fixture(autouse=True)
    def patch_io(self, fetcher, monkeypatch):
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")

    # We are in fact testing a generic feature of the ABCFetcher and use the TCPFetcher for this
    def test_fetch_reading_cache_in_discovery_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK(b"cached_section")
        assert fetcher.file_cache.cache == b"cached_section"

    # We are in fact testing a generic feature of the ABCFetcher and use the TCPFetcher for this
    def test_fetch_reading_cache_in_inventory_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.INVENTORY) == result.OK(b"cached_section")
        assert fetcher.file_cache.cache == b"cached_section"


class TestFetcherType:
    def test_factory(self):
        assert FetcherType.IPMI.make() is IPMIFetcher
        assert FetcherType.PIGGYBACK.make() is PiggybackFetcher
        assert FetcherType.PROGRAM.make() is ProgramFetcher
        assert FetcherType.SNMP.make() is SNMPFetcher
        assert FetcherType.TCP.make() is TCPFetcher
