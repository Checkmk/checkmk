#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import io
import json
import os
import socket
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Any, Literal, NamedTuple
from unittest import mock
from zlib import compress

import pytest
from pyghmi.exceptions import IpmiException  # type: ignore[import]
from pytest import MonkeyPatch

import cmk.utils.resulttype as result
import cmk.utils.version as cmk_version
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.exceptions import MKFetcherError, OnError
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.sectionname import SectionName

from cmk.snmplib import snmp_table
from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawDataSection,
    SNMPTable,
    TRawData,
)

import cmk.fetchers._snmp as snmp
import cmk.fetchers._tcp as tcp
from cmk.fetchers import (
    get_raw_data,
    IPMIFetcher,
    Mode,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPSectionMeta,
    TCPEncryptionHandling,
    TCPFetcher,
    TransportProtocol,
)
from cmk.fetchers._agentprtcl import CompressionType, HeaderV1, Version
from cmk.fetchers._ipmi import IPMISensor
from cmk.fetchers.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    MaxAge,
    NoCache,
    SNMPFileCache,
)
from cmk.fetchers.snmp import SNMPPluginStore, SNMPPluginStoreItem


class SensorReading(NamedTuple):
    states: Sequence[str]
    health: int
    name: str
    imprecision: float | None
    units: bytes | str
    state_ids: Sequence[int]
    type: str
    value: float | None
    unavailable: int


def json_identity(data: Any) -> Any:
    return json.loads(json.dumps(data))


def clone_file_cache(file_cache: FileCache) -> FileCache:
    return type(file_cache)(
        HostName(file_cache.hostname),
        path_template=file_cache.path_template,
        max_age=file_cache.max_age,
        simulation=file_cache.simulation,
        use_only_cache=file_cache.use_only_cache,
        file_cache_mode=file_cache.file_cache_mode,
    )


class TestFileCache:
    @pytest.fixture(params=[AgentFileCache, SNMPFileCache])
    def file_cache(self, request: pytest.FixtureRequest) -> FileCache:
        return request.param(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.zero(),
            simulation=True,
            use_only_cache=True,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    def test_repr(self, file_cache: FileCache) -> None:
        assert isinstance(repr(file_cache), str)

    def test_deserialization(self, file_cache: FileCache) -> None:
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))


class TestNoCache:
    def test_serialization(self) -> None:
        cache: NoCache = NoCache(HostName("testhost"))
        assert cache.from_json(cache.to_json()) == cache


