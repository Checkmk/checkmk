#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import os
import socket
from collections.abc import Sequence, Sized
from pathlib import Path
from typing import Generic, NamedTuple, NoReturn, TypeAlias, TypeVar

import pytest
from pyghmi.exceptions import IpmiException  # type: ignore[import-untyped]
from pytest import MonkeyPatch

from cmk.ccc.exceptions import MKFetcherError, MKTimeout, OnError

import cmk.utils.resulttype as result
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.sectionname import SectionMap, SectionName

from cmk.snmplib import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPTable,
    SNMPVersion,
)

import cmk.fetchers._snmp as snmp
from cmk.fetchers import (
    Fetcher,
    get_raw_data,
    IPMIFetcher,
    Mode,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPScanConfig,
    SNMPSectionMeta,
    TCPEncryptionHandling,
    TCPFetcher,
    TLSConfig,
)
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


def clone_file_cache(file_cache: FileCache) -> FileCache:
    return type(file_cache)(
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
            path_template=os.devnull,
            max_age=MaxAge.zero(),
            simulation=True,
            use_only_cache=True,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    def test_repr(self, file_cache: FileCache) -> None:
        assert isinstance(repr(file_cache), str)


class TestAgentFileCache_and_SNMPFileCache:
    @pytest.fixture
    def path(self, tmp_path: Path) -> Path:
        return tmp_path / "database"

    # AgentFileCache and SNMPFileCache are different types because of the
    # generic param.  The union here isn't helpful. See also `raw_data` below.
    @pytest.fixture(params=[AgentFileCache, SNMPFileCache])
    def file_cache(
        self, path: Path, request: pytest.FixtureRequest
    ) -> AgentFileCache | SNMPFileCache:
        return request.param(
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
        raw_data: AgentRawData | SNMPRawData,
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
        raw_data: object,
    ) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ

        assert not path.exists()

        file_cache.write(raw_data, mode)

        assert not path.exists()
        assert file_cache.read(mode) is None

    def test_write_only(self, file_cache: FileCache, path: Path, raw_data: object) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.WRITE

        assert not path.exists()

        file_cache.write(raw_data, mode)
        assert path.exists()
        assert file_cache.read(mode) is None


_TRawData = TypeVar("_TRawData", bound=Sized)


class StubFileCache(Generic[_TRawData], FileCache[_TRawData]):
    """Holds the data to be cached in-memory for testing"""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.cache: _TRawData | None = None

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> _TRawData:
        assert 0, "unreachable"

    @staticmethod
    def _to_cache_file(raw_data: _TRawData) -> bytes:
        assert 0, "unreachable"

    def write(self, raw_data: _TRawData, mode: Mode) -> None:
        self.cache = raw_data

    def read(self, mode: Mode) -> _TRawData | None:
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


class IPMIFetcherStub(IPMIFetcher):
    def open(self) -> None:
        raise IpmiException()


class TestIPMIFetcher:
    @pytest.fixture
    def fetcher(self) -> IPMIFetcher:
        return IPMIFetcher(address=HostAddress("1.2.3.4"), username="us3r", password="secret")

    def test_repr(self, fetcher: IPMIFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_with_cached_does_not_open(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)

        with IPMIFetcherStub(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING).is_ok()

    def test_command_raises_IpmiException_handling(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

        with IPMIFetcherStub(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
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
    def fetcher(self, tmp_path: Path) -> SNMPFetcher:
        return SNMPFetcher(
            sections={},
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
                oid_cache_dir=tmp_path,
            ),
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            stored_walk_path=tmp_path,
            walk_cache_path=tmp_path,
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                bulkwalk_enabled=True,
                snmp_version=SNMPVersion.V1,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )

    def test_repr(self, fetcher: SNMPFetcher) -> None:
        assert isinstance(repr(fetcher), str)


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

    @staticmethod
    def create_fetcher(
        *,
        path: Path,
        sections: SectionMap[SNMPSectionMeta] | None = None,
        do_status_data_inventory: bool = False,
    ) -> SNMPFetcher:
        return SNMPFetcher(
            sections={} if sections is None else sections,
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
                oid_cache_dir=path,
            ),
            do_status_data_inventory=do_status_data_inventory,
            section_store_path="/tmp/db",
            stored_walk_path=path,
            walk_cache_path=path,
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                bulkwalk_enabled=True,
                snmp_version=SNMPVersion.V1,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )

    def test_fetch_from_io_non_empty(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        table = [["1"]]
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: table)
        section_name = SectionName("pim")
        fetcher = self.create_fetcher(
            path=tmp_path,
            sections={
                section_name: SNMPSectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                ),
            },
        )

        file_cache = SNMPFileCache(
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
            fetcher,
            "_detect",
            lambda *_, **__: {SectionName("pim")},
        )
        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {section_name: [table]}
        )

    def test_fetch_from_io_partially_empty(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        section_name = SectionName("pum")
        fetcher = self.create_fetcher(
            path=tmp_path,
            sections={
                section_name: SNMPSectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                ),
            },
        )
        table = [["1"]]
        monkeypatch.setattr(
            snmp,
            "get_snmp_table",
            lambda tree, **__: (
                table if tree.base == fetcher.plugin_store[section_name].trees[0].base else []
            ),
        )
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(
            {section_name: [table, []]}
        )

    def test_fetch_from_io_empty(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [])
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        fetcher = self.create_fetcher(path=tmp_path)
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: {SectionName("pam")},
        )
        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {SectionName("pam"): [[]]}
        )

    def test_mode_inventory_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda tree, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda self: {SectionName("pim"), SectionName("pam")}),
        )
        fetcher = self.create_fetcher(
            path=tmp_path,
            sections={
                SectionName("pam"): SNMPSectionMeta(
                    checking=False,
                    disabled=True,
                    redetect=False,
                )
            },
            do_status_data_inventory=True,
        )
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [[["1"]]]}
        )

    def test_mode_inventory_not_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda tree, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda self: {SectionName("pim"), SectionName("pam")}),
        )
        fetcher = self.create_fetcher(
            path=tmp_path,
            sections={
                SectionName("pam"): SNMPSectionMeta(
                    checking=False,
                    disabled=True,
                    redetect=False,
                )
            },
        )
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),
        )
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [[["1"]]]}
        )

    def test_mode_checking_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda tree, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda self: {SectionName("pim"), SectionName("pam")}),
        )
        fetcher = self.create_fetcher(
            path=tmp_path,
            sections={
                SectionName("pam"): SNMPSectionMeta(
                    checking=False,
                    disabled=True,
                    redetect=False,
                )
            },
            do_status_data_inventory=True,
        )
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(
            {SectionName("pim"): [[["1"]]]}
        )

    def test_mode_checking_not_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        fetcher = self.create_fetcher(path=tmp_path)
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),
        )
        file_cache = SNMPFileCache(
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK({})


class SNMPFetcherStub(SNMPFetcher):
    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        return {SectionName("section"): [[b"fetched"]]}


class TestSNMPFetcherFetchCache:
    def test_fetch_reading_cache_in_discovery_mode(self, tmp_path: Path) -> None:
        fetcher = SNMPFetcherStub(
            sections={},
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
                oid_cache_dir=tmp_path,
            ),
            do_status_data_inventory=False,
            section_store_path="/tmp/db",
            stored_walk_path=tmp_path,
            walk_cache_path=tmp_path,
            snmp_config=SNMPHostConfig(
                is_ipv6_primary=False,
                hostname=HostName("bob"),
                ipaddress=HostAddress("1.2.3.4"),
                credentials="public",
                port=42,
                bulkwalk_enabled=True,
                snmp_version=SNMPVersion.V1,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                snmp_backend=SNMPBackendEnum.CLASSIC,
            ),
        )
        file_cache = StubFileCache[SNMPRawData](
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
            SNMPSectionMeta(checking=False, disabled=False, redetect=False),
            SNMPSectionMeta(checking=True, disabled=False, redetect=False),
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
    def fetcher(self, tmp_path: Path) -> TCPFetcher:
        return TCPFetcher(
            family=socket.AF_INET,
            address=(HostAddress("1.2.3.4"), 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_handling=TCPEncryptionHandling.ANY_AND_PLAIN,
            pre_shared_secret=None,
            tls_config=TLSConfig(
                cas_dir=tmp_path,
                ca_store=tmp_path,
                site_crt=tmp_path,
            ),
        )

    def test_repr(self, fetcher: TCPFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_with_cached_does_not_open(self, tmp_path: Path) -> None:
        file_cache = StubFileCache[AgentRawData](
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
            tls_config=TLSConfig(
                cas_dir=tmp_path,
                ca_store=tmp_path,
                site_crt=tmp_path,
            ),
        ) as fetcher:
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == result.OK(b"cached_section")

    def test_open_exception_becomes_fetcher_error(self, tmp_path: Path) -> None:
        file_cache = StubFileCache[AgentRawData](
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
            tls_config=TLSConfig(
                cas_dir=tmp_path,
                ca_store=tmp_path,
                site_crt=tmp_path,
            ),
        ) as fetcher:
            raw_data = get_raw_data(file_cache, fetcher, Mode.CHECKING)

        assert isinstance(raw_data.error, MKFetcherError)


class TestFetcherCaching:
    @pytest.fixture
    def fetcher(self) -> Fetcher[AgentRawData]:
        class _Fetcher(Fetcher[AgentRawData]):
            def open(self) -> None:
                pass

            def close(self) -> None:
                pass

            def _fetch_from_io(self, *args: object, **kw: object) -> AgentRawData:
                return AgentRawData(b"fetched_section")

        return _Fetcher()

    def test_fetch_reading_cache_in_discovery_mode(self, fetcher: Fetcher[AgentRawData]) -> None:
        file_cache = StubFileCache[AgentRawData](
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"

    def test_fetch_reading_cache_in_inventory_mode(self, fetcher: Fetcher[AgentRawData]) -> None:
        file_cache = StubFileCache[AgentRawData](
            path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"


class TestFetcherTimeout:
    T: TypeAlias = tuple[None]

    class TimeoutFetcher(Fetcher[T]):
        def open(self) -> None:
            pass

        def close(self) -> None:
            pass

        def _fetch_from_io(self, *args: object, **kw: object) -> NoReturn:
            raise MKTimeout()

    with pytest.raises(MKTimeout):
        get_raw_data(NoCache[T](HostName("")), TimeoutFetcher(), Mode.CHECKING)
