#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from types import TracebackType
from typing import Dict, List, Optional, Type, Union

from cmk.utils.check_utils import section_name_of
from cmk.utils.type_defs import ABCSNMPTree, OIDInfo, RawSNMPData, SNMPHostConfig, SNMPTable

import cmk.base.snmp as snmp  # pylint: disable=cmk-module-layer-violation


class SNMPDataFetcher:
    def __init__(
            self,
            oid_infos,  # type: Dict[str, Union[OIDInfo, List[ABCSNMPTree]]]
            use_snmpwalk_cache,  # type: bool
            snmp_config,  # type: SNMPHostConfig
    ):
        # type (...) -> None
        super(SNMPDataFetcher, self).__init__()
        self._oid_infos = oid_infos
        self._use_snmpwalk_cache = use_snmpwalk_cache
        self._snmp_config = snmp_config
        self._logger = logging.getLogger("cmk.fetchers.snmp")

    def __enter__(self):
        # type: () -> SNMPDataFetcher
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        pass

    def data(self):
        # type: () -> RawSNMPData
        info = {}  # type: RawSNMPData
        for check_plugin_name, oid_info in self._oid_infos.items():
            section_name = section_name_of(check_plugin_name)
            # Prevent duplicate data fetching of identical section in case of SNMP sub checks
            if section_name in info:
                self._logger.debug("%s: Skip fetching data (section already fetched)",
                                   check_plugin_name)
                continue

            self._logger.debug("%s: Fetching data", check_plugin_name)

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            get_snmp = snmp.get_snmp_table_cached if self._use_snmpwalk_cache else snmp.get_snmp_table
            if isinstance(oid_info, list):
                # branch: List[ABCSNMPTree]
                check_info = []  # type: List[SNMPTable]
                for entry in oid_info:
                    check_info_part = get_snmp(self._snmp_config, check_plugin_name, entry)
                    check_info.append(check_info_part)
                info[section_name] = check_info
            else:
                # branch: OIDInfo
                info[section_name] = get_snmp(self._snmp_config, check_plugin_name, oid_info)
        return info
