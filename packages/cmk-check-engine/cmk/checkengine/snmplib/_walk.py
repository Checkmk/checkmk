#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from ._typedefs import OID, SNMPBackend, SNMPContext, SNMPRawValue, SNMPRowInfo

SNMPRowInfoForStoredWalk = list[tuple[OID, str]]
SNMPWalkOptions = dict[str, list[OID]]


def walk_for_export(rows: SNMPRowInfo) -> SNMPRowInfoForStoredWalk:
    def should_be_encoded(v: SNMPRawValue) -> bool:
        return not all(32 <= c <= 127 for c in bytearray(v))

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


def walk_all_contexts_for_export(
    oid: OID,
    *,
    backend: SNMPBackend,
    on_error: Callable[[OID, SNMPContext, Exception], None],
) -> SNMPRowInfoForStoredWalk:
    """Walk the OID in every SNMPv3 context configured for the host

    OIDs returned by several contexts are kept once. A context whose walk fails
    is passed to `on_error` and skipped; the rows of the other contexts are kept.
    """
    seen: set[OID] = set()
    rows: SNMPRowInfoForStoredWalk = []
    for context in backend.config.snmpv3_contexts_of(None).contexts:
        try:
            context_rows = walk_for_export(backend.walk(oid, context=context))
        except Exception as e:
            on_error(oid, context, e)
            continue
        for row_oid, value in context_rows:
            if row_oid not in seen:
                seen.add(row_oid)
                rows.append((row_oid, value))
    return rows
