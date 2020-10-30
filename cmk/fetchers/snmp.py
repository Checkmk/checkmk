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
    cast,
    Collection,
    Dict,
    Final,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.snmp_scan import gather_available_raw_section_names
from cmk.snmplib.type_defs import (
    SNMPDetectAtom,
    SNMPDetectSpec,
    SNMPHostConfig,
    SNMPRawData,
    SNMPTable,
    SNMPTree,
)

from . import factory
from ._base import ABCFetcher, ABCFileCache, verify_ipaddress
from .type_defs import Mode

__all__ = ["SNMPFetcher", "SNMPFileCache", "SNMPPluginStore", "SNMPPluginStoreItem"]


class SNMPPluginStoreItem(NamedTuple):
    trees: Sequence[SNMPTree]
    detect_spec: SNMPDetectSpec

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "SNMPPluginStoreItem":
        try:
            return cls(
                [SNMPTree.from_json(tree) for tree in serialized["trees"]],
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
    def __init__(self, store: Mapping[SectionName, SNMPPluginStoreItem]) -> None:
        self._store: Final = store

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
        snmp_section_trees: Mapping[SectionName, List[SNMPTree]],
        snmp_section_detects: Mapping[SectionName, SNMPDetectSpec],
        disabled_sections: Set[SectionName],
        configured_snmp_sections: Set[SectionName],
        structured_data_snmp_sections: Set[SectionName],
        on_error: str,
        missing_sys_description: bool,
        use_snmpwalk_cache: bool,
        do_status_data_inventory: bool,
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.snmp"))
        self.snmp_section_trees: Final = snmp_section_trees
        self.snmp_section_detects: Final = snmp_section_detects
        self.disabled_sections: Final = disabled_sections
        self.configured_snmp_sections: Final = configured_snmp_sections
        self.structured_data_snmp_sections: Final = structured_data_snmp_sections
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
            snmp_section_trees={
                SectionName(name): [SNMPTree.from_json(tree) for tree in trees
                                   ] for name, trees in serialized["snmp_section_trees"].items()
            },
            snmp_section_detects={
                SectionName(name): SNMPDetectSpec(
                    # The cast is necessary as mypy does not infer types in a list comprehension.
                    # See https://github.com/python/mypy/issues/5068
                    [[cast(SNMPDetectAtom, tuple(inner)) for inner in outer] for outer in specs])
                for name, specs in serialized["snmp_section_detects"].items()
            },
            disabled_sections={SectionName(name) for name in serialized["disabled_sections"]},
            configured_snmp_sections={
                SectionName(name) for name in serialized["configured_snmp_sections"]
            },
            structured_data_snmp_sections={
                SectionName(name) for name in serialized["structured_data_snmp_sections"]
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
            "snmp_section_trees": {
                str(n): [tree.to_json() for tree in trees
                        ] for n, trees in self.snmp_section_trees.items()
            },
            "snmp_section_detects": {str(n): d for n, d in self.snmp_section_detects.items()},
            "disabled_sections": [str(s) for s in self.disabled_sections],
            "configured_snmp_sections": [str(s) for s in self.configured_snmp_sections],
            "structured_data_snmp_sections": [str(s) for s in self.structured_data_snmp_sections],
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

    def _detect(
        self,
        *,
        restrict_to: Optional[Collection[SectionName]] = None,
    ) -> Set[SectionName]:
        if restrict_to is None:
            # TODO: disabled sections must be considered here, once
            # snmp_section_detects is a global configuration.
            sections: Collection[Tuple[SectionName,
                                       SNMPDetectSpec]] = self.snmp_section_detects.items()
        else:
            sections = [(n, self.snmp_section_detects[n])
                        for n in restrict_to
                        if n in self.snmp_section_detects]

        return gather_available_raw_section_names(
            sections=sections,
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
        return mode not in (Mode.DISCOVERY, Mode.CHECKING)

    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        selected_sections = (
            self._detect() if mode in (Mode.DISCOVERY, Mode.CACHED_DISCOVERY) else
            (self.configured_snmp_sections |
             self._detect(restrict_to=(self.structured_data_snmp_sections if mode is Mode.INVENTORY
                                       or self.do_status_data_inventory else ()))))

        fetched_data: SNMPRawData = {}
        for section_name in self._sort_section_names(selected_sections):
            if self.use_snmpwalk_cache:
                walk_cache_msg = "SNMP walk cache is enabled: Use any locally cached information"
            else:
                walk_cache_msg = "SNMP walk cache is disabled"

            self._logger.debug("%s: Fetching data (%s)", section_name, walk_cache_msg)

            oid_info = self.snmp_section_trees[section_name]
            # oid_info is a list: Each element of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            get_snmp = partial(snmp_table.get_snmp_table_cached
                               if self.use_snmpwalk_cache else snmp_table.get_snmp_table,
                               backend=self._backend)
            # branch: List[SNMPTree]
            fetched_section_data: List[SNMPTable] = []
            for entry in oid_info:
                fetched_section_data.append(get_snmp(section_name, entry))

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
        # In Checkmk versions >= 1.5.0 the order is random and
        # interface check plugins are executed before CPU check plugins.
        # This leads to high CPU utilization sent by device. Thus we have
        # to re-order the check plugin names.
        # There are some nested check plugin names which have to be considered, too.
        #   for f in $(grep "service_description.*CPU [^lL]" -m1 * | cut -d":" -f1); do
        #   if grep -q "snmp_info" $f; then echo $f; fi done
        return sorted(
            section_names,
            key=lambda x: (not ('cpu' in str(x) or x in cls.CPU_SECTIONS_WITHOUT_CPU_IN_NAME), x),
        )
