#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
from functools import partial
from typing import (
    Any,
    Dict,
    Final,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
)

from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.snmp_scan import gather_available_raw_section_names
from cmk.snmplib.type_defs import (
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    BackendSNMPTree,
)

from . import factory
from ._base import ABCFetcher, ABCFileCache, verify_ipaddress
from .type_defs import Mode

__all__ = ["SNMPFetcher", "SNMPFileCache", "SNMPPluginStore", "SNMPPluginStoreItem"]


class SNMPPluginStoreItem(NamedTuple):
    trees: Sequence[BackendSNMPTree]
    detect_spec: SNMPDetectSpec

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "SNMPPluginStoreItem":
        try:
            return cls(
                [BackendSNMPTree.from_json(tree) for tree in serialized["trees"]],
                SNMPDetectSpec.from_json(serialized["detect_spec"]),
            )
        except (LookupError, TypeError, ValueError) as exc:
            raise ValueError(serialized) from exc

    def serialize(self) -> Dict[str, Any]:
        return {
            "trees": [tree.to_json() for tree in self.trees],
            "detect_spec": self.detect_spec.to_json(),
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


class SNMPFileCache(ABCFileCache[SNMPRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> SNMPRawData:
        return {SectionName(k): v for k, v in ast.literal_eval(raw_data.decode("utf-8")).items()}

    @staticmethod
    def _to_cache_file(raw_data: SNMPRawData) -> bytes:
        return (repr({str(k): v for k, v in raw_data.items()}) + "\n").encode("utf-8")


class SNMPFetcher(ABCFetcher[SNMPRawData]):
    CPU_SECTIONS_WITHOUT_CPU_IN_NAME = {
        SectionName("brocade_sys"),
        SectionName("bvip_util"),
    }

    def __init__(
        self,
        file_cache: SNMPFileCache,
        *,
        snmp_plugin_store: SNMPPluginStore,
        disabled_sections: Set[SectionName],
        configured_snmp_sections: Set[SectionName],
        inventory_snmp_sections: Set[SectionName],
        on_error: str,
        missing_sys_description: bool,
        use_snmpwalk_cache: bool,
        do_status_data_inventory: bool,
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.helper.snmp"))
        self.snmp_plugin_store: Final = snmp_plugin_store
        self.disabled_sections: Final = disabled_sections
        self.configured_snmp_sections: Final = configured_snmp_sections
        self.inventory_snmp_sections: Final = inventory_snmp_sections
        self.on_error: Final = on_error
        self.missing_sys_description: Final = missing_sys_description
        self.use_snmpwalk_cache: Final = use_snmpwalk_cache
        self.do_status_data_inventory: Final = do_status_data_inventory
        self.snmp_config: Final = snmp_config
        self._backend = factory.backend(self.snmp_config, self._logger)

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
            snmp_plugin_store=SNMPPluginStore.deserialize(serialized["snmp_plugin_store"]),
            disabled_sections={SectionName(name) for name in serialized["disabled_sections"]},
            configured_snmp_sections={
                SectionName(name) for name in serialized["configured_snmp_sections"]
            },
            inventory_snmp_sections={
                SectionName(name) for name in serialized["inventory_snmp_sections"]
            },
            on_error=serialized["on_error"],
            missing_sys_description=serialized["missing_sys_description"],
            use_snmpwalk_cache=serialized["use_snmpwalk_cache"],
            do_status_data_inventory=serialized["do_status_data_inventory"],
            snmp_config=SNMPHostConfig(**serialized["snmp_config"]),
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "snmp_plugin_store": self.snmp_plugin_store.serialize(),
            "disabled_sections": [str(s) for s in self.disabled_sections],
            "configured_snmp_sections": [str(s) for s in self.configured_snmp_sections],
            "inventory_snmp_sections": [str(s) for s in self.inventory_snmp_sections],
            "on_error": self.on_error,
            "missing_sys_description": self.missing_sys_description,
            "use_snmpwalk_cache": self.use_snmpwalk_cache,
            "do_status_data_inventory": self.do_status_data_inventory,
            "snmp_config": self.snmp_config._asdict(),
        }

    def open(self) -> None:
        verify_ipaddress(self.snmp_config.ipaddress)

    def close(self) -> None:
        pass

    def _detect(self, *, select_from: Set[SectionName]) -> Set[SectionName]:
        """Detect the applicable sections for the device in question"""
        sections = select_from - self.disabled_sections
        return gather_available_raw_section_names(
            sections=[(name, self.snmp_plugin_store[name].detect_spec) for name in sections],
            on_error=self.on_error,
            missing_sys_description=self.missing_sys_description,
            backend=self._backend,
        )

    def _is_cache_enabled(self, mode: Mode) -> bool:
        """Decide whether to try to read data from cache

        Fetching for SNMP data is special in that we have to list the sections to fetch
        in advance, unlike for agent data, where we parse the data and see what we get.

        For discovery, we must not fetch the pre-configured sections (which are the ones
        in the cache), but all sections for which the detection spec evaluates to true,
        which can be many more.
        """
        return mode is Mode.CACHED_DISCOVERY

    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        """Select the sections we need to fetch and do that

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
        if mode == Mode.CHECKING:
            selected_sections = self.configured_snmp_sections
            if self.do_status_data_inventory:
                selected_sections |= self._detect(select_from=set(self.inventory_snmp_sections) -
                                                  selected_sections,)
        elif mode == Mode.INVENTORY:
            selected_sections = self._detect(select_from=set(self.inventory_snmp_sections))
        else:
            selected_sections = self._detect(select_from=set(self.snmp_plugin_store))

        if self.use_snmpwalk_cache:
            walk_cache_msg = "SNMP walk cache is enabled: Use any locally cached information"
            get_snmp = partial(snmp_table.get_snmp_table_cached, backend=self._backend)
        else:
            walk_cache_msg = "SNMP walk cache is disabled"
            get_snmp = partial(snmp_table.get_snmp_table, backend=self._backend)

        fetched_data: SNMPRawData = {}
        for section_name in self._sort_section_names(selected_sections):
            self._logger.debug("%s: Fetching data (%s)", section_name, walk_cache_msg)

            fetched_section_data = [
                get_snmp(section_name, entry)
                for entry in self.snmp_plugin_store[section_name].trees
            ]

            if any(fetched_section_data):
                fetched_data[section_name] = fetched_section_data

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
