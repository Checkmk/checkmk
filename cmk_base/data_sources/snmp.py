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
import cmk_base.checks as checks
import cmk_base.snmp as snmp
import cmk_base.ip_lookup as ip_lookup

from .abstract import DataSource
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


    def __init__(self):
        super(SNMPDataSource, self).__init__()
        self._check_plugin_name_filter_func = None
        self._check_plugin_names = {}
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False


    def id(self):
        return "snmp"


    def _cpu_tracking_id(self):
        return "snmp"


    def describe(self, hostname, ipaddress):
        if config.is_usewalk_host(hostname):
            return "SNMP (use stored walk)"

        if config.is_inline_snmp_host(hostname):
            inline = "yes"
        else:
            inline = "no"

        credentials = config.snmp_credentials_of(hostname)
        if type(credentials) in [ str, unicode ]:
            cred = "Community: %r" % credentials
        else:
            cred = "Credentials: '%s'" % ", ".join(credentials)

        if config.is_snmpv3_host(hostname) or config.is_bulkwalk_host(hostname):
            bulk = "yes"
        else:
            bulk = "no"

        portinfo = config.snmp_port_of(hostname)
        if portinfo == None:
            portinfo = 'default'

        return "SNMP (%s, Bulk walk: %s, Port: %s, Inline: %s)" % \
                                   (cred, bulk, portinfo, inline)


    def _from_cache_file(self, raw_data):
        return ast.literal_eval(raw_data)


    def _to_cache_file(self, info):
        return repr(info) + "\n"


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


    def set_check_plugin_name_filter(self, filter_func):
        self._check_plugin_name_filter_func = filter_func


    def _gather_check_plugin_names(self, hostname, ipaddress):
        """Returns a list of check types that shal be executed with this source.

        The logic is only processed once per hostname+ipaddress combination. Once processed
        check types are cached to answer subsequent calls to this function.
        """
        if self._check_plugin_name_filter_func is None:
            raise MKGeneralException("The check type filter function has not been set")

        try:
            return self._check_plugin_names[(hostname, ipaddress)]
        except KeyError:
            check_plugin_names = self._check_plugin_name_filter_func(hostname, ipaddress,
                                                       on_error=self._on_error,
                                                       do_snmp_scan=self._do_snmp_scan,
                                                       for_mgmt_board=self._for_mgmt_board)
            self._check_plugin_names[(hostname, ipaddress)] = check_plugin_names
            return check_plugin_names


    def _execute(self, hostname, ipaddress):
    	import cmk_base.inventory_plugins

        self._verify_ipaddress(ipaddress)

        persisted_sections = self._load_persisted_sections(hostname)

        info = {}
        for check_plugin_name in self.get_check_plugin_names(hostname, ipaddress):
            # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
            # Please note, that if the check_plugin_name is foo.bar then we lookup the
            # snmp info for "foo", not for "foo.bar".
            section_name = checks.section_name_of(check_plugin_name)
            if section_name in checks.snmp_info:
                oid_info = checks.snmp_info[section_name]
            elif section_name in cmk_base.inventory_plugins.inv_info:
                oid_info = cmk_base.inventory_plugins.inv_info[section_name].get("snmp_info")
            else:
                oid_info = None

            if oid_info is None:
                continue

            # This checks data is configured to be persisted (snmp_check_interval) and recent enough.
            # Skip gathering new data here. The persisted data will be added latera
            if section_name in persisted_sections:
                self._logger.debug("[%s] %s: Skip fetching data (persisted info exists)" % (self.id(), check_plugin_name))
                continue

            self._logger.debug("[%s] %s: Fetching data" % (self.id(), check_plugin_name))

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            if type(oid_info) == list:
                check_info = []
                for entry in oid_info:
                    check_info_part = snmp.get_snmp_table(hostname, ipaddress, check_plugin_name, entry, self._use_snmpwalk_cache)

                    # If at least one query fails, we discard the whole info table
                    if check_info_part is None:
                        check_info = None
                        break
                    else:
                        check_info.append(check_info_part)
            else:
                check_info = snmp.get_snmp_table(hostname, ipaddress, check_plugin_name, oid_info, self._use_snmpwalk_cache)

            info[section_name] = check_info

        return info


    def _convert_to_sections(self, raw_data, hostname):
        persisted_sections = self._extract_persisted_sections(hostname, raw_data)
        return HostSections(raw_data, persisted_sections=persisted_sections)


    def _extract_persisted_sections(self, hostname, raw_data):
        """Extract the sections to be persisted from the raw_data and return it

        Gather the check types to be persisted, extract the related data from
        the raw data, calculate the times and store the persisted info for
        later use.
        """
        persisted_sections = {}

        for section_name, section_content in raw_data.items():
            check_interval = config.check_interval_of(hostname, section_name)
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

class SNMPManagementBoardDataSource(SNMPDataSource):
    _for_mgmt_board = True


    def id(self):
        return "mgmt_snmp"


    def _execute(self, hostname, ipaddress):
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        mgmt_ipaddress = config.management_address(hostname)
        if not self._is_ipaddress(mgmt_ipaddress):
            mgmt_ipaddress = ip_lookup.lookup_ip_address(mgmt_ipaddress)

        return super(SNMPManagementBoardDataSource, self)._execute(hostname, mgmt_ipaddress)


    # TODO: Why is it used only here?
    def _is_ipaddress(self, address):
        try:
            socket.inet_pton(socket.AF_INET, address)
            return True
        except socket.error:
            # not a ipv4 address
            pass

        try:
            socket.inet_pton(socket.AF_INET6, address)
            return True
        except socket.error:
            # no ipv6 address either
            return False
