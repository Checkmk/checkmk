#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import copy
import dataclasses
import logging
import time
from pathlib import Path
from typing import (
    Any,
    Collection,
    Final,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import HostName, SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.snmp_scan import gather_available_raw_section_names
from cmk.snmplib.type_defs import (
    BackendSNMPTree,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPRawDataSection,
)

from . import factory
from ._base import Fetcher, Parser, Summarizer, verify_ipaddress
from .cache import FileCache, FileCacheFactory, MaxAge, PersistedSections, SectionStore
from .host_sections import HostSections
from .type_defs import Mode, SectionNameCollection

__all__ = [
    "SNMPFetcher",
    "SNMPParser",
    "SNMPPluginStore",
    "SNMPPluginStoreItem",
    "SNMPSummarizer",
]


class SNMPPluginStoreItem(NamedTuple):
    trees: Sequence[BackendSNMPTree]
    detect_spec: SNMPDetectSpec
    inventory: bool

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SNMPPluginStoreItem":
        return cls(
            [BackendSNMPTree.from_json(tree) for tree in serialized["trees"]],
            SNMPDetectSpec.from_json(serialized["detect_spec"]),
            serialized["inventory"],
        )

    def serialize(self) -> Mapping[str, Any]:
        return {
            "trees": [tree.to_json() for tree in self.trees],
            "detect_spec": self.detect_spec.to_json(),
            "inventory": self.inventory,
        }


class SNMPPluginStore(Mapping[SectionName, SNMPPluginStoreItem]):
    def __init__(
        self,
        store: Optional[Mapping[SectionName, SNMPPluginStoreItem]] = None,
    ) -> None:
        self._store: Final[Mapping[SectionName, SNMPPluginStoreItem]] = store if store else {}

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: SectionName) -> SNMPPluginStoreItem:
        return self._store.__getitem__(key)

    def __iter__(self) -> Iterator[SectionName]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SNMPPluginStore":
        return cls(
            {
                SectionName(k): SNMPPluginStoreItem.deserialize(v)
                for k, v in serialized["plugin_store"].items()
            }
        )

    def serialize(self) -> Mapping[str, Any]:
        return {"plugin_store": {str(k): v.serialize() for k, v in self.items()}}


