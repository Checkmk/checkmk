#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
import json
import os
import socket
from collections import namedtuple
from pathlib import Path
from typing import Optional

import pytest  # type: ignore[import]

from pyghmi.exceptions import IpmiException  # type: ignore[import]

from cmk.utils.type_defs import AgentRawData, result, SectionName

from cmk.snmplib import snmp_table
from cmk.snmplib.type_defs import (
    BackendSNMPTree,
    OIDSpec,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPTable,
    SNMPBackend,
    SNMPEnumEncoder,
    read_as_enum,
)

from cmk.fetchers import FetcherType, MKFetcherError, snmp
from cmk.fetchers.agent import DefaultAgentFileCache, NoCache
from cmk.fetchers.ipmi import IPMIFetcher
from cmk.fetchers.piggyback import PiggybackFetcher
from cmk.fetchers.program import ProgramFetcher
from cmk.fetchers.snmp import SNMPFetcher, SNMPFileCache, SNMPPluginStoreItem, SNMPPluginStore
from cmk.fetchers.tcp import TCPFetcher
from cmk.fetchers.type_defs import Mode

SensorReading = namedtuple(
    "SensorReading", "states health name imprecision units"
    " state_ids type value unavailable")


def json_identity(data):
    return json.loads(json.dumps(data, cls=SNMPEnumEncoder), object_hook=read_as_enum)


def clone_file_cache(file_cache):
    return type(file_cache)(
        path=file_cache.path,
        max_age=file_cache.max_age,
        disabled=file_cache.disabled,
        use_outdated=file_cache.use_outdated,
        simulation=file_cache.simulation,
    )


class TestFileCache:
    @pytest.fixture
    def path(self, tmp_path):
        return tmp_path / "database"

    @pytest.fixture
    def file_cache(self, path):
        return SNMPFileCache(
            path=path,
            max_age=999,
            disabled=False,
            use_outdated=False,
            simulation=False,
        )

    @pytest.fixture
    def raw_data(self):
        table: SNMPTable = []
        raw_data: SNMPRawData = {SectionName("X"): table}
        return raw_data

    def test_write_and_read(self, file_cache, raw_data):
        assert not file_cache.disabled
        assert not file_cache.path.exists()

        file_cache.write(raw_data)

        assert file_cache.path.exists()
        assert file_cache.read() == raw_data

        # Now with another instance
        clone = clone_file_cache(file_cache)
        assert clone.path.exists()
        assert clone.read() == raw_data

    def test_disabled_write(self, file_cache, raw_data):
        file_cache.disabled = True
        assert file_cache.disabled is True
        assert not file_cache.path.exists()

        file_cache.write(raw_data)

        assert not file_cache.path.exists()
        assert file_cache.read() is None

    def test_disabled_read(self, file_cache, raw_data):
        file_cache.write(raw_data)
        assert file_cache.path.exists()
        assert file_cache.read() == raw_data

        file_cache.disabled = True
        assert file_cache.path.exists()
        assert file_cache.read() is None


