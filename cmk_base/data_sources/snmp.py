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

import ast
import socket
import time

from cmk.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.snmp as snmp
import cmk_base.check_utils

from .abstract import DataSource, ManagementBoardDataSource
from .host_sections import HostSections

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

class SNMPDataSource(DataSource):
    _for_mgmt_board = False


    def __init__(self, hostname, ipaddress):
        super(SNMPDataSource, self).__init__(hostname, ipaddress)
        self._check_plugin_name_filter_func = None
        self._check_plugin_names = {}
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False
        self._fetched_check_plugin_names = []


    def id(self):
        return "snmp"


    def title(self):
        return "SNMP"


    def _cpu_tracking_id(self):
        return "snmp"


    def _get_access_data(self):
        return {
            "hostname": self._hostname,
            "ipaddress": self._ipaddress,
            "credentials": self._credentials()
        }


    def _credentials(self):
        return config.snmp_credentials_of(self._hostname)


    def describe(self):
        if config.is_usewalk_host(self._hostname):
            return "SNMP (use stored walk)"

        if config.is_inline_snmp_host(self._hostname):
            inline = "yes"
        else:
            inline = "no"

        credentials = self._credentials()
        if type(credentials) in [ str, unicode ]:
            cred = "Community: %r" % credentials
        else:
            cred = "Credentials: '%s'" % ", ".join(credentials)

        if config.is_snmpv3_host(self._hostname) or config.is_bulkwalk_host(self._hostname):
            bulk = "yes"
        else:
            bulk = "no"

        portinfo = config.snmp_port_of(self._hostname)
        if portinfo == None:
            portinfo = 'default'

        return "%s (%s, Bulk walk: %s, Port: %s, Inline: %s)" % \
                           (self.title(), cred, bulk, portinfo, inline)


    def _from_cache_file(self, raw_data):
        return ast.literal_eval(raw_data)


    def _to_cache_file(self, raw_data):
        return repr(raw_data) + "\n"


    def set_ignore_check_interval(self, ignore_check_interval):
        self._ignore_check_interval = ignore_check_interval


    def set_use_snmpwalk_cache(self, use_snmpwalk_cache):
        self._use_snmpwalk_cache = use_snmpwalk_cache


    # TODO: Check if this can be dropped
    def set_on_error(self, on_error):
        self._on_error = on_error


    # TODO: Check if this can be dropped
    def set_do_snmp_scan(self, do_snmp_scan):
        self._do_snmp_scan = do_snmp_scan


    def get_do_snmp_scan(self):
        return self._do_snmp_scan


    def set_check_plugin_name_filter(self, filter_func):
        self._check_plugin_name_filter_func = filter_func


    def set_fetched_check_plugin_names(self, check_plugin_names):
        """Sets a list of already fetched host sections/check plugin names.

        Especially for SNMP data sources there are already fetched
        host sections of executed check plugins. But for some inventory plugins
        which have no related check plugin the host must be contacted again
        in order to create the full tree.
        """
        self._fetched_check_plugin_names = check_plugin_names


    def _gather_check_plugin_names(self):
        """Returns a list of check types that shal be executed with this source.

        The logic is only processed once per hostname+ipaddress combination. Once processed
        check types are cached to answer subsequent calls to this function.
        """

        if self._check_plugin_name_filter_func is None:
            raise MKGeneralException("The check type filter function has not been set")

        try:
            return self._check_plugin_names[(self._hostname, self._ipaddress)]
        except KeyError:
            check_plugin_names = self._check_plugin_name_filter_func(self._get_access_data(),
                                                       on_error=self._on_error,
                                                       do_snmp_scan=self._do_snmp_scan,
                                                       for_mgmt_board=self._for_mgmt_board)
            self._check_plugin_names[(self._hostname, self._ipaddress)] = check_plugin_names
            return check_plugin_names


    def _execute(self):
        import cmk_base.inventory_plugins

        self._verify_ipaddress()

        persisted_sections = self._load_persisted_sections()

        check_plugin_names = self.get_check_plugin_names()

        info = {}
        for check_plugin_name in check_plugin_names:
            # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
            # Please note, that if the check_plugin_name is foo.bar then we lookup the
            # snmp info for "foo", not for "foo.bar".
            has_snmp_info = False
            section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
            if section_name in config.snmp_info:
                oid_info = config.snmp_info[section_name]
            elif section_name in cmk_base.inventory_plugins.inv_info:
                oid_info = cmk_base.inventory_plugins.inv_info[section_name].get("snmp_info")
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
            if section_name in persisted_sections:
                self._logger.debug("%s: Skip fetching data (persisted info exists)" % (check_plugin_name))
                continue

            # Prevent duplicate data fetching of identical section in case of SNMP sub checks
            if section_name in info:
                self._logger.debug("%s: Skip fetching data (section already fetched)" % (check_plugin_name))
                continue

            self._logger.debug("%s: Fetching data" % (check_plugin_name))

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            if type(oid_info) == list:
                check_info = []
                for entry in oid_info:
                    check_info_part = snmp.get_snmp_table(self._get_access_data(), check_plugin_name, entry, self._use_snmpwalk_cache)

                    # If at least one query fails, we discard the whole info table
                    if check_info_part is None:
                        check_info = None
                        break
                    else:
                        check_info.append(check_info_part)
            else:
                check_info = snmp.get_snmp_table(self._get_access_data(), check_plugin_name, oid_info, self._use_snmpwalk_cache)

            info[section_name] = check_info

        return info


    def _convert_to_sections(self, raw_data):
        persisted_sections = self._extract_persisted_sections(raw_data)
        return HostSections(raw_data, persisted_sections=persisted_sections)


    def _extract_persisted_sections(self, raw_data):
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections = {}

        for section_name, section_content in raw_data.items():
            check_interval = config.check_interval_of(self._hostname, section_name)
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
    def id(self):
        return "mgmt_snmp"


    def title(self):
        return "Management board - SNMP"