# This is horrible to type since the AgentFileCache needs the AgentRawData and the
# SNMPFileCache needs SNMPRawData, this matches here (I think) but the Union types would not
# help anybody... And mypy cannot handle the conditions so we would need to ignore the errors
# anyways...
class TestAgentFileCache_and_SNMPFileCache:
    @pytest.fixture
    def path(self, tmp_path: Path) -> Path:
        return tmp_path / "database"

    @pytest.fixture(params=[AgentFileCache, SNMPFileCache])
    def file_cache(
        self, path: Path, request: pytest.FixtureRequest
    ) -> AgentFileCache | SNMPFileCache:
        return request.param(
            HostName("hostname"),
            path_template=str(path),
            max_age=MaxAge(checking=0, discovery=999, inventory=0),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    @pytest.fixture
    def raw_data(self, file_cache):
        if isinstance(file_cache, AgentFileCache):
            return AgentRawData(b"<<<check_mk>>>\nagent raw data")
        assert isinstance(file_cache, SNMPFileCache)
        table: Sequence[SNMPTable] = []
        return {SectionName("X"): table}

    def test_read_write(
        self,
        file_cache: FileCache,
        path: Path,
        raw_data: AgentRawData | dict[SectionName, list[SNMPRawDataSection]],
    ) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ_WRITE

        assert FileCacheMode.READ in file_cache.file_cache_mode
        assert FileCacheMode.WRITE in file_cache.file_cache_mode
        assert not path.exists()

        file_cache.write(raw_data, mode)

        assert path.exists()
        assert file_cache.read(mode) == raw_data

        # Now with another instance
        clone = clone_file_cache(file_cache)
        assert clone.file_cache_mode is FileCacheMode.READ_WRITE
        assert clone.read(mode) == raw_data

    def test_read_only(
        self,
        file_cache: FileCache,
        path: Path,
        raw_data: TRawData,
    ) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ

        assert not path.exists()

        file_cache.write(raw_data, mode)

        assert not path.exists()
        assert file_cache.read(mode) is None

    def test_write_only(self, file_cache: FileCache, path: Path, raw_data: TRawData) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.WRITE

        assert not path.exists()

        file_cache.write(raw_data, mode)
        assert path.exists()
        assert file_cache.read(mode) is None


class StubFileCache(FileCache[TRawData]):
    """Holds the data to be cached in-memory for testing"""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.cache: TRawData | None = None

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> TRawData:
        assert 0, "unreachable"

    @staticmethod
    def _to_cache_file(raw_data: TRawData) -> bytes:
        assert 0, "unreachable"

    def write(self, raw_data: TRawData, mode: Mode) -> None:
        self.cache = raw_data

    def read(self, mode: Mode) -> TRawData | None:
        return self.cache


class TestIPMISensor:
    def test_parse_sensor_reading_standard_case(self) -> None:
        reading = SensorReading(  #
            ["lower non-critical threshold"], 1, "Hugo", None, "", [42], "hugo-type", None, 0
        )
        assert IPMISensor.from_reading(0, reading) == IPMISensor(
            id=b"0",
            name=b"Hugo",
            type=b"hugo-type",
            value=b"N/A",
            unit=b"",
            health=b"lower non-critical threshold",
        )

    def test_parse_sensor_reading_false_positive(self) -> None:
        reading = SensorReading(  #
            ["Present"], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1
        )
        assert IPMISensor.from_reading(0, reading) == IPMISensor(
            id=b"0",
            name=b"Dingeling",
            type=b"FancyDevice",
            value=b"3.14",
            unit=b"C",
            health=b"Present",
        )


class TestIPMIFetcher:
    @pytest.fixture
    def fetcher(self) -> IPMIFetcher:
        return IPMIFetcher(address=HostAddress("1.2.3.4"), username="us3r", password="secret")

    def test_repr(self, fetcher: IPMIFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: IPMIFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.address == fetcher.address
        assert other.username == fetcher.username
        assert other.password == fetcher.password

    def test_with_cached_does_not_open(self, monkeypatch: MonkeyPatch) -> None:
        def open_(*args):
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)

        with IPMIFetcher(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING).is_ok()

    def test_command_raises_IpmiException_handling(self, monkeypatch: MonkeyPatch) -> None:
        def open_(*args: object) -> None:
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

        with IPMIFetcher(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
            raw_data = get_raw_data(file_cache, fetcher, Mode.CHECKING)

        assert isinstance(raw_data.error, MKFetcherError)


class TestPiggybackFetcher:
    @pytest.fixture
    def fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher(
            hostname=HostName("host"),
            address=HostAddress("1.2.3.4"),
            time_settings=[],
        )

    def test_repr(self, fetcher: PiggybackFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: PiggybackFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.hostname == fetcher.hostname
        assert other.address == fetcher.address
        assert other.time_settings == fetcher.time_settings


class TestProgramFetcher:
    @pytest.fixture
    def fetcher(self) -> ProgramFetcher:
        return ProgramFetcher(
            cmdline="/bin/true",
            stdin=None,
            is_cmc=False,
        )

    def test_repr(self, fetcher: ProgramFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: ProgramFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, ProgramFetcher)
        assert other.cmdline == fetcher.cmdline
        assert other.stdin == fetcher.stdin
        assert other.is_cmc == fetcher.is_cmc


class TestSNMPPluginStore:
    @pytest.fixture
    def store(self) -> SNMPPluginStore:
        return SNMPPluginStore(
            {
                SectionName("section0"): SNMPPluginStoreItem(
                    [
                        BackendSNMPTree(
                            base=".1.2.3",
                            oids=[
                                BackendOIDSpec("4.5", "string", False),
                                BackendOIDSpec("9.7", "string", False),
                            ],
                        ),
                        BackendSNMPTree(
                            base=".8.9.0",
                            oids=[
                                BackendOIDSpec("1.2", "string", False),
                                BackendOIDSpec("3.4", "string", False),
                            ],
                        ),
                    ],
                    SNMPDetectSpec(
                        [
                            [
                                ("oid0", "regex0", True),
                                ("oid1", "regex1", True),
                                ("oid2", "regex2", False),
                            ]
                        ]
                    ),
                    False,
                ),
                SectionName("section1"): SNMPPluginStoreItem(
                    [
                        BackendSNMPTree(
                            base=".1.2.3",
                            oids=[
                                BackendOIDSpec("4.5", "string", False),
                                BackendOIDSpec("6.7.8", "string", False),
                            ],
                        )
                    ],
                    SNMPDetectSpec(
                        [
                            [
                                ("oid3", "regex3", True),
                                ("oid4", "regex4", False),
                            ]
                        ]
                    ),
                    False,
                ),
            }
        )

    def test_serialization(self, store: SNMPPluginStore) -> None:
        assert SNMPPluginStore.deserialize(store.serialize()) == store


class TestSNMPFetcherDeserialization:
    @pytest.fixture
    def fetcher(self) -> SNMPFetcher:
        return SNMPFetcher(
            sections={},
            on_error=OnError.RAISE,
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )

    @pytest.fixture
    def fetcher_inline(self) -> SNMPFetcher:
        return SNMPFetcher(
            sections={},
            on_error=OnError.RAISE,
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=(
                    SNMPBackendEnum.INLINE
                    if not cmk_version.is_raw_edition()
                    else SNMPBackendEnum.CLASSIC
                ),
            ),
        )

    def test_fetcher_inline_backend_deserialization(self, fetcher_inline: SNMPFetcher) -> None:
        other = type(fetcher_inline).from_json(json_identity(fetcher_inline.to_json()))
        assert other.snmp_config.snmp_backend == (
            SNMPBackendEnum.INLINE if not cmk_version.is_raw_edition() else SNMPBackendEnum.CLASSIC
        )

    def test_repr(self, fetcher: SNMPFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: SNMPFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, SNMPFetcher)
        assert other.plugin_store == fetcher.plugin_store
        assert other.checking_sections == fetcher.checking_sections
        assert other.on_error == fetcher.on_error
        assert other.missing_sys_description == fetcher.missing_sys_description
        assert other.snmp_config == fetcher.snmp_config
        assert other.snmp_config.snmp_backend == SNMPBackendEnum.CLASSIC

    def test_fetcher_deserialization_snmpv3_credentials(self, fetcher: SNMPFetcher) -> None:
        # snmp_config is Final, but for testing...
        fetcher.snmp_config = fetcher.snmp_config._replace(  # type: ignore[misc]
            credentials=("authNoPriv", "md5", "md5", "abc"),
        )
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert other.snmp_config.credentials == fetcher.snmp_config.credentials


class TestSNMPFetcherFetch:
    @pytest.fixture(autouse=True)
    def snmp_plugin_fixture(self) -> None:
        # TODO(ml): This is way too complicated for a unit test.
        SNMPFetcher.plugin_store = SNMPPluginStore(
            {
                SectionName("pim"): SNMPPluginStoreItem(
                    trees=[
                        BackendSNMPTree(
                            base=".1.1.1",
                            oids=[
                                BackendOIDSpec("1.2", "string", False),
                                BackendOIDSpec("3.4", "string", False),
                            ],
                        )
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
                                BackendOIDSpec("8.9", "string", False),
                            ],
                        ),
                    ],
                    detect_spec=SNMPDetectSpec([[("1.2.3.4", "pam device", True)]]),
                    inventory=False,
                ),
                SectionName("pum"): SNMPPluginStoreItem(
                    trees=[
                        BackendSNMPTree(
                            base=".2.2.2", oids=[BackendOIDSpec("2.2", "string", False)]
                        ),
                        BackendSNMPTree(
                            base=".3.3.3", oids=[BackendOIDSpec("2.2", "string", False)]
                        ),
                    ],
                    detect_spec=SNMPDetectSpec([[]]),
                    inventory=False,
                ),
            }
        )

    @pytest.fixture
    def fetcher(self) -> SNMPFetcher:
        return SNMPFetcher(
            sections={},
            on_error=OnError.RAISE,
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )

    def test_fetch_from_io_non_empty(self, fetcher: SNMPFetcher, monkeypatch: MonkeyPatch) -> None:
        table = [["1"]]
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda *_, **__: table,
        )
        section_name = SectionName("pim")
        monkeypatch.setattr(
            fetcher,
            "sections",
            {
                section_name: SNMPSectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                    fetch_interval=None,
                ),
            },
        )

        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {}
        )  # 'pim' is not an inventory section
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(
            {section_name: [table]}
        )

        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: {SectionName("pim")},
        )
        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {section_name: [table]}
        )

    def test_fetch_from_io_partially_empty(
        self, fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
    ) -> None:
        section_name = SectionName("pum")
        monkeypatch.setattr(
            fetcher,
            "sections",
            {
                section_name: SNMPSectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                    fetch_interval=None,
                ),
            },
        )
        table = [["1"]]
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda tree, **__: table
            if tree.base == fetcher.plugin_store[section_name].trees[0].base
            else [],
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(
            {section_name: [table, []]}
        )

    def test_fetch_from_io_empty(self, monkeypatch: MonkeyPatch, fetcher: SNMPFetcher) -> None:
        monkeypatch.setattr(
            snmp_table,
            "get_snmp_table",
            lambda *_, **__: [],
        )
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: {SectionName("pam")},
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {SectionName("pam"): [[]]}
        )

    @pytest.fixture(name="set_sections")
    def _set_sections(self, monkeypatch: MonkeyPatch) -> list[list[str]]:
        table = [["1"]]
        monkeypatch.setattr(snmp_table, "get_snmp_table", lambda tree, **__: table)
        monkeypatch.setattr(
            SNMPFetcher, "disabled_sections", property(lambda self: {SectionName("pam")})
        )
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda self: {SectionName("pim"), SectionName("pam")}),
        )
        return table

    def test_mode_inventory_do_status_data_inventory(
        self, set_sections: list[list[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
    ) -> None:
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", True)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [table]}
        )

    def test_mode_inventory_not_do_status_data_inventory(
        self, set_sections: list[list[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
    ) -> None:
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", False)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [table]}
        )

    def test_mode_checking_do_status_data_inventory(
        self, set_sections: list[list[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
    ) -> None:
        table = set_sections
        monkeypatch.setattr(fetcher, "do_status_data_inventory", True)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(
            {SectionName("pim"): [table]}
        )

    def test_mode_checking_not_do_status_data_inventory(
        self, fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fetcher, "do_status_data_inventory", False)
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        file_cache = SNMPFileCache(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK({})


class TestSNMPFetcherFetchCache:
    @pytest.fixture
    def fetcher(self, monkeypatch: MonkeyPatch) -> SNMPFetcher:
        fetcher = SNMPFetcher(
            sections={},
            on_error=OnError.RAISE,
            missing_sys_description=False,
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )
        monkeypatch.setattr(
            fetcher,
            "_fetch_from_io",
            lambda mode: {SectionName("section"): [[b"fetched"]]},
        )
        return fetcher

    def test_fetch_reading_cache_in_discovery_mode(self, fetcher: SNMPFetcher) -> None:
        file_cache = StubFileCache[dict[SectionName, list[SNMPRawDataSection]]](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = {SectionName("section"): [[b"cached"]]}

        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {SectionName("section"): [[b"cached"]]}
        )


class TestSNMPSectionMeta:
    @pytest.mark.parametrize(
        "meta",
        [
            SNMPSectionMeta(checking=False, disabled=False, redetect=False, fetch_interval=None),
            SNMPSectionMeta(checking=True, disabled=False, redetect=False, fetch_interval=None),
        ],
    )
    def test_serialize(self, meta: SNMPSectionMeta) -> None:
        assert SNMPSectionMeta.deserialize(meta.serialize()) == meta


class _MockSock:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self._used = 0

    def recv(self, count: int, *_flags: int) -> bytes:
        use = self.data[self._used : self._used + count]
        self._used += len(use)
        return use

    def __enter__(self, *_args: object) -> _MockSock:
        return self

    def __exit__(self, *_args: object) -> None:
        pass


class TestTCPFetcher:
    @pytest.fixture
    def fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("1.2.3.4"), 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
        )

    def test_repr(self, fetcher: TCPFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: TCPFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.family == fetcher.family
        assert other.address == fetcher.address
        assert other.timeout == fetcher.timeout
        assert other.encryption_handling == fetcher.encryption_handling
        assert other.pre_shared_secret == fetcher.pre_shared_secret

    def test_with_cached_does_not_open(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.READ_WRITE,
        )
        file_cache.cache = AgentRawData(b"cached_section")
        with TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("999.999.999.999"), 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
        ) as fetcher:
            # TODO(ml): monkeypatch the fetcehr and check it was
            # not called to make this test explicit and do what
            # its name advertises.
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == b"cached_section"

    def test_open_exception_becomes_fetcher_error(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=True,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        with TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("999.999.999.999"), 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
        ) as fetcher:
            raw_data = get_raw_data(file_cache, fetcher, Mode.CHECKING)

        assert isinstance(raw_data.error, MKFetcherError)

    def test_get_agent_data_without_tls(
        self, monkeypatch: MonkeyPatch, fetcher: TCPFetcher
    ) -> None:
        mock_sock = _MockSock(b"<<<section:sep(0)>>>\nbody\n")
        monkeypatch.setattr(fetcher, "_opt_socket", mock_sock)

        assert fetcher._get_agent_data(None) == mock_sock.data

    def test_get_agent_data_with_tls(self, monkeypatch: MonkeyPatch, fetcher: TCPFetcher) -> None:
        mock_data = b"<<<section:sep(0)>>>\nbody\n"
        mock_sock = _MockSock(
            b"%b%b%b%b"
            % (
                TransportProtocol.TLS.value,
                bytes(Version.V1),
                bytes(HeaderV1(CompressionType.ZLIB)),
                compress(mock_data),
            )
        )
        monkeypatch.setattr(fetcher, "_opt_socket", mock_sock)
        monkeypatch.setattr(tcp, "wrap_tls", lambda *args: mock_sock)

        assert fetcher._get_agent_data("server") == mock_data


class TestFetcherCaching:
    @pytest.fixture
    def fetcher(self, monkeypatch: MonkeyPatch) -> TCPFetcher:
        # We use the TCPFetcher to test a general feature of the fetchers.
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("1.2.3.4"), 0),
            timeout=0.0,
            host_name=HostName("irrelevant_for_this_test"),
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
        )
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")
        return fetcher

    # We are in fact testing a generic feature of the Fetcher and use the TCPFetcher for this
    def test_fetch_reading_cache_in_discovery_mode(self, fetcher: TCPFetcher) -> None:
        file_cache = StubFileCache[AgentRawData](
            fetcher.host_name,
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"

    # We are in fact testing a generic feature of the Fetcher and use the TCPFetcher for this
    def test_fetch_reading_cache_in_inventory_mode(self, fetcher: TCPFetcher) -> None:
        file_cache = StubFileCache[AgentRawData](
            fetcher.host_name,
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"


@pytest.mark.parametrize(
    ["wait_connect", "wait_data", "timeout_connect", "exc_type"],
    [
        # No delay on connection and recv. No exception
        (0, 0, 10, None),
        # 50sec delay on connection. This times out.
        (50, 0, 10, socket.timeout),
        # Explicitly set timeout on connection
        # TCP_TIMEOUT related tests
        (0, 120, 10, None),  # will definitely run for 2 minutes without any data coming
        # ... but will time out immediately after 151 seconds due to KEEPALIVE settings
        (0, (120 + 3 * 10) + 1, 10, MKFetcherError),
    ],
)
def test_tcp_fetcher_dead_connection_timeout(
    wait_connect: float,
    wait_data: float,
    timeout_connect: float,
    exc_type: type[Exception] | None,
) -> None:
    # This tests if the TCPFetcher properly times out in the event of an unresponsive agent (due to
    # whatever reasons). We can't wait forever, else the process runs into the risk of never dying,
    # sticking around forever, hogging important resources and blocking user interaction.
    with FakeSocket(wait_connect=wait_connect, wait_data=wait_data, data=b"<<"):
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("127.0.0.1"), 12345),  # Will be ignored by the FakeSocket
            timeout=timeout_connect,
            # Boilerplate stuff to make the code not crash.
            host_name=HostName("timeout_tcp_test"),
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
        )
        if exc_type is not None:
            with pytest.raises(exc_type):
                fetcher.open()
                fetcher._get_agent_data(None)
        else:
            fetcher.open()
            fetcher._get_agent_data(None)


class FakeSocket:
    """A socket look-alike to test timeout behaviours

    Args:

        wait_connect:
            How long the "simulated" delay will be, until a connection is established. If longer
            than the timeout set by `settimeout`, the exception `socket.timeout` will be raised.

        wait_data:
            How long the "simulated" delay of a `recv` call will be. If the delay is longer than
            the one registered by `settimeout`, the exception `socket.timeout` will be raised.

        data:
            The data in bytes which will be received from a `recv` call on the socket.

    """

    def __init__(self, wait_connect: float = 0, wait_data: float = 0, data: bytes = b"") -> None:
        self._wait_connect = wait_connect
        self._wait_data = wait_data
        self._timeout: int | None = None
        self._buffer = io.BytesIO(data)

    def __enter__(self) -> None:
        # Patch `socket.socket` to return this object
        self._mock = mock.patch("socket.socket", new=self)
        self._mock.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        # Clean up the mock again
        self._mock.__exit__(exc_type, exc_val, exc_tb)
        return False

    def __call__(self, family: int, flags: int) -> FakeSocket:
        """Fake a `socket.socket` call"""
        self._family = family
        self._flags = flags
        self._sock_opts: dict[int, int] = {}
        return self

    def settimeout(self, timeout: int) -> None:
        self._timeout = timeout

    def connect(self, address: tuple[str, int]) -> None:
        """Simulate a connection to a socket

        Raises:
            socket.timeout - when `wait_connection` is larger than the timeout set by `settimeout`
        """
        self._check_timeout(self._wait_connect)

    def recv(self, byte_count: int, flags: Any) -> bytes:
        """Simulate a recv call on a socket

        Raises:
            socket.timeout - when `wait_data` is larger than the timeout set by `settimeout`
        """
        self._check_timeout(self._wait_data)
        return self._buffer.read(byte_count)

    def setsockopt(self, level: int, optname: int, value: int) -> None:
        self._sock_opts[optname] = value

    def _check_timeout(self, delay_time: float) -> None:
        if self._timeout is not None and delay_time > self._timeout:
            raise socket.timeout

        if self._sock_opts.get(socket.SO_KEEPALIVE):
            # defaults according to tcp(7)
            keep_idle = self._sock_opts.get(socket.TCP_KEEPIDLE, 7200)
            keep_interval = self._sock_opts.get(socket.TCP_KEEPINTVL, 75)
            keep_count = self._sock_opts.get(socket.TCP_KEEPCNT, 9)

            is_timed_out = delay_time > (keep_idle + keep_count * keep_interval)
            if is_timed_out:
                raise socket.timeout

    def close(self) -> None:
        self._buffer.close()
