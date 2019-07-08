#!/usr/bin/python
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

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.tty as tty

import cmk_base.check_utils
import cmk_base.config as config
import cmk_base.console as console
from cmk_base.exceptions import MKSNMPError
import cmk_base.snmp as snmp
import cmk_base.check_api_utils as check_api_utils


# gather auto_discovered check_plugin_names for this host
def gather_snmp_check_plugin_names(host_config,
                                   on_error,
                                   do_snmp_scan,
                                   for_inventory=False,
                                   for_mgmt_board=False):
    check_plugin_names = set()

    try:
        check_plugin_names.update(
            _snmp_scan(host_config,
                       on_error=on_error,
                       do_snmp_scan=do_snmp_scan,
                       for_inv=for_inventory,
                       for_mgmt_board=for_mgmt_board))
    except Exception as e:
        if on_error == "raise":
            raise
        elif on_error == "warn":
            console.error("SNMP scan failed: %s\n" % e)

    return list(check_plugin_names)


def _snmp_scan(host_config,
               on_error="ignore",
               for_inv=False,
               do_snmp_scan=True,
               for_mgmt_board=False):
    import cmk_base.inventory_plugins as inventory_plugins

    # Make hostname globally available for scan functions.
    # This is rarely used, but e.g. the scan for if/if64 needs
    # this to evaluate if_disabled_if64_checks.
    check_api_utils.set_hostname(host_config.hostname)

    snmp.initialize_single_oid_cache(host_config)
    console.vverbose("  SNMP scan:\n")
    if not config.get_config_cache().in_binary_hostlist(host_config.hostname,
                                                        config.snmp_without_sys_descr):
        for oid, name in [(".1.3.6.1.2.1.1.1.0", "system description"),
                          (".1.3.6.1.2.1.1.2.0", "system object")]:
            value = snmp.get_single_oid(host_config, oid, do_snmp_scan=do_snmp_scan)
            if value is None:
                raise MKSNMPError(
                    "Cannot fetch %s OID %s. This might be OK for some bogus devices. "
                    "In that case please configure the ruleset \"Hosts without system "
                    "description OID\" to tell Check_MK not to fetch the system "
                    "description and system object OIDs." % (name, oid))
    else:
        # Fake OID values to prevent issues with a lot of scan functions
        console.vverbose("       Skipping system description OID "
                         "(Set .1.3.6.1.2.1.1.1.0 and .1.3.6.1.2.1.1.2.0 to \"\")\n")
        snmp.set_single_oid_cache(host_config, ".1.3.6.1.2.1.1.1.0", "")
        snmp.set_single_oid_cache(host_config, ".1.3.6.1.2.1.1.2.0", "")

    found_check_plugin_names = []
    if for_inv:
        items = inventory_plugins.inv_info.items()
    else:
        items = config.check_info.items()

    positive_found = []
    default_found = []

    for check_plugin_name, _unused_check in items:
        if config.service_ignored(host_config.hostname, check_plugin_name, None):
            continue
        else:
            if for_inv and not inventory_plugins.is_snmp_plugin(check_plugin_name):
                continue
            elif not for_inv and not cmk_base.check_utils.is_snmp_check(check_plugin_name):
                continue

        section_name = cmk_base.check_utils.section_name_of(check_plugin_name)
        # The scan function should be assigned to the section_name, because
        # subchecks sharing the same SNMP info of course should have
        # an identical scan function. But some checks do not do this
        # correctly
        if check_plugin_name in config.snmp_scan_functions:
            scan_function = config.snmp_scan_functions[check_plugin_name]
        elif section_name in config.snmp_scan_functions:
            scan_function = config.snmp_scan_functions[section_name]
        elif section_name in inventory_plugins.inv_info:
            scan_function = inventory_plugins.inv_info[section_name].get("snmp_scan_function")
        else:
            scan_function = None

        if scan_function:
            try:

                def oid_function(oid, default_value=None, cp_name=check_plugin_name):
                    value = snmp.get_single_oid(host_config,
                                                oid,
                                                cp_name,
                                                do_snmp_scan=do_snmp_scan)
                    return default_value if value is None else value

                result = scan_function(oid_function)
                if result is not None and not isinstance(result, (str, bool)):
                    if on_error == "warn":
                        console.warning("   SNMP scan function of %s returns invalid type %s." %
                                        (check_plugin_name, type(result)))
                    elif on_error == "raise":
                        raise MKGeneralException("SNMP Scan aborted.")
                elif result:
                    found_check_plugin_names.append(check_plugin_name)
                    positive_found.append(check_plugin_name)
            except MKGeneralException:
                # some error messages which we explicitly want to show to the user
                # should be raised through this
                raise
            except:
                if on_error == "warn":
                    console.warning("   Exception in SNMP scan function of %s" % check_plugin_name)
                elif on_error == "raise":
                    raise
        else:
            found_check_plugin_names.append(check_plugin_name)
            default_found.append(check_plugin_name)

    _output_snmp_check_plugins("SNMP scan found", positive_found)
    if default_found:
        _output_snmp_check_plugins("SNMP without scan function", default_found)

    filtered = config.filter_by_management_board(host_config.hostname,
                                                 found_check_plugin_names,
                                                 for_mgmt_board,
                                                 for_discovery=True,
                                                 for_inventory=for_inv)

    _output_snmp_check_plugins("SNMP filtered check plugin names", filtered)
    snmp.write_single_oid_cache(host_config)
    return sorted(filtered)


def _output_snmp_check_plugins(title, collection):
    if collection:
        collection_out = " ".join(sorted(collection))
    else:
        collection_out = "-"
    console.vverbose("   %-35s%s%s%s%s\n" % \
                    (title, tty.bold, tty.yellow, collection_out, tty.normal))
