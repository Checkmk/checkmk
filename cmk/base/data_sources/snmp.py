#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import ast
import time
from typing import Callable, Tuple, cast, Set, Optional, Dict, List, Union  # pylint: disable=unused-import
import six

from cmk.utils.exceptions import MKGeneralException

import cmk.base.config as config
import cmk.base.snmp as snmp
import cmk.base.snmp_utils as snmp_utils
from cmk.base.utils import (  # pylint: disable=unused-import
    HostName, HostAddress,
)
from cmk.base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName, PiggybackRawData, SectionCacheInfo, SectionName,
)
from cmk.base.snmp_utils import (  # pylint: disable=unused-import
    OIDInfo, SNMPTable, RawSNMPData, PersistedSNMPSections, SNMPSections, SNMPSectionContent,
    SNMPCredentials,
)

from .abstract import DataSource, ManagementBoardDataSource  # pylint: disable=unused-import
from .host_sections import AbstractHostSections

PluginNameFilterFunction = Callable[[snmp_utils.SNMPHostConfig, str, bool, bool],
                                    Set[CheckPluginName]]

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


class SNMPHostSections(AbstractHostSections[RawSNMPData, SNMPSections, PersistedSNMPSections,
                                            SNMPSectionContent]):
    def __init__(self,
                 sections=None,
                 cache_info=None,
                 piggybacked_raw_data=None,
                 persisted_sections=None):
        # type: (Optional[SNMPSections], Optional[SectionCacheInfo], Optional[PiggybackRawData], Optional[PersistedSNMPSections]) -> None
        super(SNMPHostSections, self).__init__(
            sections=sections if sections is not None else {},
            cache_info=cache_info if cache_info is not None else {},
            piggybacked_raw_data=piggybacked_raw_data if piggybacked_raw_data is not None else {},
            persisted_sections=persisted_sections if persisted_sections is not None else {},
        )

    def _extend_section(self, section_name, section_content):
        # type: (SectionName, SNMPSectionContent) -> None
        raise NotImplementedError()


# TODO: Move common functionality of SNMPManagementBoardDataSource and
# SNMPDataSource to ABCSNMPDataSource and make SNMPManagementBoardDataSource
# inherit from ABCSNMPDataSource instead of SNMPDataSource
class ABCSNMPDataSource(
        six.with_metaclass(
            abc.ABCMeta, DataSource[RawSNMPData, SNMPSections, PersistedSNMPSections,
                                    SNMPHostSections])):
    @abc.abstractproperty
    def _snmp_config(self):
        # type: () -> snmp_utils.SNMPHostConfig
        raise NotImplementedError()


