#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Callable, Iterable, NamedTuple, Set

from mypy_extensions import NamedArg

import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKSNMPError
from cmk.utils.log import console
from cmk.utils.regex import regex
from cmk.utils.type_defs import CheckPluginName, PluginName

import cmk.snmplib.snmp_cache as snmp_cache
import cmk.snmplib.snmp_modes as snmp_modes
from cmk.snmplib.type_defs import ABCSNMPBackend, SNMPDetectAtom, SNMPDetectSpec

SNMPScanSection = NamedTuple("SNMPScanSection", [
    ("name", PluginName),
    ("specs", SNMPDetectSpec),
])


def _evaluate_snmp_detection(detect_spec, cp_name, do_snmp_scan, *, backend):
    # type: (SNMPDetectSpec, str, bool, ABCSNMPBackend) -> bool
    """Evaluate a SNMP detection specification

    Return True if and and only if at least all conditions in one "line" are True
    """
    return any(
        all(
            _evaluate_snmp_detection_atom(atom, cp_name, do_snmp_scan, backend=backend)
            for atom in alternative)
        for alternative in detect_spec)


def _evaluate_snmp_detection_atom(atom, cp_name, do_snmp_scan, *, backend):
    # type: (SNMPDetectAtom, str, bool, ABCSNMPBackend) -> bool
    oid, pattern, flag = atom
    value = snmp_modes.get_single_oid(
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


PluginNameFilterFunction = Callable[[
    Iterable[SNMPScanSection],
    NamedArg(str, 'on_error'),
    NamedArg(bool, 'do_snmp_scan'),
    NamedArg(bool, "binary_host"),
    NamedArg(ABCSNMPBackend, 'backend'),
], Set[CheckPluginName]]


# gather auto_discovered check_plugin_names for this host
def gather_available_raw_section_names(sections, on_error, do_snmp_scan, *, binary_host, backend):
    # type: (Iterable[SNMPScanSection], str, bool, bool, ABCSNMPBackend) -> Set[CheckPluginName]
    try:
        return _snmp_scan(
            sections,
            on_error=on_error,
            do_snmp_scan=do_snmp_scan,
            binary_host=binary_host,
            backend=backend,
        )
    except Exception as e:
        if on_error == "raise":
            raise
        if on_error == "warn":
            console.error("SNMP scan failed: %s\n" % e)

    return set()


OID_SYS_DESCR = ".1.3.6.1.2.1.1.1.0"
OID_SYS_OBJ = ".1.3.6.1.2.1.1.2.0"


def _snmp_scan(sections, on_error="ignore", do_snmp_scan=True, *, binary_host, backend):
    # type: (Iterable[SNMPScanSection], str, bool, bool, ABCSNMPBackend) -> Set[CheckPluginName]
    snmp_cache.initialize_single_oid_cache(backend.config)
    console.vverbose("  SNMP scan:\n")
    _snmp_scan_cache_description(
        binary_host=binary_host,
        do_snmp_scan=do_snmp_scan,
        backend=backend,
    )

    found_plugins = _snmp_scan_find_plugins(sections,
                                            do_snmp_scan=do_snmp_scan,
                                            on_error=on_error,
                                            backend=backend)
    _output_snmp_check_plugins("SNMP scan found", found_plugins)
    snmp_cache.write_single_oid_cache(backend.config)
    return found_plugins


def _snmp_scan_cache_description(binary_host, *, do_snmp_scan, backend):
    # type: (bool, bool, ABCSNMPBackend) -> None
    if not binary_host:
        for oid, name in [(OID_SYS_DESCR, "system description"), (OID_SYS_OBJ, "system object")]:
            value = snmp_modes.get_single_oid(oid, do_snmp_scan=do_snmp_scan, backend=backend)
            if value is None:
                raise MKSNMPError("Cannot fetch %s OID %s. Please check your SNMP "
                                  "configuration. Possible reason might be: Wrong credentials, "
                                  "wrong SNMP version, Firewall rules, etc." % (name, oid))
    else:
        # Fake OID values to prevent issues with a lot of scan functions
        console.vverbose("       Skipping system description OID "
                         "(Set %s and %s to \"\")\n", OID_SYS_DESCR, OID_SYS_OBJ)
        snmp_cache.set_single_oid_cache(OID_SYS_DESCR, "")
        snmp_cache.set_single_oid_cache(OID_SYS_OBJ, "")


def _snmp_scan_find_plugins(sections, *, do_snmp_scan, on_error, backend):
    # type: (Iterable[SNMPScanSection], bool, str, ABCSNMPBackend) -> Set[CheckPluginName]
    found_plugins = set()  # type: Set[CheckPluginName]
    for name, specs in sections:
        try:
            if _evaluate_snmp_detection(
                    specs,
                    str(name),
                    do_snmp_scan,
                    backend=backend,
            ):
                found_plugins.add(str(name))
        except MKGeneralException:
            # some error messages which we explicitly want to show to the user
            # should be raised through this
            raise
        except Exception:
            if on_error == "warn":
                console.warning("   Exception in SNMP scan function of %s" % name)
            elif on_error == "raise":
                raise
    return found_plugins


def _output_snmp_check_plugins(title, collection):
    # type: (str, Iterable[CheckPluginName]) -> None
    if collection:
        collection_out = " ".join(sorted(collection))
    else:
        collection_out = "-"
    console.vverbose("   %-35s%s%s%s%s\n" %
                     (title, tty.bold, tty.yellow, collection_out, tty.normal))
