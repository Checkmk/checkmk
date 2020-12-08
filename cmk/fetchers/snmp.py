#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import dataclasses
import logging
import time
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Dict,
    Final,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Union,
)

from cmk.utils.type_defs import SectionName

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
from ._base import Fetcher, FileCache, verify_ipaddress
from .cache import PersistedSections, SectionStore
from .type_defs import Mode

__all__ = ["SNMPFetcher", "SNMPFileCache", "SNMPPluginStore", "SNMPPluginStoreItem"]


class SNMPPluginStoreItem(NamedTuple):
    trees: Sequence[BackendSNMPTree]
    detect_spec: SNMPDetectSpec
    inventory: bool

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "SNMPPluginStoreItem":
        try:
            return cls(
                [BackendSNMPTree.from_json(tree) for tree in serialized["trees"]],
                SNMPDetectSpec.from_json(serialized["detect_spec"]),
                serialized["inventory"],
            )
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
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
    def deserialize(cls, serialized: Dict[str, Any]) -> "SNMPPluginStore":
        try:
            return cls({
                SectionName(k): SNMPPluginStoreItem.deserialize(v)
                for k, v in serialized["plugin_store"].items()
            })
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
        return {"plugin_store": {str(k): v.serialize() for k, v in self.items()}}


@dataclasses.dataclass(init=False)
class SectionMeta:
    """Metadata for the section names."""
    checking: bool
    disabled: bool

    def __init__(self, *, checking: bool, disabled: bool) -> None:
        # There does not seem to be a way to have kwonly dataclasses.
        self.checking = checking
        self.disabled = disabled

    def serialize(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "SectionMeta":
        return cls(**serialized)


class SNMPFileCache(FileCache[SNMPRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> SNMPRawData:
        return {SectionName(k): v for k, v in ast.literal_eval(raw_data.decode("utf-8")).items()}

    @staticmethod
    def _to_cache_file(raw_data: SNMPRawData) -> bytes:
        return (repr({str(k): v for k, v in raw_data.items()}) + "\n").encode("utf-8")


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
        sections: Dict[SectionName, SectionMeta],
        on_error: str,
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
            keep_outdated=False,  # irrelevant to SNMP
            logger=self._logger,
        )
        self._backend = factory.backend(self.snmp_config, self._logger)

    @property
    def disabled_sections(self) -> Set[SectionName]:
        return {name for name, meta in self.sections.items() if meta.disabled}

    @property
    def checking_sections(self) -> Set[SectionName]:
        return {name for name, meta in self.sections.items() if meta.checking}

    @property
    def inventory_sections(self) -> Set[SectionName]:
        return {name for name, data in self.plugin_store.items() if data.inventory}

    @classmethod
    def _from_json(cls, serialized: Dict[str, Any]) -> 'SNMPFetcher':
        # The SNMPv3 configuration is represented by a tuple of different lengths (see
        # SNMPCredentials). Since we just deserialized from JSON, we have to convert the
        # list used by JSON back to a tuple.
        # SNMPv1/v2 communities are represented by a string: Leave it untouched.
        if isinstance(serialized["snmp_config"]["credentials"], list):
            serialized["snmp_config"]["credentials"] = tuple(
                serialized["snmp_config"]["credentials"])

        return cls(
            file_cache=SNMPFileCache.from_json(serialized.pop("file_cache")),
            sections={
                SectionName(s): SectionMeta.deserialize(m)
                for s, m in serialized["sections"].items()
            },
            on_error=serialized["on_error"],
            missing_sys_description=serialized["missing_sys_description"],
            do_status_data_inventory=serialized["do_status_data_inventory"],
            section_store_path=serialized["section_store_path"],
            snmp_config=SNMPHostConfig.deserialize(serialized["snmp_config"]),
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "sections": {str(s): m.serialize() for s, m in self.sections.items()},
            "on_error": self.on_error,
            "missing_sys_description": self.missing_sys_description,
            "do_status_data_inventory": self.do_status_data_inventory,
            "section_store_path": str(self._section_store.path),
            "snmp_config": self.snmp_config.serialize(),
        }

    def open(self) -> None:
        verify_ipaddress(self.snmp_config.ipaddress)

    def close(self) -> None:
        pass

    def _detect(self, *, select_from: Set[SectionName]) -> Set[SectionName]:
        """Detect the applicable sections for the device in question"""
        return gather_available_raw_section_names(
            sections=[(name, self.plugin_store[name].detect_spec) for name in select_from],
            on_error=self.on_error,
            missing_sys_description=self.missing_sys_description,
            backend=self._backend,
        )

    def _use_snmpwalk_cache(self, mode: Mode) -> bool:
        """Decide whether to use the SNMP walk cache

        The SNMP walk cache applies to individual OIDs that are marked as to-be-cached
        in the section definition plugins using `OIDCached`.
        """
        return mode in (Mode.CACHED_DISCOVERY, Mode.CHECKING)

    def _is_cache_read_enabled(self, mode: Mode) -> bool:
        """Decide whether to try to read data from cache

        Fetching for SNMP data is special in that we have to list the sections to fetch
        in advance, unlike for agent data, where we parse the data and see what we get.

        For discovery, we must not fetch the pre-configured sections (which are the ones
        in the cache), but all sections for which the detection spec evaluates to true,
        which can be many more.
        """
        return mode is Mode.CACHED_DISCOVERY

    def _is_cache_write_enabled(self, mode: Mode) -> bool:
        """Decide whether to write data to cache

        If we write the fetching result for SNMP, we also "override" the resulting
        sections for the next call that uses the cache. Since we use the cache for
        CACHED_DISCOVERY only, we must only write it if we're dealing with the right
        sections for discovery.
        """
        return mode in (Mode.CACHED_DISCOVERY, Mode.DISCOVERY)

    def _get_selection(self, mode: Mode) -> Set[SectionName]:
        """Determine the sections fetched unconditionally (without detection)"""
        if mode is Mode.CHECKING:
            return self.checking_sections - self.disabled_sections

        if mode is Mode.FORCE_SECTIONS:
            return self.checking_sections

        return set()

    def _get_detected_sections(self, mode: Mode) -> Set[SectionName]:
        """Determine the sections fetched after successful detection"""
        if mode in (Mode.INVENTORY, Mode.CHECKING) and self.do_status_data_inventory:
            return self.inventory_sections - self.disabled_sections

        if mode in (Mode.DISCOVERY, Mode.CACHED_DISCOVERY):
            return set(self.plugin_store) - self.disabled_sections

        return set()

    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        """Select the sections we need to fetch and do that

        Note:
            There still may be some fetching from cache involved
            if the fetch interval was overridden by the user.

        Detection:

         * Mode.DISCOVERY / CACHED_DISCOVERY:
           In this straight forward case we must determine all applicable sections for
           the device in question.
           Should the fetcher make it to this IO function in *CACHED_*DISCOVERY mode, it
           should behave in the same way as DISCOVERY mode.

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
        persisted_sections = (self._section_store.load() if mode is Mode.CHECKING else
                              PersistedSections[SNMPRawDataSection]({}))
        section_names = self._get_selection(mode)
        section_names |= self._detect(select_from=self._get_detected_sections(mode) - section_names)

        if self._use_snmpwalk_cache(mode):
            walk_cache_msg = "SNMP walk cache is enabled: Use any locally cached information"
            get_snmp = partial(snmp_table.get_snmp_table_cached, backend=self._backend)
        else:
            walk_cache_msg = "SNMP walk cache is disabled"
            get_snmp = partial(snmp_table.get_snmp_table, backend=self._backend)

        fetched_data: MutableMapping[SectionName, SNMPRawDataSection] = {}
        for section_name in self._sort_section_names(section_names):
            try:
                _from, until, _section = persisted_sections[section_name]
                if now > until:
                    raise LookupError(section_name)
            except LookupError:
                self._logger.debug("%s: Fetching data (%s)", section_name, walk_cache_msg)
                section = [
                    get_snmp(section_name, entry) for entry in self.plugin_store[section_name].trees
                ]

                if any(section):
                    fetched_data[section_name] = section

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
            key=lambda x: (not ('cpu' in str(x) or x in cls.CPU_SECTIONS_WITHOUT_CPU_IN_NAME), x),
        )