class SNMPDataSource(ABCSNMPDataSource):
    _for_mgmt_board = False

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(SNMPDataSource, self).__init__(hostname, ipaddress)
        self._check_plugin_name_filter_func = None  # type: Optional[PluginNameFilterFunction]
        self._check_plugin_names = {
        }  # type: Dict[Tuple[HostName, Optional[HostAddress]], Set[CheckPluginName]]
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False
        self._fetched_check_plugin_names = set()  # type: Set[CheckPluginName]

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
        # type: () -> snmp_utils.SNMPHostConfig
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

        if snmp_utils.is_snmpv3_host(snmp_config):
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        if snmp_utils.is_snmpv3_host(snmp_config) or snmp_config.is_bulkwalk_host:
            bulk = "yes"
        else:
            bulk = "no"

        return "%s (%s, Bulk walk: %s, Port: %d, Inline: %s)" % \
               (self.title(), credentials_text, bulk, snmp_config.port, inline)

    def _empty_raw_data(self):
        # type: () -> RawSNMPData
        return {}

    def _empty_host_sections(self):
        # type: () -> SNMPHostSections
        return SNMPHostSections()

    def _from_cache_file(self, raw_data):
        # type: (bytes) -> RawSNMPData
        return ast.literal_eval(raw_data.decode("utf-8"))

    def _to_cache_file(self, raw_data):
        # type: (RawSNMPData) -> bytes
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
        self._check_plugin_name_filter_func = filter_func

    def set_fetched_check_plugin_names(self, check_plugin_names):
        # type: (Set[CheckPluginName]) -> None
        """Sets a list of already fetched host sections/check plugin names.

        Especially for SNMP data sources there are already fetched
        host sections of executed check plugins. But for some inventory plugins
        which have no related check plugin the host must be contacted again
        in order to create the full tree.
        """
        self._fetched_check_plugin_names = check_plugin_names

    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        """Returns a list of check types that shal be executed with this source.

        The logic is only processed once per hostname+ipaddress combination. Once processed
        check types are cached to answer subsequent calls to this function.
        """

        if self._check_plugin_name_filter_func is None:
            raise MKGeneralException("The check type filter function has not been set")

        try:
            return self._check_plugin_names[(self._hostname, self._ipaddress)]
        except KeyError:
            # mypy complains: Unexpected keyword argument "for_mgmt_board"
            check_plugin_names = self._check_plugin_name_filter_func(  # type: ignore
                self._snmp_config,
                on_error=self._on_error,
                do_snmp_scan=self._do_snmp_scan,
                for_mgmt_board=self._for_mgmt_board)
            self._check_plugin_names[(self._hostname, self._ipaddress)] = check_plugin_names
            return check_plugin_names

    def _execute(self):
        # type: () -> RawSNMPData
        import cmk.base.inventory_plugins

        self._verify_ipaddress()

        check_plugin_names = self.get_check_plugin_names()

        snmp_config = self._snmp_config
        info = {}  # type: RawSNMPData
        oid_info = None  # type: Optional[OIDInfo]
        for check_plugin_name in self._sort_check_plugin_names(check_plugin_names):
            # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
            # Please note, that if the check_plugin_name is foo.bar then we lookup the
            # snmp info for "foo", not for "foo.bar".
            has_snmp_info = False
            section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
            if section_name in config.snmp_info:
                oid_info = config.snmp_info[section_name]  # type: ignore
            elif section_name in cmk.base.inventory_plugins.inv_info:
                oid_info = cmk.base.inventory_plugins.inv_info[section_name].get("snmp_info")
                if oid_info:
                    has_snmp_info = True
            else:
                oid_info = None

            if not has_snmp_info and check_plugin_name in self._fetched_check_plugin_names:
                continue

            if oid_info is None:
                continue

            # This checks data is configured to be persisted (snmp_check_interval) and recent enough.
            # Skip gathering new data here. The persisted data will be added latera
            if self._persisted_sections and section_name in self._persisted_sections:
                self._logger.debug("%s: Skip fetching data (persisted info exists)" %
                                   (check_plugin_name))
                continue

            # Prevent duplicate data fetching of identical section in case of SNMP sub checks
            if section_name in info:
                self._logger.debug("%s: Skip fetching data (section already fetched)" %
                                   (check_plugin_name))
                continue

            self._logger.debug("%s: Fetching data" % (check_plugin_name))

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            if isinstance(oid_info, list):
                check_info = []  # type: List[SNMPTable]
                for entry in oid_info:
                    check_info_part = snmp.get_snmp_table(snmp_config, check_plugin_name, entry,
                                                          self._use_snmpwalk_cache)
                    check_info.append(check_info_part)
                info[section_name] = check_info
            else:
                info[section_name] = snmp.get_snmp_table(snmp_config, check_plugin_name, oid_info,
                                                         self._use_snmpwalk_cache)

        return info

    def _sort_check_plugin_names(self, check_plugin_names):
        # type: (Set[CheckPluginName]) -> List[CheckPluginName]
        # In former Check_MK versions (<=1.4.0) CPU check plugins were
        # checked before other check plugins like interface checks.
        # In Check_MK versions >= 1.5.0 the order is random and
        # interface check plugins are executed before CPU check plugins.
        # This leads to high CPU utilization sent by device. Thus we have
        # to re-order the check plugin names.
        # There are some nested check plugin names which have to be considered, too.
        #   for f in $(grep "service_description.*CPU [^lL]" -m1 * | cut -d":" -f1); do
        #   if grep -q "snmp_info" $f; then echo $f; fi done
        cpu_checks_without_cpu_in_check_name = {"brocade_sys", "bvip_util"}
        return sorted(check_plugin_names,
                      key=lambda x:
                      (not ('cpu' in x or x in cpu_checks_without_cpu_in_check_name), x))

    def _convert_to_sections(self, raw_data):
        # type: (RawSNMPData) -> SNMPHostSections
        raw_data = cast(RawSNMPData, raw_data)
        sections_to_persist = self._extract_persisted_sections(raw_data)
        return SNMPHostSections(raw_data, persisted_sections=sections_to_persist)

    def _extract_persisted_sections(self, raw_data):
        # type: (RawSNMPData) -> PersistedSNMPSections
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections = {}  #  type: PersistedSNMPSections

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


class SNMPManagementBoardDataSource(ManagementBoardDataSource, SNMPDataSource):
    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(SNMPManagementBoardDataSource, self).__init__(hostname, ipaddress)
        self._credentials = cast(SNMPCredentials, self._host_config.management_credentials)

    def id(self):
        # type: () -> str
        return "mgmt_snmp"

    def title(self):
        # type: () -> str
        return "Management board - SNMP"

    @property
    def _snmp_config(self):
        # type: () -> snmp_utils.SNMPHostConfig
        return self._host_config.management_snmp_config
