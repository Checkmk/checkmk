#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional
import logging

from cmk.snmplib.type_defs import ABCSNMPBackend, SNMPHostConfig

from .snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from .cee.snmp_backend import inline  # type: ignore[import]
except ImportError:
    inline = None  # type: ignore[assignment]

__all__ = ["backend"]

_force_stored_walks = False


def force_stored_walks() -> None:
    global _force_stored_walks
    _force_stored_walks = True


def get_force_stored_walks() -> bool:
    return _force_stored_walks


def backend(snmp_config: SNMPHostConfig,
            logger: logging.Logger,
            *,
            use_cache: Optional[bool] = None) -> ABCSNMPBackend:
    if use_cache is None:
        use_cache = get_force_stored_walks()

    if use_cache or snmp_config.is_usewalk_host:
        return StoredWalkSNMPBackend(snmp_config, logger)

    if snmp_config.is_inline_snmp_host:
        return inline.InlineSNMPBackend(snmp_config, logger)

    return ClassicSNMPBackend(snmp_config, logger)
