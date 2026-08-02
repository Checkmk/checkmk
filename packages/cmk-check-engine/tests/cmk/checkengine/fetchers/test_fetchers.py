#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


import os
import socket
import time
from collections.abc import Mapping, Sequence, Sized
from pathlib import Path
from typing import Any, cast, NamedTuple, NoReturn, override, Self

import pytest
from pyghmi.exceptions import IpmiException  # type: ignore[import-untyped,unused-ignore]
from pytest import MonkeyPatch

import cmk.ccc.resulttype as result
import cmk.checkengine.fetchers.snmp._fetcher as snmp
from cmk.ccc.exceptions import MKTimeout, OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine import agent_protocol
from cmk.checkengine.fetcher_abc import Fetcher, FetcherError, Mode
from cmk.checkengine.fetcher_utils.secrets import ActivatedSecrets
from cmk.checkengine.fetcher_utils.trigger import PlainFetcherTrigger
from cmk.checkengine.fetchers.ipmi import IPMIFetcher, IPMISensor
from cmk.checkengine.fetchers.piggyback import PiggybackFetcher
from cmk.checkengine.fetchers.program import ProgramFetcher
from cmk.checkengine.fetchers.snmp import SNMPFetcher, SNMPScanConfig, SNMPSectionMeta
from cmk.checkengine.fetchers.tcp import TCPFetcher, TLSConfig
from cmk.checkengine.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheMode,
    MaxAge,
    NoCache,
    SNMPFileCache,
)
from cmk.checkengine.helper_interface import AgentRawData
from cmk.checkengine.snmplib import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPPluginStore,
    SNMPPluginStoreItem,
    SNMPRawData,
    SNMPSectionMarker,
    SNMPSectionName,
    SNMPTable,
    SNMPVersion,
)
from cmk.checkengine.snmplib import SNMPSectionName as SectionName

