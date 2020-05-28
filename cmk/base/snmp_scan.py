#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any, Callable, Dict, Iterable, Optional, Set, Union

import cmk.utils.snmp_cache as snmp_cache
import cmk.utils.tty as tty
from cmk.utils.check_utils import section_name_of
from cmk.utils.exceptions import MKGeneralException, MKSNMPError
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import OID, CheckPluginName, DecodedString, SNMPHostConfig

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.snmp as snmp
from cmk.base.api import PluginName
from cmk.base.api.agent_based.section_types import SNMPDetectAtom, SNMPDetectSpec
from cmk.base.snmp_utils import ScanFunction


def _evaluate_snmp_detection(oid_function, detect_spec):
    # type: (Callable, SNMPDetectSpec) -> bool
    """This is a compatibility wrapper for the new SNMP detection.
    """
    # TODO: Once this is the only used method, we can consolidate
    #       this into the code below and simplify.
    return any(
        all(_evaluate_snmp_detection_atom(oid_function, atom)
            for atom in alternative)
        for alternative in detect_spec)


def _evaluate_snmp_detection_atom(oid_function, atom):
    # type: (Callable, SNMPDetectAtom) -> bool
    oid, pattern, flag = atom
    value = oid_function(oid)
    if value is None:
        # check for "not_exists"
        return pattern == '.*' and not flag
    # ignore case!
    return bool(regex(pattern, re.IGNORECASE).fullmatch(value)) is flag


# gather auto_discovered check_plugin_names for this host
def gather_available_raw_section_names(host_config,
                                       on_error,
                                       do_snmp_scan,
                                       for_inventory=False,
                                       for_mgmt_board=False):
    # type: (SNMPHostConfig, str, bool, bool, bool) -> Set[CheckPluginName]
    try:
        return _snmp_scan(
            host_config,
            on_error=on_error,
            do_snmp_scan=do_snmp_scan,
            for_inv=for_inventory,
            for_mgmt_board=for_mgmt_board,
        )
    except Exception as e:
        if on_error == "raise":
            raise
        if on_error == "warn":
            console.error("SNMP scan failed: %s\n" % e)

    return set()


def _snmp_scan(host_config,
               on_error="ignore",
               for_inv=False,
               do_snmp_scan=True,
               for_mgmt_board=False):
    # type: (SNMPHostConfig, str, bool, bool, bool) -> Set[CheckPluginName]
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel

    # Make hostname globally available for scan functions.
    # This is rarely used, but e.g. the scan for if/if64 needs
    # this to evaluate if_disabled_if64_checks.
    check_api_utils.set_hostname(host_config.hostname)

    snmp_cache.initialize_single_oid_cache(host_config)
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
        snmp_cache.set_single_oid_cache(".1.3.6.1.2.1.1.1.0", "")
        snmp_cache.set_single_oid_cache(".1.3.6.1.2.1.1.2.0", "")

    if for_inv:
        these_plugin_names = [
            name for name in inventory_plugins.inv_info if inventory_plugins.is_snmp_plugin(name)
        ]
    else:
        # TODO (mo): stop converting to string!
        these_plugin_names = [str(n) for n in config.registered_snmp_sections]

    found_plugins = set()  # type: Set[CheckPluginName]

    for check_plugin_name in these_plugin_names:

        detection_spec = _get_detection_spec_from_plugin_name(check_plugin_name,
                                                              inventory_plugins.inv_info)

        if detection_spec is None:
            console.warning("   SNMP check %s: Could not detect specifications for plugin" %
                            check_plugin_name)

            continue

        try:

            def oid_function(oid, default_value=None, cp_name=check_plugin_name):
                # type: (OID, Optional[DecodedString], Optional[CheckPluginName]) -> Optional[DecodedString]
                value = snmp.get_single_oid(host_config, oid, cp_name, do_snmp_scan=do_snmp_scan)
                return default_value if value is None else value

            if callable(detection_spec):
                result = detection_spec(oid_function)
            else:
                result = _evaluate_snmp_detection(oid_function, detection_spec)

            if result is not None and not isinstance(result, (str, bool)):
                if on_error == "warn":
                    console.warning("   SNMP scan function of %s returns invalid type %s." %
                                    (check_plugin_name, type(result)))
                elif on_error == "raise":
                    raise MKGeneralException("SNMP Scan aborted.")
            elif result:
                found_plugins.add(check_plugin_name)
        except MKGeneralException:
            # some error messages which we explicitly want to show to the user
            # should be raised through this
            raise
        except Exception:
            if on_error == "warn":
                console.warning("   Exception in SNMP scan function of %s" % check_plugin_name)
            elif on_error == "raise":
                raise

    _output_snmp_check_plugins("SNMP scan found", found_plugins)

    filtered = config.filter_by_management_board(
        host_config.hostname,
        found_plugins,
        for_mgmt_board,
        for_discovery=True,
        for_inventory=for_inv,
    )

    _output_snmp_check_plugins("SNMP filtered check plugin names", filtered)
    snmp_cache.write_single_oid_cache(host_config)
    return filtered


def _get_detection_spec_from_plugin_name(check_plugin_name, inv_info):
    # type: (CheckPluginName, Dict[str, Any]) -> Union[SNMPDetectSpec, Optional[ScanFunction]]
    # This function will hopefully shrink and finally disappear during API development.
    section_name = section_name_of(check_plugin_name)
    section_plugin = config.registered_snmp_sections.get(PluginName(section_name))
    if section_plugin:
        return section_plugin.detect_spec

    # TODO (mo): migrate section definitions from inventory plugins to
    #            section plugins and remove this conditional entirely
    info = inv_info[section_name]
    return info.get("snmp_scan_function")


def _output_snmp_check_plugins(title, collection):
    # type: (str, Iterable[CheckPluginName]) -> None
    if collection:
        collection_out = " ".join(sorted(collection))
    else:
        collection_out = "-"
    console.vverbose("   %-35s%s%s%s%s\n" %
                     (title, tty.bold, tty.yellow, collection_out, tty.normal))
