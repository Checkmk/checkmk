#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
from functools import partial
from types import TracebackType
from typing import Any, Collection, Dict, List, Mapping, Optional, Sequence, Tuple, Type

from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.snmp_scan import gather_available_raw_section_names
from cmk.snmplib.type_defs import SNMPDetectSpec, SNMPHostConfig, SNMPRawData, SNMPTable, SNMPTree

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
        *,
        file_cache: SNMPFileCache,
        snmp_section_trees: Mapping[SectionName, List[SNMPTree]],
        snmp_section_detects: Sequence[Tuple[SectionName, SNMPDetectSpec]],
        configured_snmp_sections: Collection[SectionName],
        on_error: str,
        missing_sys_description: bool,
        use_snmpwalk_cache: bool,
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.snmp"))
        self._snmp_section_trees = snmp_section_trees
        self._snmp_section_detects = snmp_section_detects
        self._configured_snmp_sections = configured_snmp_sections
        self._on_error = on_error
        self._missing_sys_description = missing_sys_description
        self._use_snmpwalk_cache = use_snmpwalk_cache
        self._snmp_config = snmp_config
        self._backend = factory.backend(self._snmp_config, self._logger)

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> 'SNMPFetcher':
        return cls(
            file_cache=SNMPFileCache.from_json(serialized.pop("file_cache")),
            snmp_section_trees={
                SectionName(name): [SNMPTree.from_json(tree) for tree in trees
                                   ] for name, trees in serialized["snmp_section_trees"].items()
            },
            snmp_section_detects=[
                (SectionName(name), specs) for name, specs in serialized["snmp_section_detects"]
            ],
            configured_snmp_sections={
                SectionName(name) for name in serialized["configured_snmp_sections"]
            },
            on_error=serialized["on_error"],
            missing_sys_description=serialized["missing_sys_description"],
            use_snmpwalk_cache=serialized["use_snmpwalk_cache"],
            snmp_config=SNMPHostConfig(**serialized["snmp_config"]),
        )

    def __enter__(self) -> 'SNMPFetcher':
        verify_ipaddress(self._snmp_config.ipaddress)
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        pass

    def _detect(self) -> Collection[SectionName]:
        return gather_available_raw_section_names(
            sections=self._snmp_section_detects,
            on_error=self._on_error,
            missing_sys_description=self._missing_sys_description,
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
                             if mode is Mode.DISCOVERY else self._configured_snmp_sections)

        fetched_data: SNMPRawData = {}
        for section_name in selected_sections:
            self._logger.debug("%s: Fetching data", section_name)

            oid_info = self._snmp_section_trees[section_name]
            # oid_info is a list: Each element of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            get_snmp = partial(snmp_table.get_snmp_table_cached
                               if self._use_snmpwalk_cache else snmp_table.get_snmp_table,
                               backend=self._backend)
            # branch: List[SNMPTree]
            fetched_section_data: List[SNMPTable] = []
            for entry in oid_info:
                fetched_section_data.append(get_snmp(section_name, entry))
            fetched_data[section_name] = fetched_section_data
        return fetched_data
