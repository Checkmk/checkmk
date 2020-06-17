#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import time
from typing import cast, Dict, List, Optional, Set

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, HostAddress, HostName, SectionName, SourceType

from cmk.snmplib.type_defs import (
    SNMPCredentials,
    SNMPHostConfig,
    SNMPPersistedSections,
    SNMPRawData,
    SNMPSectionContent,
    SNMPSections,
    SNMPTree,
)

from cmk.fetchers import factory, SNMPDataFetcher

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
from cmk.base.snmp_scan import PluginNameFilterFunction
from cmk.base.api import PluginName
from cmk.base.api.agent_based.register.check_plugins_legacy import maincheckify
from cmk.base.api.agent_based.section_types import SNMPSectionPlugin
from cmk.base.check_utils import PiggybackRawData, SectionCacheInfo
from cmk.base.exceptions import MKAgentError

from .abstract import DataSource, verify_ipaddress
from .host_sections import AbstractHostSections

#.
#   .--SNMP----------------------------------------------------------------.
#   |                      ____  _   _ __  __ ____                         |
#   |                     / ___|| \ | |  \/  |  _ \                        |
#   |                     \___ \|  \| | |\/| | |_) |                       |
#   |                      ___) | |\  | |  | |  __/                        |
#   |                     |____/|_| \_|_|  |_|_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Realize the data source for dealing with SNMP data                   |
#   '----------------------------------------------------------------------'


class SNMPHostSections(AbstractHostSections[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                            SNMPSectionContent]):
    def __init__(self,
                 sections=None,
                 cache_info=None,
                 piggybacked_raw_data=None,
                 persisted_sections=None):
        # type: (Optional[SNMPSections], Optional[SectionCacheInfo], Optional[PiggybackRawData], Optional[SNMPPersistedSections]) -> None
        super(SNMPHostSections, self).__init__(
            sections=sections if sections is not None else {},
            cache_info=cache_info if cache_info is not None else {},
            piggybacked_raw_data=piggybacked_raw_data if piggybacked_raw_data is not None else {},
            persisted_sections=persisted_sections if persisted_sections is not None else {},
        )

    def _extend_section(self, section_name, section_content):
        # type: (SectionName, SNMPSectionContent) -> None
        raise NotImplementedError()


class CachedSNMPDetector:
    """Object to run/cache SNMP detection"""
    def __init__(self):
        super(CachedSNMPDetector, self).__init__()
        # TODO (mo): With the new API we may be able to set this here.
        #            For now, it is set later :-(
        self._filter_function = None  # type: Optional[PluginNameFilterFunction]
        # Optional set: None: we never tried, empty: we tried, but found nothing
        self._cached_result = None  # type: Optional[Set[CheckPluginName]]

    def set_filter_function(self, filter_function):
        # type: (PluginNameFilterFunction) -> None
        self._filter_function = filter_function

    def __call__(
            self,
            snmp_config,  # type: SNMPHostConfig
            on_error,  # type: str
            do_snmp_scan,  # type: bool
            for_mgmt_board,  # type: bool
    ):
        """Returns a list of raw sections that shall be processed by this source.

        The logic is only processed once. Once processed, the answer is cached.
        """
        if self._filter_function is None:
            raise MKGeneralException("The check type filter function has not been set")

        if self._cached_result is not None:
            return self._cached_result

        # Make hostname globally available for scan functions.
        # This is rarely used, but e.g. the scan for if/if64 needs
        # this to evaluate if_disabled_if64_checks.
        check_api_utils.set_hostname(snmp_config.hostname)
        self._cached_result = self._filter_function(
            on_error=on_error,
            do_snmp_scan=do_snmp_scan,
            for_mgmt_board=for_mgmt_board,
            backend=factory.backend(snmp_config),
        )
        return self._cached_result