# TODO(ml): This is way too complicated for a unit test.
PLUGIN_STORE = SNMPPluginStore(
    {
        SNMPSectionName("pim"): SNMPPluginStoreItem(
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
        SNMPSectionName("pam"): SNMPPluginStoreItem(
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
        SNMPSectionName("pum"): SNMPPluginStoreItem(
            trees=[
                BackendSNMPTree(base=".2.2.2", oids=[BackendOIDSpec("2.2", "string", False)]),
                BackendSNMPTree(base=".3.3.3", oids=[BackendOIDSpec("2.2", "string", False)]),
            ],
            detect_spec=SNMPDetectSpec([[]]),
            inventory=False,
        ),
    }
)


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


def clone_file_cache(file_cache: FileCache[Sized]) -> FileCache[Sized]:
    return type(file_cache)(
        base_path=file_cache.base_path,
        relative_path_template=file_cache.relative_path_template,
        max_age=file_cache.max_age,
        simulation=file_cache.simulation,
        use_only_cache=file_cache.use_only_cache,
        file_cache_mode=file_cache.file_cache_mode,
    )


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
        return cast(
            AgentFileCache | SNMPFileCache,
            request.param(
                base_path=Path("/"),
                relative_path_template=str(path),
                max_age=MaxAge(checking=0, discovery=999, inventory=0),
                simulation=False,
                use_only_cache=False,
                file_cache_mode=FileCacheMode.DISABLED,
            ),
        )

    @pytest.fixture
    def raw_data(self, file_cache: AgentFileCache | SNMPFileCache) -> AgentRawData | SNMPRawData:
        if isinstance(file_cache, AgentFileCache):
            return AgentRawData(b"<<<check_mk>>>\nagent raw data")
        assert isinstance(file_cache, SNMPFileCache)
        table: Sequence[SNMPTable] = []
        return {SNMPSectionMarker("X"): table}

    def test_read_write(
        self,
        file_cache: FileCache[Sized],
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
        file_cache: FileCache[Sized],
        path: Path,
        raw_data: Sized,
    ) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ

        assert not path.exists()

        file_cache.write(raw_data, mode)

        assert not path.exists()
        assert file_cache.read(mode) is None

    def test_write_only(self, file_cache: FileCache[Sized], path: Path, raw_data: Sized) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.WRITE

        assert not path.exists()

        file_cache.write(raw_data, mode)
        assert path.exists()
        assert file_cache.read(mode) is None

    def test_delete(self, file_cache: FileCache[Sized], path: Path, raw_data: Sized) -> None:
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ_WRITE

        file_cache.write(raw_data, mode)
        assert path.exists()

        file_cache.delete(mode)
        assert not path.exists()

    def test_delete_missing_is_noop(self, file_cache: FileCache[Sized], path: Path) -> None:
        file_cache.file_cache_mode = FileCacheMode.READ_WRITE

        assert not path.exists()
        file_cache.delete(Mode.DISCOVERY)  # must not raise
        assert not path.exists()

    def test_delete_disabled_keeps_file(
        self, file_cache: FileCache[Sized], path: Path, raw_data: Sized
    ) -> None:
        file_cache.file_cache_mode = FileCacheMode.READ_WRITE
        file_cache.write(raw_data, Mode.DISCOVERY)
        assert path.exists()

        file_cache.file_cache_mode = FileCacheMode.DISABLED
        file_cache.delete(Mode.DISCOVERY)
        assert path.exists()

    def test_delete_non_cacheable_mode_keeps_file(
        self, file_cache: FileCache[Sized], path: Path, raw_data: Sized
    ) -> None:
        file_cache.file_cache_mode = FileCacheMode.READ_WRITE
        file_cache.write(raw_data, Mode.DISCOVERY)
        assert path.exists()

        # FORCE_SECTIONS is not cached, so delete() must be a no-op for it.
        file_cache.delete(Mode.FORCE_SECTIONS)
        assert path.exists()


class StubFileCache[TRawData: Sized](FileCache[TRawData]):
    """Holds the data to be cached in-memory for testing"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cache: TRawData | None = None

    @staticmethod
    @override
    def _from_cache_file(_raw_data: bytes) -> TRawData:
        assert 0, "unreachable"

    @staticmethod
    @override
    def _to_cache_file(_raw_data: TRawData) -> bytes:
        assert 0, "unreachable"

    @override
    def write(self, raw_data: TRawData, _mode: Mode) -> None:
        self.cache = raw_data

    @override
    def read(self, _mode: Mode) -> TRawData | None:
        return self.cache


class CannedFetcherTrigger(PlainFetcherTrigger):
    """A trigger whose fetch result is provided up front, ignoring the fetcher."""

    def __init__(self, omd_root: Path, canned: result.Result[Any, Exception]) -> None:
        super().__init__(omd_root)
        self._canned = canned

    @override
    def _trigger(
        self, _fetcher: Fetcher[Any], _mode: Mode, _secrets: Any
    ) -> result.Result[Any, Exception]:
        return self._canned


class TestFetcherTriggerCacheHandling:
    @pytest.fixture
    def path(self, tmp_path: Path) -> Path:
        return tmp_path / "database"

    @pytest.fixture
    def file_cache(self, path: Path) -> AgentFileCache:
        # MaxAge.zero() makes read() ignore any existing file (as a rescan does),
        # so get_raw_data() always reaches the fetch-and-cache step.
        return AgentFileCache(
            base_path=Path("/"),
            relative_path_template=str(path),
            max_age=MaxAge.zero(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.READ_WRITE,
        )

    def test_successful_fetch_is_cached(self, file_cache: AgentFileCache, path: Path) -> None:
        trigger = CannedFetcherTrigger(Path("/"), result.OK(AgentRawData(b"<<<check_mk>>>\nfresh")))

        out = trigger.get_raw_data(
            file_cache, PiggybackFetcher(), Mode.DISCOVERY, ActivatedSecrets()
        )

        assert out.is_ok()
        assert path.exists()

    def test_failed_fetch_deletes_stale_cache(self, file_cache: AgentFileCache, path: Path) -> None:
        # A previous successful fetch left populated data on disk.
        file_cache.write(AgentRawData(b"<<<check_mk>>>\nstale"), Mode.DISCOVERY)
        assert path.exists()

        trigger = CannedFetcherTrigger(Path("/"), result.Error(FetcherError("Got no data")))

        out = trigger.get_raw_data(
            file_cache, PiggybackFetcher(), Mode.DISCOVERY, ActivatedSecrets()
        )

        assert not out.is_ok()
        # The stale cache must be gone so a later cache-only read reports the failure
        # instead of resurrecting the outdated data.
        assert not path.exists()


class TestIPMISensor:
    def test_parse_sensor_reading_standard_case(self) -> None:
        reading = SensorReading(  #
            ["lower non-critical threshold"], 1, "Hugo", None, "", [42], "hugo-type", None, 0
        )
        assert IPMISensor.from_reading(0, reading) == IPMISensor(  # type: ignore[arg-type,unused-ignore]
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
        assert IPMISensor.from_reading(0, reading) == IPMISensor(  # type: ignore[arg-type,unused-ignore]
            id=b"0",
            name=b"Dingeling",
            type=b"FancyDevice",
            value=b"3.14",
            unit=b"C",
            health=b"Present",
        )


class IPMIFetcherStub(IPMIFetcher):
    @override
    def open(self) -> None:
        raise IpmiException  # type: ignore[no-untyped-call,unused-ignore]


class TestIPMIFetcher:
    @pytest.fixture
    def fetcher(self) -> IPMIFetcher:
        return IPMIFetcher(address=HostAddress("1.2.3.4"), username="us3r", password="secret")

    def test_repr(self, fetcher: IPMIFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_with_cached_does_not_open(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)

        with IPMIFetcherStub(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
            assert (
                PlainFetcherTrigger(Path("/"))
                .get_raw_data(file_cache, fetcher, Mode.CHECKING, ActivatedSecrets())
                .is_ok()
            )

    def test_command_raises_IpmiException_handling(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

        with IPMIFetcherStub(address=HostAddress("127.0.0.1"), username="", password="") as fetcher:
            raw_data = PlainFetcherTrigger(Path("/")).get_raw_data(
                file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
            )

        assert isinstance(raw_data.error, FetcherError)


class TestPiggybackFetcher:
    def test_repr(self) -> None:
        assert isinstance(repr(PiggybackFetcher()), str)


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
                SNMPSectionName("section0"): SNMPPluginStoreItem(
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
                SNMPSectionName("section1"): SNMPPluginStoreItem(
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
            plugin_store=SNMPPluginStore({}),
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
            ),
            do_status_data_inventory=False,
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
                stored_walk_path=Path("/tmp/foo"),
            ),
            base_path=Path("/"),
            relative_stored_walk_path=tmp_path,
            relative_walk_cache_path=tmp_path,
            relative_section_cache_path=Path("tmp/db"),
            caching_config={SNMPSectionName("foobar"): 42},
            force_stored_walks=False,
        )

    def test_repr(self, fetcher: SNMPFetcher) -> None:
        assert isinstance(repr(fetcher), str)


def _create_fetcher(
    *,
    path: Path,
    sections: Mapping[SNMPSectionName, SNMPSectionMeta] | None = None,
    do_status_data_inventory: bool = False,
    caching_config: Mapping[SNMPSectionName, int] | None = None,
    snmp_backend: SNMPBackendEnum = SNMPBackendEnum.CLASSIC,
) -> SNMPFetcher:
    return SNMPFetcher(
        sections={} if sections is None else sections,
        plugin_store=PLUGIN_STORE,
        scan_config=SNMPScanConfig(
            on_error=OnError.RAISE,
            missing_sys_description=False,
        ),
        do_status_data_inventory=do_status_data_inventory,
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
            snmp_backend=snmp_backend,
            stored_walk_path=Path("/tmp/foo"),
        ),
        base_path=Path("/"),
        relative_stored_walk_path=path,
        relative_walk_cache_path=path,
        relative_section_cache_path=path / "section_cache_path",
        caching_config=caching_config or {},
        force_stored_walks=False,
    )


class TestSNMPFetcherFetch:
    def test_open_unavailable_backend(self, tmp_path: Path) -> None:
        # this package does not ship the inline backend
        fetcher = _create_fetcher(path=tmp_path, snmp_backend=SNMPBackendEnum.INLINE)

        with pytest.raises(FetcherError, match="'Inline' SNMP backend is not available"):
            fetcher.open()

    def test_fetch_from_io_non_empty(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        table = [["1"]]
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: table)
        raw_section_name = "pim"
        fetcher = _create_fetcher(
            path=tmp_path,
            sections={
                SNMPSectionName(raw_section_name): SNMPSectionMeta(
                    checking=True,
                    disabled=False,
                    redetect=False,
                ),
            },
        )

        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.INVENTORY, ActivatedSecrets()
        ) == result.OK({})  # 'pim' is not an inventory section
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
        ) == result.OK({SectionName(raw_section_name): [table]})

        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: {SectionName("pim")},
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.DISCOVERY, ActivatedSecrets()
        ) == result.OK({SectionName(raw_section_name): [table]})

    def test_fetch_from_io_partially_empty(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        section_name = SNMPSectionName("pum")
        fetcher = _create_fetcher(
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
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
        ) == result.OK({section_name: [table, []]})

    def test_fetch_from_io_empty(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [])
        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        fetcher = _create_fetcher(path=tmp_path)
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: {SectionName("pam")},
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.DISCOVERY, ActivatedSecrets()
        ) == result.OK({SectionName("pam"): [[]]})

    def test_mode_inventory_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda _self: {SNMPSectionName("pim"), SNMPSectionName("pam")}),
        )
        fetcher = _create_fetcher(
            path=tmp_path,
            sections={
                SNMPSectionName("pam"): SNMPSectionMeta(
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
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),  # noqa: SLF001
        )
        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.INVENTORY, ActivatedSecrets()
        ) == result.OK({SectionName("pim"): [[["1"]]]})

    def test_mode_inventory_not_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda _self: {SectionName("pim"), SectionName("pam")}),
        )
        fetcher = _create_fetcher(
            path=tmp_path,
            sections={
                SNMPSectionName("pam"): SNMPSectionMeta(
                    checking=False,
                    disabled=True,
                    redetect=False,
                )
            },
        )
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.INVENTORY),  # noqa: SLF001
        )
        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.INVENTORY, ActivatedSecrets()
        ) == result.OK({SectionName("pim"): [[["1"]]]})

    def test_mode_checking_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [["1"]])
        monkeypatch.setattr(
            SNMPFetcher,
            "inventory_sections",
            property(lambda _self: {SNMPSectionName("pim"), SNMPSectionName("pam")}),
        )
        fetcher = _create_fetcher(
            path=tmp_path,
            sections={
                SNMPSectionName("pam"): SNMPSectionMeta(
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
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),  # noqa: SLF001
        )
        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
        ) == result.OK({SectionName("pim"): [[["1"]]]})

    def test_mode_checking_not_do_status_data_inventory(
        self, tmp_path: Path, monkeypatch: MonkeyPatch
    ) -> None:
        fetcher = _create_fetcher(path=tmp_path)
        monkeypatch.setattr(
            fetcher,
            "_detect",
            lambda *_, **__: fetcher._get_detected_sections(Mode.CHECKING),  # noqa: SLF001
        )
        file_cache = SNMPFileCache(
            base_path=Path("/"),
            relative_path_template=os.devnull,
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
        ) == result.OK({})


class TestSNMPFetcherConfiguredCaching:
    @pytest.fixture(autouse=True, scope="function")
    def _get_snmp_table(self, monkeypatch: pytest.MonkeyPatch) -> None:
        vals = iter("ab")
        monkeypatch.setattr(snmp, "get_snmp_table", lambda *_, **__: [[next(vals)]])

    @staticmethod
    def _create_fetcher(
        tmp_path: Path, caching_config: Mapping[SNMPSectionName, int]
    ) -> SNMPFetcher:
        return _create_fetcher(
            path=tmp_path,
            sections={
                SNMPSectionName("pim"): SNMPSectionMeta(
                    checking=True, disabled=False, redetect=False
                ),
            },
            caching_config=caching_config,
        )

    @staticmethod
    def _fetch(fetcher: SNMPFetcher, mode: Mode) -> SNMPRawData:
        return (
            PlainFetcherTrigger(Path("/"))
            .get_raw_data(NoCache(), fetcher, mode, ActivatedSecrets())
            .ok
        )

    def test_uncached(self, tmp_path: Path) -> None:
        fetcher = self._create_fetcher(tmp_path, caching_config={})

        assert self._fetch(fetcher, Mode.CHECKING) == {SNMPSectionMarker("pim"): [[["a"]]]}
        assert self._fetch(fetcher, Mode.CHECKING) == {SNMPSectionMarker("pim"): [[["b"]]]}

    def test_cached(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(time, "time", lambda c=iter((0, 100)): next(c))

        fetcher = self._create_fetcher(tmp_path, caching_config={SNMPSectionName("pim"): 123})

        assert self._fetch(fetcher, Mode.CHECKING) == {
            SNMPSectionMarker("pim:cached(0,123)"): [[["a"]]]
        }
        assert self._fetch(fetcher, Mode.CHECKING) == {
            SNMPSectionMarker("pim:cached(0,123)"): [[["a"]]]
        }

    def test_cache_outdated(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(time, "time", lambda c=iter((0, 100)): next(c))

        fetcher = self._create_fetcher(tmp_path, caching_config={SNMPSectionName("pim"): 42})

        assert self._fetch(fetcher, Mode.CHECKING) == {
            SNMPSectionMarker("pim:cached(0,42)"): [[["a"]]]
        }
        assert self._fetch(fetcher, Mode.CHECKING) == {
            SNMPSectionMarker("pim:cached(100,42)"): [[["b"]]]
        }

    @pytest.mark.parametrize("mode", [Mode.DISCOVERY, Mode.INVENTORY, Mode.FORCE_SECTIONS])
    def test_cache_disabled_non_checking_mode(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: Mode
    ) -> None:
        monkeypatch.setattr(time, "time", lambda c=iter((0, 100)): next(c))
        monkeypatch.setattr(
            snmp,
            "gather_available_raw_section_names",
            lambda **__: frozenset({SNMPSectionName("pim")}),
        )

        fetcher = self._create_fetcher(tmp_path, caching_config={SNMPSectionName("pim"): 123})

        assert self._fetch(fetcher, mode) == {SNMPSectionMarker("pim:cached(0,123)"): [[["a"]]]}
        assert self._fetch(fetcher, mode) == {SNMPSectionMarker("pim:cached(100,123)"): [[["b"]]]}


class SNMPFetcherStub(SNMPFetcher):
    @override
    def _fetch_from_io(self, _mode: Mode) -> SNMPRawData:
        return {SNMPSectionMarker("section"): [[b"fetched"]]}


class TestSNMPFetcherFetchCache:
    def test_fetch_reading_cache_in_discovery_mode(self, tmp_path: Path) -> None:
        fetcher = SNMPFetcherStub(
            sections={},
            plugin_store=SNMPPluginStore({}),
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
            ),
            do_status_data_inventory=False,
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
                stored_walk_path=Path("/tmp/foo"),
            ),
            base_path=Path("/"),
            relative_stored_walk_path=tmp_path,
            relative_walk_cache_path=tmp_path,
            relative_section_cache_path=Path("tmp/db"),
            caching_config={},
            force_stored_walks=False,
        )
        file_cache = StubFileCache[SNMPRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = {SNMPSectionMarker("section"): [[b"cached"]]}

        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.DISCOVERY, ActivatedSecrets()
        ) == result.OK({SectionName("section"): [[b"cached"]]})


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
            encryption_handling=agent_protocol.TCPEncryptionHandling.ANY_AND_PLAIN,
            uuid_file=Path("/dev/null"),
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
            base_path=Path("/"),
            relative_path_template="dev/null",
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
            encryption_handling=agent_protocol.TCPEncryptionHandling.ANY_AND_PLAIN,
            uuid_file=Path("/dev/null"),
            pre_shared_secret=None,
            tls_config=TLSConfig(
                cas_dir=tmp_path,
                ca_store=tmp_path,
                site_crt=tmp_path,
            ),
        ) as fetcher:
            assert PlainFetcherTrigger(Path("/")).get_raw_data(
                file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
            ) == result.OK(b"cached_section")

    def test_open_exception_becomes_fetcher_error(self, tmp_path: Path) -> None:
        file_cache = StubFileCache[AgentRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
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
            encryption_handling=agent_protocol.TCPEncryptionHandling.ANY_AND_PLAIN,
            uuid_file=Path("/dev/null"),
            pre_shared_secret=None,
            tls_config=TLSConfig(
                cas_dir=tmp_path,
                ca_store=tmp_path,
                site_crt=tmp_path,
            ),
        ) as fetcher:
            raw_data = PlainFetcherTrigger(Path("/")).get_raw_data(
                file_cache, fetcher, Mode.CHECKING, ActivatedSecrets()
            )

        assert isinstance(raw_data.error, FetcherError)


class TestFetcherCaching:
    @pytest.fixture
    def fetcher(self) -> Fetcher[AgentRawData]:
        class _Fetcher(Fetcher[AgentRawData]):
            @override
            def open(self) -> None:
                pass

            @override
            def close(self) -> None:
                pass

            @override
            def _fetch_from_io(self, *_args: object, **_kw: object) -> AgentRawData:
                return AgentRawData(b"fetched_section")

            @override
            def serialized_params(self) -> Mapping[str, Any]:
                raise NotImplementedError

            @classmethod
            @override
            def from_params(cls, _params: Mapping[str, Any], _ctx: object) -> Self:
                raise NotImplementedError

        return _Fetcher()

    def test_fetch_reading_cache_in_discovery_mode(self, fetcher: Fetcher[AgentRawData]) -> None:
        file_cache = StubFileCache[AgentRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.DISCOVERY, ActivatedSecrets()
        ) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"

    def test_fetch_reading_cache_in_inventory_mode(self, fetcher: Fetcher[AgentRawData]) -> None:
        file_cache = StubFileCache[AgentRawData](
            base_path=Path("/"),
            relative_path_template="dev/null",
            max_age=MaxAge.unlimited(),
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert PlainFetcherTrigger(Path("/")).get_raw_data(
            file_cache, fetcher, Mode.INVENTORY, ActivatedSecrets()
        ) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"


class TestFetcherTimeout:
    type T = tuple[None]

    class TimeoutFetcher(Fetcher[T]):
        @override
        def open(self) -> None:
            pass

        @override
        def close(self) -> None:
            pass

        @override
        def _fetch_from_io(self, *_args: object, **_kw: object) -> NoReturn:
            raise MKTimeout

        @override
        def serialized_params(self) -> Mapping[str, Any]:
            raise NotImplementedError

        @classmethod
        @override
        def from_params(cls, _params: Mapping[str, Any], _ctx: object) -> Self:
            raise NotImplementedError

    with pytest.raises(MKTimeout):
        PlainFetcherTrigger(Path("/")).get_raw_data(
            NoCache[T](HostName("")), TimeoutFetcher(), Mode.CHECKING, ActivatedSecrets()
        )
