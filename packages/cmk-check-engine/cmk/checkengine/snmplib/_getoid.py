#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from contextlib import suppress

import cmk.ccc.debug
from cmk.ccc.exceptions import MKGeneralException

from ._table import SNMPDecodedString
from ._typedefs import ensure_str, OID, SNMPBackend, SNMPSectionName

logger = logging.getLogger(__name__)


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(
    oid: str,
    *,
    section_name: SNMPSectionName | None = None,
    single_oid_cache: dict[OID, SNMPDecodedString | None],
    backend: SNMPBackend,
    warn_on_empty_value: bool = True,
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
        logger.debug(
            "Using cached OID %(oid)s: %(cached_value)s", {"oid": oid, "cached_value": cached_value}
        )
        return cached_value

    # get_single_oid() can only return a single value. When SNMPv3 is used with multiple
    # SNMP contexts, all contextes will be queried until the first answer is received.
    value = None
    logger.debug("Getting OID %(oid)s", {"oid": oid})
    context_config = backend.config.snmpv3_contexts_of(section_name)
    for context in context_config.contexts:
        try:
            value = backend.get(oid, context=context)

            if value is not None:
                break  # Use first received answer in case of multiple contextes
        except Exception:
            logger.exception(
                "Exception while getting OID %(oid)s from context %(context)s.",
                {"oid": oid, "context": context},
            )
            if cmk.ccc.debug.enabled():
                raise
            value = None

    if value is not None:
        logger.debug("Got OID %(oid)s: %(value)s", {"oid": oid, "value": value})
        decoded_value: SNMPDecodedString | None = ensure_str(
            value, encoding=backend.config.character_encoding
        )  # used ensure_str function with different possible encoding arguments
    else:
        log_func = logger.warning if warn_on_empty_value else logger.debug
        log_func("Getting OID %(oid)s failed.", {"oid": oid})
        decoded_value = value

    single_oid_cache[oid] = decoded_value
    return decoded_value