@dataclasses.dataclass(init=False)
class SectionMeta:
    """Metadata for the section names."""

    checking: bool
    disabled: bool
    redetect: bool
    fetch_interval: Optional[int]

    def __init__(
        self,
        *,
        checking: bool,
        disabled: bool,
        redetect: bool,
        fetch_interval: Optional[int],
    ) -> None:
        # There does not seem to be a way to have kwonly dataclasses.
        self.checking = checking
        self.disabled = disabled
        self.redetect = redetect
        self.fetch_interval = fetch_interval

    def serialize(self) -> Mapping[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SectionMeta":
        return cls(**serialized)


class SNMPFileCache(FileCache[SNMPRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> SNMPRawData:
        return {SectionName(k): v for k, v in ast.literal_eval(raw_data.decode("utf-8")).items()}

    @staticmethod
    def _to_cache_file(raw_data: SNMPRawData) -> bytes:
        return (repr({str(k): v for k, v in raw_data.items()}) + "\n").encode("utf-8")

    def make_path(self, mode: Mode) -> Path:
        return self.base_path / mode.name.lower() / self.hostname


class SNMPFileCacheFactory(FileCacheFactory[SNMPRawData]):
    def make(self, *, force_cache_refresh: bool = False) -> SNMPFileCache:
        return SNMPFileCache(
            self.hostname,
            base_path=self.base_path,
            max_age=MaxAge.none() if force_cache_refresh else self.max_age,
            disabled=self.disabled,
            use_outdated=False if force_cache_refresh else self.disabled,
            simulation=self.simulation,
            use_only_cache=self.use_only_cache,
        )


class SNMPFetcher(Fetcher[SNMPRawData]):
    CPU_SECTIONS_WITHOUT_CPU_IN_NAME = {
        SectionName("brocade_sys"),
        SectionName("bvip_util"),
    }
    plugin_store: SNMPPluginStore = SNMPPluginStore()

    def __init__(
        self,
        file_cache: SNMPFileCache,
        *,
        sections: Mapping[SectionName, SectionMeta],
        on_error: OnError,
        missing_sys_description: bool,
        do_status_data_inventory: bool,
        section_store_path: Union[Path, str],
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.helper.snmp"))
        self.sections: Final = sections
        self.on_error: Final = on_error
        self.missing_sys_description: Final = missing_sys_description
        self.do_status_data_inventory: Final = do_status_data_inventory
        self.snmp_config: Final = snmp_config
        self._section_store = SectionStore[SNMPRawDataSection](
            section_store_path,
            logger=self._logger,
        )
        self._backend = factory.backend(self.snmp_config, self._logger)

    @property
    def disabled_sections(self) -> FrozenSet[SectionName]:
        return frozenset(name for name, meta in self.sections.items() if meta.disabled)

    @property
    def checking_sections(self) -> FrozenSet[SectionName]:
        return frozenset(name for name, meta in self.sections.items() if meta.checking)

    @property
    def inventory_sections(self) -> FrozenSet[SectionName]:
        return frozenset(name for name, data in self.plugin_store.items() if data.inventory)

    @property
    def section_store_path(self) -> Path:
        return self._section_store.path

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"{type(self.file_cache).__name__}",
                    f"sections={self.sections!r}",
                    f"on_error={self.on_error!r}",
                    f"missing_sys_description={self.missing_sys_description!r}",
                    f"do_status_data_inventory={self.do_status_data_inventory!r}",
                    f"section_store_path={self.section_store_path!r}",
                    f"snmp_config={self.snmp_config!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "SNMPFetcher":
        # The SNMPv3 configuration is represented by a tuple of different lengths (see
        # SNMPCredentials). Since we just deserialized from JSON, we have to convert the
        # list used by JSON back to a tuple.
        # SNMPv1/v2 communities are represented by a string: Leave it untouched.
        serialized_ = copy.deepcopy(dict(serialized))
        if isinstance(serialized_["snmp_config"]["credentials"], list):
            serialized_["snmp_config"]["credentials"] = tuple(
                serialized_["snmp_config"]["credentials"]
            )

        return cls(
            file_cache=SNMPFileCache.from_json(serialized_.pop("file_cache")),
            sections={
                SectionName(s): SectionMeta.deserialize(m)
                for s, m in serialized_["sections"].items()
            },
            on_error=OnError(serialized_["on_error"]),
            missing_sys_description=serialized_["missing_sys_description"],
            do_status_data_inventory=serialized_["do_status_data_inventory"],
            section_store_path=serialized_["section_store_path"],
            snmp_config=SNMPHostConfig.deserialize(serialized_["snmp_config"]),
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "sections": {str(s): m.serialize() for s, m in self.sections.items()},
            "on_error": self.on_error.value,
            "missing_sys_description": self.missing_sys_description,
            "do_status_data_inventory": self.do_status_data_inventory,
            "section_store_path": str(self._section_store.path),
            "snmp_config": self.snmp_config.serialize(),
        }

    def open(self) -> None:
        verify_ipaddress(self.snmp_config.ipaddress)

    def close(self) -> None:
        pass

    def _detect(self, *, select_from: Collection[SectionName]) -> FrozenSet[SectionName]:
        """Detect the applicable sections for the device in question"""
        return gather_available_raw_section_names(
            sections=[(name, self.plugin_store[name].detect_spec) for name in select_from],
            on_error=self.on_error,
            missing_sys_description=self.missing_sys_description,
            backend=self._backend,
        )

    def _update_snmpwalk_cache(self, mode: Mode) -> bool:
        """Decide whether to load data from the SNMP walk cache"""
        return mode is not Mode.CHECKING

    def _get_selection(self, mode: Mode) -> FrozenSet[SectionName]:
        """Determine the sections fetched unconditionally (without detection)"""
        if mode is Mode.CHECKING:
            return frozenset(
                {name for name in self.checking_sections if not self.sections[name].redetect}
                - self.disabled_sections
            )

        if mode is Mode.FORCE_SECTIONS:
            return self.checking_sections

        return frozenset()

    def _get_detected_sections(self, mode: Mode) -> FrozenSet[SectionName]:
        """Determine the sections fetched after successful detection"""
        if mode is Mode.CHECKING:
            return frozenset(
                {name for name in self.checking_sections if self.sections[name].redetect}
                | (self.inventory_sections if self.do_status_data_inventory else frozenset())
                - self.disabled_sections
            )

        if mode is Mode.INVENTORY:
            return self.inventory_sections - self.disabled_sections

        if mode is Mode.DISCOVERY:
            return frozenset(self.plugin_store) - self.disabled_sections

        return frozenset()

    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        """Select the sections we need to fetch and do that

        Note:
            There still may be some fetching from cache involved
            if the fetch interval was overridden by the user.

        Detection:

         * Mode.DISCOVERY:
           In this straight forward case we must determine all applicable sections for
           the device in question.

         * Mode.INVENTORY
           There is no need to try to detect all sections: For the inventory we have a
           set of sections known to be relevant for inventory plugins, and we can restrict
           detection to those.

         * Mode.CHECKING
           Sections needed for checking are known without detection. If the status data
           inventory is enabled, we detect from the inventory sections; but not those,
           which are fetched for checking anyway.

        """
        now = int(time.time())
        persisted_sections = (
            self._section_store.load()
            if mode is Mode.CHECKING
            else PersistedSections[SNMPRawDataSection]({})
        )
        section_names = self._get_selection(mode)
        section_names |= self._detect(select_from=self._get_detected_sections(mode) - section_names)

        walk_cache = snmp_table.WalkCache(self._backend.hostname)
        if self._update_snmpwalk_cache(mode):
            walk_cache.clear()
            walk_cache_msg = "SNMP walk cache cleared"
        else:
            walk_cache_msg = "SNMP walk cache is enabled: Use any locally cached information"
            walk_cache.load(
                trees=(
                    tree
                    for section_name in section_names
                    for tree in self.plugin_store[section_name].trees
                ),
            )

        fetched_data: MutableMapping[SectionName, Sequence[SNMPRawDataSection]] = {}
        for section_name in self._sort_section_names(section_names):
            try:
                _from, until, _section = persisted_sections[section_name]
                if now > until:
                    raise LookupError(section_name)
            except LookupError:
                self._logger.debug("%s: Fetching data (%s)", section_name, walk_cache_msg)

                fetched_data[section_name] = [
                    snmp_table.get_snmp_table(
                        section_name=section_name,
                        tree=tree,
                        walk_cache=walk_cache,
                        backend=self._backend,
                    )
                    for tree in self.plugin_store[section_name].trees
                ]

        walk_cache.save()

        return fetched_data

    @classmethod
    def _sort_section_names(
        cls,
        section_names: Iterable[SectionName],
    ) -> Iterable[SectionName]:
        # In former Checkmk versions (<=1.4.0) CPU check plugins were
        # checked before other check plugins like interface checks.
        # In Checkmk 1.5 the order was random and
        # interface sections where executed before CPU check plugins.
        # This lead to high CPU utilization sent by device. Thus we have
        # to re-order the section names.
        return sorted(
            section_names,
            key=lambda x: (not ("cpu" in str(x) or x in cls.CPU_SECTIONS_WITHOUT_CPU_IN_NAME), x),
        )


class SNMPParser(Parser[SNMPRawData, SNMPRawDataSection]):
    """A parser for SNMP data.

    Note:
        It is forbidden to add base dependencies to this class.

    """

    def __init__(
        self,
        hostname: HostName,
        section_store: SectionStore[SNMPRawDataSection],
        *,
        check_intervals: Mapping[SectionName, Optional[int]],
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.hostname: Final = hostname
        self.check_intervals: Final = check_intervals
        self.section_store: Final = section_store
        self.keep_outdated: Final = keep_outdated
        self._logger = logger

    def parse(
        self,
        raw_data: SNMPRawData,
        *,
        # The selection argument is ignored: Selection is done
        # in the fetcher for SNMP.
        selection: SectionNameCollection,
    ) -> HostSections[SNMPRawDataSection]:
        sections = dict(raw_data)
        now = int(time.time())

        def lookup_persist(section_name: SectionName) -> Optional[Tuple[int, int]]:
            if (interval := self.check_intervals.get(section_name)) is not None:
                return now, now + interval
            return None

        cache_info: MutableMapping[SectionName, Tuple[int, int]] = {}
        new_sections = self.section_store.update(
            sections,
            cache_info,
            lookup_persist,
            now=now,
            keep_outdated=self.keep_outdated,
        )
        return HostSections[SNMPRawDataSection](new_sections, cache_info=cache_info)


class SNMPSummarizer(Summarizer):
    def summarize_success(self) -> Sequence[ActiveCheckResult]:
        return [ActiveCheckResult(0, "Success")]