class TestIPMIFetcher:
    @pytest.fixture
    def file_cache(self):
        return DefaultAgentFileCache(
            path=Path(os.devnull),
            max_age=0,
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    @pytest.fixture
    def fetcher(self, file_cache):
        return IPMIFetcher(
            file_cache,
            address="1.2.3.4",
            username="us3r",
            password="secret",
        )

    def test_file_cache_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.file_cache == fetcher.file_cache
        assert other.address == fetcher.address
        assert other.username == fetcher.username
        assert other.password == fetcher.password

    def test_command_raises_IpmiException_handling(self, file_cache, monkeypatch):
        def open_(*args):
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        with pytest.raises(MKFetcherError):
            with IPMIFetcher(
                    file_cache,
                    address="127.0.0.1",
                    username="",
                    password="",
            ):
                pass

    def test_parse_sensor_reading_standard_case(self):
        reading = SensorReading(  #
            ['lower non-critical threshold'], 1, "Hugo", None, "", [42], "hugo-type", None, 0)
        assert IPMIFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Hugo", b"hugo-type", b"N/A", b"", b"WARNING"]

    def test_parse_sensor_reading_false_positive(self):
        reading = SensorReading(  #
            ['Present'], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1)
        assert IPMIFetcher._parse_sensor_reading(  #
            0, reading) == [b"0", b"Dingeling", b"FancyDevice", b"3.14", b"C", b"Present"]


class TestPiggybackFetcher:
    @pytest.fixture
    def file_cache(self):
        return NoCache(
            path=Path(os.devnull),
            max_age=0,
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

    def test_file_cache_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))

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
            path=Path(os.devnull),
            max_age=0,
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

    def test_file_cache_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))

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
                    BackendSNMPTree(base=".1.2.3", oids=[OIDSpec("4.5"),
                                                         OIDSpec("9.7")]),
                    BackendSNMPTree(base=".8.9.0", oids=[OIDSpec("1.2"),
                                                         OIDSpec("3.4")]),
                ],
                SNMPDetectSpec([[
                    ("oid0", "regex0", True),
                    ("oid1", "regex1", True),
                    ("oid2", "regex2", False),
                ]]),
            ),
            SectionName("section1"): SNMPPluginStoreItem(
                [BackendSNMPTree(base=".1.2.3", oids=[OIDSpec("4.5"),
                                                      OIDSpec("6.7.8")])],
                SNMPDetectSpec([[
                    ("oid3", "regex3", True),
                    ("oid4", "regex4", False),
                ]]),
            ),
        })

    def test_serialization(self, store):
        assert SNMPPluginStore.deserialize(store.serialize()) == store


class ABCTestSNMPFetcher(ABC):
    @abstractmethod
    @pytest.fixture
    def file_cache(self):
        raise NotImplementedError()

    @pytest.fixture(name="fetcher")
    def fetcher_fixture(self, file_cache):
        return SNMPFetcher(
            file_cache,
            snmp_plugin_store=SNMPPluginStore({
                SectionName("pim"): SNMPPluginStoreItem(
                    trees=[BackendSNMPTree(base=".1.1.1", oids=[OIDSpec("1.2"),
                                                                OIDSpec("3.4")])],
                    detect_spec=SNMPDetectSpec([[("1.2.3.4", "pim device", True)]]),
                ),
                SectionName("pam"): SNMPPluginStoreItem(
                    trees=[
                        BackendSNMPTree(
                            base=".1.2.3",
                            oids=[OIDSpec("4.5"), OIDSpec("6.7"),
                                  OIDSpec("8.9")],
                        ),
                    ],
                    detect_spec=SNMPDetectSpec([[("1.2.3.4", "pam device", True)]]),
                ),
                SectionName("pum"): SNMPPluginStoreItem(
                    trees=[
                        BackendSNMPTree(base=".2.2.2", oids=[OIDSpec("2.2")]),
                        BackendSNMPTree(base=".3.3.3", oids=[OIDSpec("2.2")]),
                    ],
                    detect_spec=SNMPDetectSpec([[]]),
                ),
            }),
            disabled_sections=set(),
            configured_snmp_sections=set(),
            inventory_snmp_sections=set(),
            on_error="raise",
            missing_sys_description=False,
            use_snmpwalk_cache=False,
            do_status_data_inventory=False,
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


class TestSNMPFetcherDeserialization(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return SNMPFileCache(
            path=Path(os.devnull),
            max_age=0,
            disabled=True,
            use_outdated=True,
            simulation=True,
        )

    def test_file_cache_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, SNMPFetcher)
        assert other.snmp_plugin_store == fetcher.snmp_plugin_store
        assert other.configured_snmp_sections == fetcher.configured_snmp_sections
        assert other.on_error == fetcher.on_error
        assert other.missing_sys_description == fetcher.missing_sys_description
        assert other.use_snmpwalk_cache == fetcher.use_snmpwalk_cache
        assert other.snmp_config == fetcher.snmp_config

    def test_fetcher_deserialization_snmpv3_credentials(self, fetcher):
        fetcher.snmp_config = fetcher.snmp_config._replace(credentials=("authNoPriv", "md5", "md5",
                                                                        "abc"))
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert other.snmp_config.credentials == fetcher.snmp_config.credentials


class TestSNMPFetcherFetch(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return SNMPFileCache(
            path=Path(os.devnull),
            max_age=0,
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
        fetcher.configured_snmp_sections = {section_name}
        assert fetcher.fetch(Mode.INVENTORY) == result.OK({})  # 'pim' is not an inventory section
        assert fetcher.fetch(Mode.CHECKING) == result.OK({section_name: [table]})

    @pytest.mark.skip
    def test_fetch_from_io_partially_empty(self, monkeypatch, fetcher):
        section_name = SectionName('pum')
        table = [['1']]
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda _, oid_info, **__: table
            if oid_info.base == fetcher.snmp_plugin_store[section_name].trees[0].base else [],
        )
        fetcher.configured_snmp_sections = {section_name}
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
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK({})


class TestSNMPFetcherFetchCache(ABCTestSNMPFetcher):
    @pytest.fixture
    def file_cache(self):
        return StubFileCache(
            path=Path(os.devnull),
            max_age=0,
            disabled=True,
            use_outdated=True,
            simulation=False,
        )

    @pytest.fixture(autouse=True)
    def populate_cache(self, fetcher):
        assert isinstance(fetcher.file_cache, StubFileCache)
        fetcher.file_cache.cache = b"cached_section"

    @pytest.fixture(autouse=True)
    def patch_io(self, fetcher, monkeypatch):
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")

    def test_fetch_not_reading_cache_in_discovery_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.DISCOVERY) == result.OK(b"fetched_section")

    def test_fetch_reading_cache_in_cached_discovery_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.CACHED_DISCOVERY) == result.OK(b"cached_section")


