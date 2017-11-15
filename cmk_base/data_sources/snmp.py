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

from cmk.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.checks as checks
import cmk_base.snmp as snmp
import cmk_base.ip_lookup as ip_lookup

from .abstract import DataSource
from .host_info import HostInfo

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

# Handle SNMP check interval. The idea: An SNMP check should only be
# executed every X seconds. Skip when called too often.
# TODO: The time information was lost in the step we merged the SNMP cache files
#       together. Can't we handle this equal to the persisted agent sections? The
#       check would then be executed but with "old data". That would be nice!
#check_interval = config.check_interval_of(hostname, check_type)
#cache_path = "%s/%s" % (cmk.paths.snmp_cache_dir, hostname)
#if not self._ignore_check_interval \
#   and not _no_submit \
#   and check_interval is not None and os.path.exists(cache_path) \
#   and cmk_base.utils.cachefile_age(cache_path) < check_interval * 60:
#    # cache file is newer than check_interval, skip this check
#    raise MKSkipCheck()
class SNMPDataSource(DataSource):
    def __init__(self):
        super(SNMPDataSource, self).__init__()
        self._check_type_filter_func = None
        self._check_types = {}
        self._do_snmp_scan = False
        self._on_error = "raise"
        self._use_snmpwalk_cache = True
        self._ignore_check_interval = False


    def id(self):
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
        return repr(info)


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


    def set_check_type_filter(self, filter_func):
        self._check_type_filter_func = filter_func


    def get_check_types(self, hostname, ipaddress):
        """Returns a list of check types that shal be executed with this source.

        The logic is only processed once per hostname+ipaddress combination. Once processed
        check types are cached to answer subsequent calls to this function.
        """
        if self._check_type_filter_func is None:
            raise MKGeneralException("The check type filter function has not been set")

        try:
            return self._check_types[(hostname, ipaddress)]
        except KeyError:
            check_types = self._check_type_filter_func(hostname, ipaddress,
                                                       on_error=self._on_error,
                                                       do_snmp_scan=self._do_snmp_scan)
            self._check_types[(hostname, ipaddres)] = check_types
            return check_types


    def _execute(self, hostname, ipaddress):
    	import cmk_base.inventory_plugins

        self._verify_ipaddress(ipaddress)

        info = {}
        for check_type in self.get_check_types(hostname, ipaddress):
            # Is this an SNMP table check? Then snmp_info specifies the OID to fetch
            # Please note, that if the check_type is foo.bar then we lookup the
            # snmp info for "foo", not for "foo.bar".
            info_type = check_type.split(".")[0]
            if info_type in checks.snmp_info:
                oid_info = checks.snmp_info[info_type]
            elif info_type in cmk_base.inventory_plugins.inv_info:
                oid_info = cmk_base.inventory_plugins.inv_info[info_type].get("snmp_info")
            else:
                oid_info = None

            if oid_info is None:
                continue

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            if type(oid_info) == list:
                check_info = []
                for entry in oid_info:
                    check_info_part = snmp.get_snmp_table(hostname, ipaddress, check_type, entry, self._use_snmpwalk_cache)

                    # If at least one query fails, we discard the whole info table
                    if check_info_part is None:
                        check_info = None
                        break
                    else:
                        check_info.append(check_info_part)
            else:
                check_info = snmp.get_snmp_table(hostname, ipaddress, check_type, oid_info, self._use_snmpwalk_cache)

            info[check_type] = check_info

        return info


    def _convert_to_infos(self, raw_data, hostname):
        return HostInfo(raw_data)


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