# TODO: Move common functionality of SNMPManagementBoardDataSource and
# SNMPDataSource to ABCSNMPDataSource and make SNMPManagementBoardDataSource
# inherit from ABCSNMPDataSource instead of SNMPDataSource
class ABCSNMPDataSource(DataSource[SNMPRawData, SNMPSections, SNMPPersistedSections,
                                   SNMPHostSections],
                        metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def _snmp_config(self):
        # type: () -> SNMPHostConfig
        raise NotImplementedError()


class SNMPDataSource(ABCSNMPDataSource):
    source_type = SourceType.HOST

    def __init__(
            self,
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            selected_raw_sections=None,  # type: Optional[Dict[PluginName, config.SectionPlugin]]
    ):
        # type: (...) -> None
        super(SNMPDataSource, self).__init__(
            hostname,
            ipaddress,
            None if selected_raw_sections is None else
            {s.name for s in selected_raw_sections.values() if isinstance(s, SNMPSectionPlugin)},
        )
        self._detector = CachedSNMPDetector()
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False
        self._fetched_raw_section_names = set()  # type: Set[PluginName]

    def id(self):
        # type: () -> str
        return "snmp"

    def title(self):
        # type: () -> str
        return "SNMP"

    def _cpu_tracking_id(self):
        # type: () -> str
        return "snmp"

    @property
    def _snmp_config(self):
        # type: () -> SNMPHostConfig
        # TODO: snmp_config.ipaddress is not Optional. At least classic SNMP enforces that there
        # is an address set, Inline-SNMP has some lookup logic for some reason. We need to find
        # out whether or not we can really have None here. Looks like it could be the case for
        # cluster hosts which don't have an IP address set.
        if self._ipaddress is None:
            raise NotImplementedError("Invalid SNMP host configuration: self._ipaddress is None")
        return self._host_config.snmp_config(self._ipaddress)

    def describe(self):
        # type: () -> str
        snmp_config = self._snmp_config
        if snmp_config.is_usewalk_host:
            return "SNMP (use stored walk)"

        if snmp_config.is_inline_snmp_host:
            inline = "yes"
        else:
            inline = "no"

        if snmp_config.is_snmpv3_host:
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        if snmp_config.is_snmpv3_host or snmp_config.is_bulkwalk_host:
            bulk = "yes"
        else:
            bulk = "no"

        return "%s (%s, Bulk walk: %s, Port: %d, Inline: %s)" % \
               (self.title(), credentials_text, bulk, snmp_config.port, inline)

    def _empty_raw_data(self):
        # type: () -> SNMPRawData
        return {}

    def _empty_host_sections(self):
        # type: () -> SNMPHostSections
        return SNMPHostSections()

    def _from_cache_file(self, raw_data):
        # type: (bytes) -> SNMPRawData
        return ast.literal_eval(raw_data.decode("utf-8"))

    def _to_cache_file(self, raw_data):
        # type: (SNMPRawData) -> bytes
        return (repr(raw_data) + "\n").encode("utf-8")

    def set_ignore_check_interval(self, ignore_check_interval):
        # type: (bool) -> None
        self._ignore_check_interval = ignore_check_interval

    def set_use_snmpwalk_cache(self, use_snmpwalk_cache):
        # type: (bool) -> None
        self._use_snmpwalk_cache = use_snmpwalk_cache

    # TODO: Check if this can be dropped
    def set_on_error(self, on_error):
        # type: (str) -> None
        self._on_error = on_error

    # TODO: Check if this can be dropped
    def set_do_snmp_scan(self, do_snmp_scan):
        # type: (bool) -> None
        self._do_snmp_scan = do_snmp_scan

    def get_do_snmp_scan(self):
        # type: () -> bool
        return self._do_snmp_scan

    def set_check_plugin_name_filter(self, filter_func):
        # type: (PluginNameFilterFunction) -> None
        self._detector.set_filter_function(filter_func)

    def set_fetched_raw_section_names(self, raw_section_names):
        # type: (Set[PluginName]) -> None
        """Sets a list of already fetched host sections/check plugin names.

        Especially for SNMP data sources there are already fetched
        host sections of executed check plugins. But for some inventory plugins
        which have no related check plugin the host must be contacted again
        in order to create the full tree.
        """
        self._fetched_raw_section_names = raw_section_names

    def _execute(self):
        # type: () -> SNMPRawData
        verify_ipaddress(self._ipaddress)
        with SNMPDataFetcher(
                self._make_oid_infos(),
                self._use_snmpwalk_cache,
                self._snmp_config,
        ) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def _make_oid_infos(self):
        # type: () -> Dict[str, List[SNMPTree]]
        oid_infos = {}  # Dict[str, List[SNMPTree]]
        raw_sections_to_process = {PluginName(n) for n in self._get_raw_section_names_to_process()}
        for section_name in self._sort_section_names(raw_sections_to_process):
            plugin = config.registered_snmp_sections.get(section_name)
            if plugin is None:
                self._logger.debug("%s: No such section definiton", section_name)
                continue

            if section_name in self._fetched_raw_section_names:
                continue

            # This checks data is configured to be persisted (snmp_check_interval) and recent enough.
            # Skip gathering new data here. The persisted data will be added later
            if self._persisted_sections and str(section_name) in self._persisted_sections:
                self._logger.debug("%s: Skip fetching data (persisted info exists)", section_name)
                continue

            oid_infos[str(section_name)] = plugin.trees
        return oid_infos

    def _get_raw_section_names_to_process(self):
        # type: () -> Set[CheckPluginName]
        """Return a set of raw section names that shall be processed"""
        # TODO (mo): Make this (and the called) function(s) return the sections directly!
        if self._selected_raw_section_names is not None:
            return {str(n) for n in self._selected_raw_section_names}

        # TODO (mo): At the moment, we must also consider the legacy version:
        if self._enforced_check_plugin_names is not None:
            # TODO (mo): centralize maincheckify: CMK-4295
            return {maincheckify(n) for n in self._enforced_check_plugin_names}

        return self._detector(
            self._snmp_config,
            on_error=self._on_error,
            do_snmp_scan=self._do_snmp_scan,
            for_mgmt_board=self.source_type is SourceType.MANAGEMENT,
        )

    @staticmethod
    def _sort_section_names(section_names):
        # type: (Set[PluginName]) -> List[PluginName]
        # In former Check_MK versions (<=1.4.0) CPU check plugins were
        # checked before other check plugins like interface checks.
        # In Check_MK versions >= 1.5.0 the order is random and
        # interface check plugins are executed before CPU check plugins.
        # This leads to high CPU utilization sent by device. Thus we have
        # to re-order the check plugin names.
        # There are some nested check plugin names which have to be considered, too.
        #   for f in $(grep "service_description.*CPU [^lL]" -m1 * | cut -d":" -f1); do
        #   if grep -q "snmp_info" $f; then echo $f; fi done
        cpu_sections_without_cpu_in_name = {
            PluginName("brocade_sys"),
            PluginName("bvip_util"),
        }
        return sorted(section_names,
                      key=lambda x:
                      (not ('cpu' in str(x) or x in cpu_sections_without_cpu_in_name), x))

    def _convert_to_sections(self, raw_data):
        # type: (SNMPRawData) -> SNMPHostSections
        raw_data = cast(SNMPRawData, raw_data)
        sections_to_persist = self._extract_persisted_sections(raw_data)
        return SNMPHostSections(raw_data, persisted_sections=sections_to_persist)

    def _extract_persisted_sections(self, raw_data):
        # type: (SNMPRawData) -> SNMPPersistedSections
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections = {}  # type: SNMPPersistedSections

        for section_name, section_content in raw_data.items():
            check_interval = self._host_config.snmp_check_interval(section_name)
            if check_interval is None:
                continue

            cached_at = int(time.time())
            until = cached_at + (check_interval * 60)
            persisted_sections[section_name] = (cached_at, until, section_content)

        return persisted_sections


#.
#   .--SNMP Mgmt.----------------------------------------------------------.
#   |       ____  _   _ __  __ ____    __  __                 _            |
#   |      / ___|| \ | |  \/  |  _ \  |  \/  | __ _ _ __ ___ | |_          |
#   |      \___ \|  \| | |\/| | |_) | | |\/| |/ _` | '_ ` _ \| __|         |
#   |       ___) | |\  | |  | |  __/  | |  | | (_| | | | | | | |_ _        |
#   |      |____/|_| \_|_|  |_|_|     |_|  |_|\__, |_| |_| |_|\__(_)       |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   | Special case for managing the Management Board SNMP data             |
#   '----------------------------------------------------------------------'

#TODO
# 1. TCP host + SNMP MGMT Board: standard SNMP beibehalten
# 2. snmpv3 context


class SNMPManagementBoardDataSource(SNMPDataSource):
    source_type = SourceType.MANAGEMENT

    def __init__(
            self,
            hostname,  # type: HostName
            ipaddress,  # type: Optional[HostAddress]
            selected_raw_sections=None,  # type: Optional[Dict[PluginName, config.SectionPlugin]]
    ):
        # type: (...) -> None
        super(SNMPManagementBoardDataSource, self).__init__(hostname, ipaddress,
                                                            selected_raw_sections)
        self._credentials = cast(SNMPCredentials, self._host_config.management_credentials)

    def id(self):
        # type: () -> str
        return "mgmt_snmp"

    def title(self):
        # type: () -> str
        return "Management board - SNMP"

    @property
    def _snmp_config(self):
        # type: () -> SNMPHostConfig
        return self._host_config.management_snmp_config
