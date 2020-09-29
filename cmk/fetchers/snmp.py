#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
from functools import partial
from typing import Any, cast, Collection, Dict, Final, List, Mapping, Sequence, Tuple

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

__all__ = ["SNMPFetcher", "SNMPFileCache"]


class SNMPFileCache(ABCFileCache[SNMPRawData]):
    @staticmethod
    def _from_cache_file(raw_data: bytes) -> SNMPRawData:
        return {SectionName(k): v for k, v in ast.literal_eval(raw_data.decode("utf-8")).items()}

    @staticmethod
    def _to_cache_file(raw_data: SNMPRawData) -> bytes:
        return (repr({str(k): v for k, v in raw_data.items()}) + "\n").encode("utf-8")


class SNMPFetcher(ABCFetcher[SNMPRawData]):
    def __init__(
        self,
        file_cache: SNMPFileCache,
        *,
        snmp_section_trees: Mapping[SectionName, List[SNMPTree]],
        snmp_section_detects: Sequence[Tuple[SectionName, SNMPDetectSpec]],
        configured_snmp_sections: Collection[SectionName],
        on_error: str,
        missing_sys_description: bool,
        use_snmpwalk_cache: bool,
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.snmp"))
        self.snmp_section_trees: Final = snmp_section_trees
        self.snmp_section_detects: Final = snmp_section_detects
        self.configured_snmp_sections: Final = configured_snmp_sections
        self.on_error: Final = on_error
        self.missing_sys_description: Final = missing_sys_description
        self.use_snmpwalk_cache: Final = use_snmpwalk_cache
        self.snmp_config: Final = snmp_config
        self._backend = factory.backend(self.snmp_config, self._logger)

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> 'SNMPFetcher':
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
            snmp_section_detects=[
                (
                    SectionName(name),
                    # The cast is necessary as mypy does not infer types in a list comprehension.
                    # See https://github.com/python/mypy/issues/5068
                    SNMPDetectSpec([[cast(SNMPDetectAtom, tuple(inner))
                                     for inner in outer]
                                    for outer in specs]),
                )
                for name, specs in serialized["snmp_section_detects"]
            ],
            configured_snmp_sections={
                SectionName(name) for name in serialized["configured_snmp_sections"]
            },
            on_error=serialized["on_error"],
            missing_sys_description=serialized["missing_sys_description"],
            use_snmpwalk_cache=serialized["use_snmpwalk_cache"],
            snmp_config=SNMPHostConfig(**serialized["snmp_config"]),
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "snmp_section_trees": {
                str(n): [tree.to_json() for tree in trees
                        ] for n, trees in self.snmp_section_trees.items()
            },
            "snmp_section_detects": [(str(n), d) for n, d in self.snmp_section_detects],
            "configured_snmp_sections": [str(s) for s in self.configured_snmp_sections],
            "on_error": self.on_error,
            "missing_sys_description": self.missing_sys_description,
            "use_snmpwalk_cache": self.use_snmpwalk_cache,
            "snmp_config": self.snmp_config._asdict(),
        }

    def open(self) -> None:
        verify_ipaddress(self.snmp_config.ipaddress)

    def close(self) -> None:
        pass

    def _detect(self) -> Collection[SectionName]:
        return gather_available_raw_section_names(
            sections=self.snmp_section_detects,
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
        selected_sections = (self._detect()
                             if mode is Mode.DISCOVERY else self.configured_snmp_sections)

        fetched_data: SNMPRawData = {}
        for section_name in selected_sections:
            self._logger.debug("%s: Fetching data", section_name)

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
