#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Optional

from cmk.snmplib.type_defs import SNMPBackend, SNMPBackendEnum, SNMPHostConfig

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


def backend(
    snmp_config: SNMPHostConfig, logger: logging.Logger, *, use_cache: Optional[bool] = None
) -> SNMPBackend:
    if use_cache is None:
        use_cache = get_force_stored_walks()

    if use_cache or snmp_config.is_usewalk_host:
        return StoredWalkSNMPBackend(snmp_config, logger)

    if inline and snmp_config.snmp_backend == SNMPBackendEnum.INLINE:
        return inline.InlineSNMPBackend(snmp_config, logger)

    if snmp_config.snmp_backend == SNMPBackendEnum.CLASSIC:
        return ClassicSNMPBackend(snmp_config, logger)

    raise NotImplementedError(f"Unknown SNMP backend: {snmp_config.snmp_backend}")
