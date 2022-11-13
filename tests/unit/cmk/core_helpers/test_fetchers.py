#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import socket
from itertools import product as cartesian_product
from pathlib import Path
from typing import Any, List, NamedTuple, Optional, Sequence, Union
from zlib import compress

import pytest
from _pytest.monkeypatch import MonkeyPatch
from pyghmi.exceptions import IpmiException  # type: ignore[import]

import cmk.utils.version as cmk_version
from cmk.utils.encryption import TransportProtocol
from cmk.utils.exceptions import MKFetcherError, OnError
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName, result, SectionName

from cmk.snmplib import snmp_table
from cmk.snmplib.type_defs import (
    BackendOIDSpec,
    BackendSNMPTree,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPTable,
)

from cmk.core_helpers import get_raw_data, snmp
from cmk.core_helpers.agent import AgentFileCache
from cmk.core_helpers.cache import FileCache, FileCacheMode, MaxAge, TRawData
from cmk.core_helpers.ipmi import IPMIFetcher
from cmk.core_helpers.piggyback import PiggybackFetcher
from cmk.core_helpers.program import ProgramFetcher
from cmk.core_helpers.snmp import (
    SectionMeta,
    SNMPFetcher,
    SNMPFileCache,
    SNMPPluginStore,
    SNMPPluginStoreItem,
)
from cmk.core_helpers.tcp import TCPFetcher
from cmk.core_helpers.tcp_agent_ctl import CompressionType, HeaderV1, Version
from cmk.core_helpers.type_defs import Mode


class SensorReading(NamedTuple):
    states: Sequence[str]
    health: int
    name: str
    imprecision: Optional[float]
    units: Union[bytes, str]
    state_ids: Sequence[int]
    type: str
    value: Optional[float]
    unavailable: int


def json_identity(data: Any) -> Any:
    return json.loads(json.dumps(data))


def clone_file_cache(file_cache: FileCache) -> FileCache:
    return type(file_cache)(
        HostName(file_cache.hostname),
        path_template=file_cache.path_template,
        max_age=file_cache.max_age,
        use_outdated=file_cache.use_outdated,
        simulation=file_cache.simulation,
        use_only_cache=file_cache.use_only_cache,
        file_cache_mode=file_cache.file_cache_mode,
    )


class TestFileCache:
    @pytest.fixture(params=[AgentFileCache, SNMPFileCache])
    def file_cache(self, request) -> FileCache:  # type:ignore[no-untyped-def]
        return request.param(
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=False,
            simulation=True,
            use_only_cache=True,
            file_cache_mode=FileCacheMode.DISABLED,
        )

    def test_repr(self, file_cache: FileCache) -> None:
        assert isinstance(repr(file_cache), str)

    def test_deserialization(self, file_cache: FileCache) -> None:
        assert file_cache == type(file_cache).from_json(json_identity(file_cache.to_json()))


