#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Iterable, Set

import cmk.utils.snmp_cache as snmp_cache
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKSNMPError
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import ABCSNMPBackend, CheckPluginName, SNMPHostConfig

import cmk.base.check_api_utils as check_api_utils
import cmk.base.config as config
import cmk.base.snmp as snmp
from cmk.base.api import PluginName
from cmk.base.api.agent_based.section_types import SNMPDetectAtom, SNMPDetectSpec
from cmk.fetchers import factory


def _evaluate_snmp_detection(detect_spec, host_config, cp_name, do_snmp_scan, *, backend):
    # type: (SNMPDetectSpec, SNMPHostConfig, str, bool, ABCSNMPBackend) -> bool
    """Evaluate a SNMP detection specification

    Return True if and and only if at least all conditions in one "line" are True
    """
    return any(
        all(
            _evaluate_snmp_detection_atom(atom, host_config, cp_name, do_snmp_scan, backend=backend)
            for atom in alternative)
        for alternative in detect_spec)


def _evaluate_snmp_detection_atom(atom, host_config, cp_name, do_snmp_scan, *, backend):
    # type: (SNMPDetectAtom, SNMPHostConfig, str, bool, ABCSNMPBackend) -> bool
    oid, pattern, flag = atom
    value = snmp.get_single_oid(
        host_config,
        oid,
        cp_name,
        do_snmp_scan=do_snmp_scan,
        backend=backend,
    )
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
    backend = factory.backend(host_config)

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
            value = snmp.get_single_oid(host_config,
                                        oid,
                                        do_snmp_scan=do_snmp_scan,
                                        backend=backend)
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

    # TODO (mo): Assumption here is that inventory plugins are significantly fewer
    #            than check plugins. We should pass an explicit list along, instead
    #            of this flag. That way we would also get rid of the import above.
    if for_inv:
        section_names = [PluginName(n) for n in inventory_plugins.inv_info]
        these_sections = [
            config.registered_snmp_sections[section_name]
            for section_name in section_names
            if section_name in config.registered_snmp_sections
        ]
    else:
        these_sections = list(config.registered_snmp_sections.values())

    found_plugins = set()  # type: Set[CheckPluginName]

    for section_plugin in these_sections:
        try:
            if _evaluate_snmp_detection(
                    section_plugin.detect_spec,
                    host_config,
                    str(section_plugin.name),
                    do_snmp_scan,
                    backend=backend,
            ):
                found_plugins.add(str(section_plugin.name))
        except MKGeneralException:
            # some error messages which we explicitly want to show to the user
            # should be raised through this
            raise
        except Exception:
            if on_error == "warn":
                console.warning("   Exception in SNMP scan function of %s" % section_plugin.name)
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


def _output_snmp_check_plugins(title, collection):
    # type: (str, Iterable[CheckPluginName]) -> None
    if collection:
        collection_out = " ".join(sorted(collection))
    else:
        collection_out = "-"
    console.vverbose("   %-35s%s%s%s%s\n" %
                     (title, tty.bold, tty.yellow, collection_out, tty.normal))
