#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from functools import partial
from types import TracebackType
from typing import Any, Dict, List, Optional, Type

from cmk.utils.type_defs import SectionName

import cmk.snmplib.snmp_table as snmp_table
from cmk.snmplib.type_defs import SNMPHostConfig, SNMPRawData, SNMPTable, SNMPTree

from . import factory


class SNMPDataFetcher:
    def __init__(
        self,
        oid_infos: Dict[SectionName, List[SNMPTree]],
        use_snmpwalk_cache: bool,
        snmp_config: SNMPHostConfig,
    ):
        # type (...) -> None
        super(SNMPDataFetcher, self).__init__()
        self._oid_infos = oid_infos
        self._use_snmpwalk_cache = use_snmpwalk_cache
        self._snmp_config = snmp_config
        self._logger = logging.getLogger("cmk.fetchers.snmp")

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> 'SNMPDataFetcher':
        return cls(
            {
                name: [SNMPTree.from_json(tree) for tree in trees
                      ] for name, trees in serialized["oid_infos"].items()
            },
            serialized["use_snmpwalk_cache"],
            SNMPHostConfig(**serialized["snmp_config"]),
        )

    def __enter__(self) -> 'SNMPDataFetcher':
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException],
                 traceback: Optional[TracebackType]) -> None:
        pass

    def data(self) -> SNMPRawData:
        info: SNMPRawData = {}
        for section_name, oid_info in self._oid_infos.items():
            self._logger.debug("%s: Fetching data", section_name)

            # oid_info is now a list: Each element of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            get_snmp = partial(snmp_table.get_snmp_table_cached
                               if self._use_snmpwalk_cache else snmp_table.get_snmp_table,
                               backend=factory.backend(self._snmp_config))
            # branch: List[SNMPTree]
            check_info: List[SNMPTable] = []
            for entry in oid_info:
                check_info_part = get_snmp(section_name, entry)
                check_info.append(check_info_part)
            info[section_name] = check_info
        return info