# This is horrible to type since the AgentFileCache needs the AgentRawData and the
# SNMPFileCache needs SNMPRawData, this matches here (I think) but the Union types would not
# help anybody... And mypy cannot handle the conditions so we would need to ignore the errors
# anyways...
class TestAgentFileCache_and_SNMPFileCache:
    @pytest.fixture
    def path(self, tmp_path: Path) -> Path:
        return tmp_path / "database"

    @pytest.fixture(params=[AgentFileCache, SNMPFileCache])
    def file_cache(self, path: Path, request):  # type:ignore[no-untyped-def]
        return request.param(
            HostName("hostname"),
            path_template=str(path),
            max_age=MaxAge(checking=0, discovery=999, inventory=0),
            use_outdated=False,
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

    def test_read_write(self, file_cache, path, raw_data) -> None:  # type:ignore[no-untyped-def]
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

    def test_read_only(self, file_cache, path, raw_data) -> None:  # type:ignore[no-untyped-def]
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.READ

        assert not path.exists()

        file_cache.write(raw_data, mode)

        assert not path.exists()
        assert file_cache.read(mode) is None

    def test_write_only(self, file_cache, path, raw_data) -> None:  # type:ignore[no-untyped-def]
        mode = Mode.DISCOVERY
        file_cache.file_cache_mode = FileCacheMode.WRITE

        assert not path.exists()

        file_cache.write(raw_data, mode)
        assert path.exists()
        assert file_cache.read(mode) is None


class StubFileCache(FileCache[TRawData]):
    """Holds the data to be cached in-memory for testing"""

    def __init__(self, *args, **kwargs) -> None:  # type:ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.cache: Optional[TRawData] = None

    @staticmethod
    def _from_cache_file(raw_data: bytes) -> TRawData:
        assert 0, "unreachable"

    @staticmethod
    def _to_cache_file(raw_data: TRawData) -> bytes:
        assert 0, "unreachable"

    def write(self, raw_data: TRawData, mode: Mode) -> None:
        self.cache = raw_data

    def read(self, mode: Mode) -> Optional[TRawData]:
        return self.cache


class TestIPMIFetcher:
    @pytest.fixture
    def fetcher(self) -> IPMIFetcher:
        return IPMIFetcher(address="1.2.3.4", username="us3r", password="secret")

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
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.write(AgentRawData(b"<<<whatever>>>"), Mode.CHECKING)

        with IPMIFetcher(address="127.0.0.1", username="", password="") as fetcher:
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING).is_ok()

    def test_command_raises_IpmiException_handling(self, monkeypatch: MonkeyPatch) -> None:
        def open_(*args: object):  # type:ignore[no-untyped-def]
            raise IpmiException()

        monkeypatch.setattr(IPMIFetcher, "open", open_)

        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )

        with IPMIFetcher(address="127.0.0.1", username="", password="") as fetcher:
            raw_data = get_raw_data(file_cache, fetcher, Mode.CHECKING)

        assert isinstance(raw_data.error, MKFetcherError)

    def test_parse_sensor_reading_standard_case(self, fetcher: IPMIFetcher) -> None:
        reading = SensorReading(  #
            ["lower non-critical threshold"], 1, "Hugo", None, "", [42], "hugo-type", None, 0
        )
        assert fetcher._parse_sensor_reading(0, reading) == [  #
            b"0",
            b"Hugo",
            b"hugo-type",
            b"N/A",
            b"",
            b"lower non-critical threshold",
        ]

    def test_parse_sensor_reading_false_positive(self, fetcher: IPMIFetcher) -> None:
        reading = SensorReading(  #
            ["Present"], 1, "Dingeling", 0.2, b"\xc2\xb0C", [], "FancyDevice", 3.14159265, 1
        )
        assert fetcher._parse_sensor_reading(0, reading) == [  #
            b"0",
            b"Dingeling",
            b"FancyDevice",
            b"3.14",
            b"C",
            b"Present",
        ]


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
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
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
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
                snmp_backend=SNMPBackendEnum.INLINE
                if not cmk_version.is_raw_edition()
                else SNMPBackendEnum.CLASSIC,
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
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
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
                section_name: SectionMeta(
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
            max_age=MaxAge.none(),
            use_outdated=True,
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
                section_name: SectionMeta(
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
            max_age=MaxAge.none(),
            use_outdated=True,
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
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.DISCOVERY) == result.OK(
            {SectionName("pam"): [[]]}
        )

    @pytest.fixture(name="set_sections")
    def _set_sections(self, monkeypatch: MonkeyPatch) -> List[List[str]]:
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
        self, set_sections: List[List[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
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
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [table]}
        )

    def test_mode_inventory_not_do_status_data_inventory(
        self, set_sections: List[List[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
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
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(
            {SectionName("pim"): [table]}
        )

    def test_mode_checking_do_status_data_inventory(
        self, set_sections: List[List[str]], fetcher: SNMPFetcher, monkeypatch: MonkeyPatch
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
            max_age=MaxAge.none(),
            use_outdated=True,
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
            max_age=MaxAge.none(),
            use_outdated=True,
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
                ipaddress="1.2.3.4",
                credentials="public",
                port=42,
                is_bulkwalk_host=False,
                is_snmpv2or3_without_bulkwalk_host=False,
                bulk_walk_size_of=0,
                timing={},
                oid_range_limits={},
                snmpv3_contexts=[],
                character_encoding=None,
                is_usewalk_host=False,
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
        file_cache = StubFileCache[SNMPRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
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
            SectionMeta(checking=False, disabled=False, redetect=False, fetch_interval=None),
            SectionMeta(checking=True, disabled=False, redetect=False, fetch_interval=None),
        ],
    )
    def test_serialize(self, meta: SectionMeta) -> None:
        assert SectionMeta.deserialize(meta.serialize()) == meta


class _MockSock:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self._used = 0

    def recv(self, count: int, *_flags: int) -> bytes:
        use = self.data[self._used : self._used + count]
        self._used += len(use)
        return use

    def __enter__(self, *_args) -> "_MockSock":  # type:ignore[no-untyped-def]
        return self

    def __exit__(self, *_args) -> None:  # type:ignore[no-untyped-def]
        pass


class TestTCPFetcher:
    @pytest.fixture
    def fetcher(self) -> TCPFetcher:
        return TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_settings={"use_regular": "allow"},
        )

    def test_repr(self, fetcher: TCPFetcher) -> None:
        assert isinstance(repr(fetcher), str)

    def test_fetcher_deserialization(self, fetcher: TCPFetcher) -> None:
        other = type(fetcher).from_json(json_identity(fetcher.to_json()))
        assert isinstance(other, type(fetcher))
        assert other.family == fetcher.family
        assert other.address == fetcher.address
        assert other.timeout == fetcher.timeout
        assert other.encryption_settings == fetcher.encryption_settings

    def test_with_cached_does_not_open(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.READ_WRITE,
        )
        file_cache.cache = AgentRawData(b"cached_section")
        with TCPFetcher(
            family=socket.AF_INET,
            address=("This is not an IP address. Connecting would fail.", 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_settings={"use_regular": "allow"},
        ) as fetcher:
            # TODO(ml): monkeypatch the fetcehr and check it was
            # not called to make this test explicit and do what
            # its name advertises.
            assert get_raw_data(file_cache, fetcher, Mode.CHECKING) == b"cached_section"

    def test_fetching_without_cache_raises_in_non_checking_mode(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.READ_WRITE,
        )
        with TCPFetcher(
            family=socket.AF_INET,
            address=("127.0.0.1", 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_settings={"use_regular": "allow"},
        ) as fetcher:
            for mode in Mode:
                if mode is Mode.CHECKING:
                    continue
                raw_data = get_raw_data(file_cache, fetcher, mode)
                assert isinstance(raw_data.error, MKFetcherError)

    def test_open_exception_becomes_fetcher_error(self) -> None:
        file_cache = StubFileCache[AgentRawData](
            HostName("hostname"),
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=True,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        with TCPFetcher(
            family=socket.AF_INET,
            address=("This is not an IP address. Connecting fails.", 6556),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.1,
            encryption_settings={"use_regular": "allow"},
        ) as fetcher:
            raw_data = get_raw_data(file_cache, fetcher, Mode.CHECKING)

        assert isinstance(raw_data.error, MKFetcherError)

    def test_decrypt_plaintext_is_noop(self) -> None:
        settings = {"use_regular": "allow"}
        output = b"<<<section:sep(0)>>>\nbody\n"
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings=settings,
        )
        assert fetcher._decrypt(TransportProtocol(output[:2]), AgentRawData(output[2:])) == output

    def test_validate_protocol_plaintext_with_enforce_raises(self) -> None:
        settings = {"use_regular": "enforce"}
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings=settings,
        )

        with pytest.raises(MKFetcherError):
            fetcher._validate_protocol(TransportProtocol.PLAIN, is_registered=False)

    def test_validate_protocol_missing_use_regular_key_allows_plaintext(self) -> None:
        # The key is missing if a rule "Encryption" is set up without configuring anything.
        # Fixing this is not worth it at the moment, the ruleset needs a makeover anyway.
        TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings={},  # key use_regular is missing here
        )._validate_protocol(TransportProtocol.PLAIN, is_registered=False)

    def test_validate_protocol_no_tls_with_registered_host_raises(self) -> None:
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings={},
        )
        for p in TransportProtocol:
            if p is TransportProtocol.TLS:
                continue
            with pytest.raises(MKFetcherError):
                fetcher._validate_protocol(p, is_registered=True)

    def test_validate_protocol_tls_always_ok(self) -> None:
        for setting, is_registered in cartesian_product(
            ("tls", "enforce", "enable", "disable"),
            (True, False),
        ):
            TCPFetcher(
                family=socket.AF_INET,
                address=("1.2.3.4", 0),
                host_name=HostName("irrelevant_for_this_test"),
                timeout=0.0,
                encryption_settings={"use_regular": setting},
            )._validate_protocol(TransportProtocol.TLS, is_registered=is_registered)

    def test_validate_protocol_encryption_with_disabled_raises(self) -> None:
        settings = {"use_regular": "disable"}
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings=settings,
        )
        with pytest.raises(MKFetcherError):
            fetcher._validate_protocol(TransportProtocol.PBKDF2, is_registered=False)

    def test_validate_protocol_tls_required(self) -> None:
        settings = {"use_regular": "tls"}
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            host_name=HostName("irrelevant_for_this_test"),
            timeout=0.0,
            encryption_settings=settings,
        )
        for p in TransportProtocol:
            if p is TransportProtocol.TLS:
                continue
            with pytest.raises(MKFetcherError, match="TLS"):
                fetcher._validate_protocol(p, is_registered=False)

    def test_get_agent_data_without_tls(
        self, monkeypatch: MonkeyPatch, fetcher: TCPFetcher
    ) -> None:
        mock_sock = _MockSock(b"<<<section:sep(0)>>>\nbody\n")
        monkeypatch.setattr(fetcher, "_opt_socket", mock_sock)

        agent_data, protocol = fetcher._get_agent_data()
        assert agent_data == mock_sock.data[2:]
        assert protocol == TransportProtocol.PLAIN

    def test_get_agent_data_with_tls(self, monkeypatch: MonkeyPatch, fetcher: TCPFetcher) -> None:
        mock_data = b"<<<section:sep(0)>>>\nbody\n"
        mock_sock = _MockSock(
            b"16%b%b%b"
            % (
                bytes(Version.V1),
                bytes(HeaderV1(CompressionType.ZLIB)),
                compress(mock_data),
            )
        )
        monkeypatch.setattr(fetcher, "_opt_socket", mock_sock)
        monkeypatch.setattr(fetcher, "_wrap_tls", lambda _uuid: mock_sock)

        agent_data, protocol = fetcher._get_agent_data()
        assert agent_data == mock_data[2:]
        assert protocol == TransportProtocol.PLAIN

    def test_detect_transport_protocol(self, fetcher: TCPFetcher) -> None:
        assert fetcher._detect_transport_protocol(b"02", "Unused") == TransportProtocol.SHA256

    def test_detect_transport_protocol_error(self, fetcher: TCPFetcher) -> None:
        with pytest.raises(MKFetcherError, match="Unknown transport protocol: b'abc'"):
            fetcher._detect_transport_protocol(b"abc", "unused")

    def test_detect_transport_protocol_empty_error(self, fetcher: TCPFetcher) -> None:
        with pytest.raises(MKFetcherError, match="Passed error message"):
            fetcher._detect_transport_protocol(b"", "Passed error message")


