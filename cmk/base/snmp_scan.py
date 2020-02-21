#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Set, List, Optional, Iterable  # pylint: disable=unused-import

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.tty as tty

import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.console as console
from cmk.base.exceptions import MKSNMPError
import cmk.base.snmp as snmp
from cmk.base.snmp_utils import SNMPHostConfig, OID, RawValue, ScanFunction  # pylint: disable=unused-import
import cmk.base.check_api_utils as check_api_utils
from cmk.base.check_utils import CheckPluginName  # pylint: disable=unused-import


# gather auto_discovered check_plugin_names for this host
def gather_snmp_check_plugin_names(host_config,
                                   on_error,
                                   do_snmp_scan,
                                   for_inventory=False,
                                   for_mgmt_board=False):
    # type: (SNMPHostConfig, str, bool, bool, bool) -> Set[CheckPluginName]
    check_plugin_names = set()  # type: Set[CheckPluginName]

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
        if on_error == "warn":
            console.error("SNMP scan failed: %s\n" % e)

    return check_plugin_names


def _snmp_scan(host_config,
               on_error="ignore",
               for_inv=False,
               do_snmp_scan=True,
               for_mgmt_board=False):
    # type: (SNMPHostConfig, str, bool, bool, bool) -> List[CheckPluginName]
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel

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
        snmp.set_single_oid_cache(".1.3.6.1.2.1.1.1.0", b"")
        snmp.set_single_oid_cache(".1.3.6.1.2.1.1.2.0", b"")

    found_check_plugin_names = set()  # type: Set[CheckPluginName]
    if for_inv:
        these_plugin_names = inventory_plugins.inv_info
    else:
        these_plugin_names = config.check_info

    positive_found = []  # type: List[CheckPluginName]
    default_found = []  # type: List[CheckPluginName]

    for check_plugin_name, _unused_check in these_plugin_names.items():
        if config.service_ignored(host_config.hostname, check_plugin_name, None):
            continue
        if for_inv and not inventory_plugins.is_snmp_plugin(check_plugin_name):
            continue
        if not for_inv and not cmk.base.check_utils.is_snmp_check(check_plugin_name):
            continue

        section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
        # The scan function should be assigned to the section_name, because
        # subchecks sharing the same SNMP info of course should have
        # an identical scan function. But some checks do not do this
        # correctly
        scan_function = None  # type: Optional[ScanFunction]
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
                    # type: (OID, Optional[RawValue], Optional[CheckPluginName]) -> Optional[RawValue]
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
                    found_check_plugin_names.add(check_plugin_name)
                    positive_found.append(check_plugin_name)
            except MKGeneralException:
                # some error messages which we explicitly want to show to the user
                # should be raised through this
                raise
            except Exception:
                if on_error == "warn":
                    console.warning("   Exception in SNMP scan function of %s" % check_plugin_name)
                elif on_error == "raise":
                    raise
        else:
            found_check_plugin_names.add(check_plugin_name)
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
    # type: (str, Iterable[CheckPluginName]) -> None
    if collection:
        collection_out = " ".join(sorted(collection))
    else:
        collection_out = "-"
    console.vverbose("   %-35s%s%s%s%s\n" %
                     (title, tty.bold, tty.yellow, collection_out, tty.normal))