class TestTCPFetcher:
    @pytest.fixture
    def file_cache(self):
        return DefaultAgentFileCache(
            path=Path(os.devnull),
            max_age=0,
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

    def test_file_cache_deserialization(self, file_cache):
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))

    def test_fetcher_deserialization(self, fetcher):
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.family == fetcher.family
        assert other.address == fetcher.address
        assert other.timeout == fetcher.timeout
        assert other.encryption_settings == fetcher.encryption_settings
        assert other.use_only_cache == fetcher.use_only_cache

    def test_decrypt_plaintext_is_noop(self, file_cache):
        settings = {"use_regular": "allow"}
        output = b"<<<section:sep(0)>>>\nbody\n"
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
        output = b"<<<section:sep(0)>>>\nbody\n"
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
        output = b"the first two bytes are not a number"
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


class StubFileCache(DefaultAgentFileCache):
    """Holds the data to be cached in-memory for testing"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache: Optional[AgentRawData] = None

    def write(self, raw_data: AgentRawData) -> None:
        self.cache = raw_data

    def read(self) -> Optional[AgentRawData]:
        return self.cache


class TestFetcherCaching:
    @pytest.fixture
    def file_cache(self):
        return DefaultAgentFileCache(
            path=Path(os.devnull),
            max_age=0,
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
        fetcher.file_cache.cache = b"cached_section"

    @pytest.fixture(autouse=True)
    def patch_io(self, fetcher, monkeypatch):
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")

    def test_fetch_not_reading_cache_in_checking_mode(self, fetcher):
        assert fetcher.file_cache.cache == b"cached_section"
        assert fetcher.fetch(Mode.CHECKING) == result.OK(b"fetched_section")
        assert fetcher.file_cache.cache == b"fetched_section"

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