class TestFetcherCaching:
    @pytest.fixture
    def fetcher(self, monkeypatch: MonkeyPatch) -> TCPFetcher:
        # We use the TCPFetcher to test a general feature of the fetchers.
        fetcher = TCPFetcher(
            family=socket.AF_INET,
            address=("1.2.3.4", 0),
            timeout=0.0,
            host_name=HostName("irrelevant_for_this_test"),
            encryption_settings={},
        )
        monkeypatch.setattr(fetcher, "_fetch_from_io", lambda mode: b"fetched_section")
        return fetcher

    # We are in fact testing a generic feature of the Fetcher and use the TCPFetcher for this
    def test_fetch_reading_cache_in_discovery_mode(self, fetcher: TCPFetcher) -> None:
        file_cache = StubFileCache[AgentRawData](
            fetcher.host_name,
            path_template=os.devnull,
            max_age=MaxAge.none(),
            use_outdated=True,
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
            max_age=MaxAge.none(),
            use_outdated=True,
            simulation=False,
            use_only_cache=False,
            file_cache_mode=FileCacheMode.DISABLED,
        )
        file_cache.cache = AgentRawData(b"cached_section")

        assert get_raw_data(file_cache, fetcher, Mode.INVENTORY) == result.OK(b"cached_section")
        assert file_cache.cache == b"cached_section"
