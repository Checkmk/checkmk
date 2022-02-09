#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import SectionName

from . import snmp_cache
from .type_defs import OID, SNMPBackend, SNMPDecodedString, SNMPRawValue, SNMPRowInfo

SNMPRowInfoForStoredWalk = List[Tuple[OID, str]]
SNMPWalkOptions = Dict[str, List[OID]]

# .
#   .--Generic SNMP--------------------------------------------------------.
#   |     ____                      _        ____  _   _ __  __ ____       |
#   |    / ___| ___ _ __   ___ _ __(_) ___  / ___|| \ | |  \/  |  _ \      |
#   |   | |  _ / _ \ '_ \ / _ \ '__| |/ __| \___ \|  \| | |\/| | |_) |     |
#   |   | |_| |  __/ | | |  __/ |  | | (__   ___) | |\  | |  | |  __/      |
#   |    \____|\___|_| |_|\___|_|  |_|\___| |____/|_| \_|_|  |_|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Top level functions to realize SNMP functionality for Checkmk.      |
#   '----------------------------------------------------------------------'


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(
    oid: str, *, section_name: Optional[SectionName] = None, backend: SNMPBackend
) -> Optional[SNMPDecodedString]:
    # The OID can end with ".*". In that case we do a snmpgetnext and try to
    # find an OID with the prefix in question. The *cache* is working including
    # the X, however.
    if oid[0] != ".":
        if cmk.utils.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        oid = "." + oid

    # TODO: Use generic cache mechanism
    if oid in snmp_cache.single_oid_cache():
        console.vverbose("       Using cached OID %s: " % oid)
        cached_value = snmp_cache.single_oid_cache()[oid]
        console.vverbose("%s%s%r%s\n" % (tty.bold, tty.green, cached_value, tty.normal))
        return cached_value

    # get_single_oid() can only return a single value. When SNMPv3 is used with multiple
    # SNMP contexts, all contextes will be queried until the first answer is received.
    console.vverbose("       Getting OID %s: " % oid)
    for context_name in backend.config.snmpv3_contexts_of(section_name):
        try:
            value = backend.get(
                oid=oid,
                context_name=context_name,
            )

            if value is not None:
                break  # Use first received answer in case of multiple contextes
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            value = None

    if value is not None:
        console.vverbose("%s%s%r%s\n" % (tty.bold, tty.green, value, tty.normal))
    else:
        console.vverbose("failed.\n")

    if value is not None:
        decoded_value: Optional[SNMPDecodedString] = backend.config.ensure_str(
            value
        )  # used ensure_str function with different possible encoding arguments
    else:
        decoded_value = value

    snmp_cache.single_oid_cache()[oid] = decoded_value
    return decoded_value


def walk_for_export(oid: OID, *, backend: SNMPBackend) -> SNMPRowInfoForStoredWalk:
    return _convert_rows_for_stored_walk(backend.walk(oid=oid))


# .
#   .--SNMP helpers--------------------------------------------------------.
#   |     ____  _   _ __  __ ____    _          _                          |
#   |    / ___|| \ | |  \/  |  _ \  | |__   ___| |_ __   ___ _ __ ___      |
#   |    \___ \|  \| | |\/| | |_) | | '_ \ / _ \ | '_ \ / _ \ '__/ __|     |
#   |     ___) | |\  | |  | |  __/  | | | |  __/ | |_) |  __/ |  \__ \     |
#   |    |____/|_| \_|_|  |_|_|     |_| |_|\___|_| .__/ \___|_|  |___/     |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Internal helpers for processing SNMP things                          |
#   '----------------------------------------------------------------------'


def _convert_rows_for_stored_walk(rows: SNMPRowInfo) -> SNMPRowInfoForStoredWalk:
    def should_be_encoded(v: SNMPRawValue) -> bool:
        for c in bytearray(v):
            if c < 32 or c > 127:
                return True
        return False

    def hex_encode_value(v: SNMPRawValue) -> str:
        encoded = ""
        for c in bytearray(v):
            encoded += "%02X " % c
        return '"%s"' % encoded

    new_rows: SNMPRowInfoForStoredWalk = []
    for oid, value in rows:
        if value == b"ENDOFMIBVIEW":
            continue

        if should_be_encoded(value):
            new_rows.append((oid, hex_encode_value(value)))
        else:
            new_rows.append((oid, value.decode()))
    return new_rows


