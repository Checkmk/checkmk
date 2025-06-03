#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from contextlib import suppress

import cmk.ccc.cleanup
import cmk.ccc.debug
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.sectionname import SectionName

from ._table import SNMPDecodedString
from ._typedefs import ensure_str, OID, SNMPBackend


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(
    oid: str,
    *,
    section_name: SectionName | None = None,
    single_oid_cache: dict[OID, SNMPDecodedString | None],
    backend: SNMPBackend,
    log: Callable[[str], None],
) -> SNMPDecodedString | None:
    # The OID can end with ".*". In that case we do a snmpgetnext and try to
    # find an OID with the prefix in question. The *cache* is working including
    # the X, however.
    if oid[0] != ".":
        if cmk.ccc.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        oid = "." + oid

    with suppress(KeyError):
        cached_value = single_oid_cache[oid]
        log(f"       Using cached OID {oid}: {tty.bold}{tty.green}{cached_value!r}{tty.normal}")
        return cached_value

    # get_single_oid() can only return a single value. When SNMPv3 is used with multiple
    # SNMP contexts, all contextes will be queried until the first answer is received.
    value = None
    log(f"       Getting OID {oid}...")
    context_config = backend.config.snmpv3_contexts_of(section_name)
    for context in context_config.contexts:
        try:
            value = backend.get(oid, context=context)

            if value is not None:
                break  # Use first received answer in case of multiple contextes
        except Exception:
            if cmk.ccc.debug.enabled():
                raise
            value = None

    if value is not None:
        log(f"       Got OID {oid}: {tty.bold}{tty.green}{value!r}{tty.normal}")
    else:
        log(f"       Getting OID {oid} failed.")

    if value is not None:
        decoded_value: SNMPDecodedString | None = ensure_str(
            value, encoding=backend.config.character_encoding
        )  # used ensure_str function with different possible encoding arguments
    else:
        decoded_value = value

    single_oid_cache[oid] = decoded_value
    return decoded_value
