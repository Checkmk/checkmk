#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.sectionname import SectionName

from ._typedefs import OID, SNMPBackend, SNMPDecodedString, SNMPRawValue, SNMPRowInfo

SNMPRowInfoForStoredWalk = list[tuple[OID, str]]
SNMPWalkOptions = dict[str, list[OID]]


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(
    oid: str,
    *,
    section_name: SectionName | None = None,
    single_oid_cache: dict[OID, SNMPDecodedString | None],
    backend: SNMPBackend,
) -> SNMPDecodedString | None:
    # The OID can end with ".*". In that case we do a snmpgetnext and try to
    # find an OID with the prefix in question. The *cache* is working including
    # the X, however.
    if oid[0] != ".":
        if cmk.utils.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        oid = "." + oid

    with suppress(KeyError):
        cached_value = single_oid_cache[oid]
        console.vverbose(
            f"       Using cached OID {oid}: {tty.bold}{tty.green}{cached_value!r}{tty.normal}\n"
        )
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
        console.vverbose(f"{tty.bold}{tty.green}{value!r}{tty.normal}\n")
    else:
        console.vverbose("failed.\n")

    if value is not None:
        decoded_value: SNMPDecodedString | None = backend.config.ensure_str(
            value
        )  # used ensure_str function with different possible encoding arguments
    else:
        decoded_value = value

    single_oid_cache[oid] = decoded_value
    return decoded_value


def walk_for_export(rows: SNMPRowInfo) -> SNMPRowInfoForStoredWalk:
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


def oids_to_walk(options: SNMPWalkOptions | None = None) -> list[OID]:
    if options is None:
        options = {}

    oids = [".1.3.6.1.2.1", ".1.3.6.1.4.1"]  # SNMPv2-SMI::mib-2  # SNMPv2-SMI::enterprises

    if "oids" in options:
        oids = options["oids"]

    elif "extraoids" in options:
        oids += options["extraoids"]

    return sorted(oids, key=lambda x: list(map(int, x.strip(".").split("."))))