# .
#   .--Main modes----------------------------------------------------------.
#   |       __  __       _                             _                   |
#   |      |  \/  | __ _(_)_ __    _ __ ___   ___   __| | ___  ___         |
#   |      | |\/| |/ _` | | '_ \  | '_ ` _ \ / _ \ / _` |/ _ \/ __|        |
#   |      | |  | | (_| | | | | | | | | | | | (_) | (_| |  __/\__ \        |
#   |      |_|  |_|\__,_|_|_| |_| |_| |_| |_|\___/ \__,_|\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some main modes to help the user                                     |
#   '----------------------------------------------------------------------'


def do_snmptranslate(walk_filename: str) -> None:
    if not walk_filename:
        raise MKGeneralException("Please provide the name of a SNMP walk file")

    walk_path = Path(cmk.utils.paths.snmpwalks_dir) / walk_filename
    if not walk_path.exists():
        raise MKGeneralException("The walk '%s' does not exist" % walk_path)

    command: List[str] = [
        "snmptranslate",
        "-m",
        "ALL",
        "-M+%s" % cmk.utils.paths.local_mib_dir,
        "-",
    ]
    p = subprocess.Popen(  # pylint:disable=consider-using-with
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

    with walk_path.open("rb") as walk_file:
        walk = walk_file.read().split(b"\n")
    while walk[-1] == b"":
        del walk[-1]

    # to be compatible to previous version of this script, we do not feed
    # to original walk to snmptranslate (which would be possible) but a
    # version without values. The output should look like:
    # "[full oid] [value] --> [translated oid]"
    walk_without_values = b"\n".join(line.split(b" ", 1)[0] for line in walk)
    stdout, _stderr = p.communicate(walk_without_values)

    data_translated = stdout.split(b"\n")
    # remove last empty line (some tools add a '\n' at the end of the file, others not)
    if data_translated[-1] == b"":
        del data_translated[-1]

    if len(walk) != len(data_translated):
        raise MKGeneralException("call to snmptranslate returned a ambiguous result")

    for element_input, element_translated in zip(walk, data_translated):
        sys.stdout.buffer.write(element_input.strip())
        sys.stdout.buffer.write(b" --> ")
        sys.stdout.buffer.write(element_translated.strip())
        sys.stdout.buffer.write(b"\n")


def do_snmpwalk(options: SNMPWalkOptions, *, backend: SNMPBackend) -> None:
    if not os.path.exists(cmk.utils.paths.snmpwalks_dir):
        os.makedirs(cmk.utils.paths.snmpwalks_dir)

    # TODO: What about SNMP management boards?
    try:
        _do_snmpwalk_on(
            options, cmk.utils.paths.snmpwalks_dir + "/" + backend.hostname, backend=backend
        )
    except Exception as e:
        console.error("Error walking %s: %s\n" % (backend.hostname, e))
        if cmk.utils.debug.enabled():
            raise
    cmk.utils.cleanup.cleanup_globals()


def _do_snmpwalk_on(options: SNMPWalkOptions, filename: str, *, backend: SNMPBackend) -> None:
    console.verbose("%s:\n" % backend.hostname)

    oids = oids_to_walk(options)

    with Path(filename).open("w", encoding="utf-8") as file:
        for rows in _execute_walks_for_dump(oids, backend=backend):
            for oid, value in rows:
                file.write("%s %s\n" % (oid, value))
            console.verbose("%d variables.\n" % len(rows))

    console.verbose("Wrote fetched data to %s%s%s.\n" % (tty.bold, filename, tty.normal))


def _execute_walks_for_dump(
    oids: List[OID], *, backend: SNMPBackend
) -> Iterable[SNMPRowInfoForStoredWalk]:
    for oid in oids:
        try:
            console.verbose('Walk on "%s"...\n' % oid)
            yield walk_for_export(oid, backend=backend)
        except Exception as e:
            console.error("Error: %s\n" % e)
            if cmk.utils.debug.enabled():
                raise


def oids_to_walk(options: Optional[SNMPWalkOptions] = None) -> List[OID]:
    if options is None:
        options = {}

    oids = [".1.3.6.1.2.1", ".1.3.6.1.4.1"]  # SNMPv2-SMI::mib-2  # SNMPv2-SMI::enterprises

    if "oids" in options:
        oids = options["oids"]

    elif "extraoids" in options:
        oids += options["extraoids"]

    return sorted(oids, key=lambda x: list(map(int, x.strip(".").split("."))))


def do_snmpget(oid: OID, *, backend: SNMPBackend) -> None:
    # TODO what about SNMP management boards?
    snmp_cache.initialize_single_oid_cache(backend.config)

    value = get_single_oid(oid, backend=backend)
    sys.stdout.write("%s (%s): %r\n" % (backend.hostname, backend.address, value))
    cmk.utils.cleanup.cleanup_globals()
