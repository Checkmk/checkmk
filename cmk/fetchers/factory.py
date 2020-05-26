#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.type_defs import ABCSNMPBackend, SNMPHostConfig

from .snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from .cee.snmp_backend import inline
except ImportError:
    inline = None  # type: ignore[assignment]

__all__ = ["backend"]

_force_stored_walks = False


def force_stored_walks():
    # type: () -> None
    global _force_stored_walks
    _force_stored_walks = True


def get_force_stored_walks():
    # type: () -> bool
    return _force_stored_walks


def backend(snmp_config, *, use_cache=None):
    # type: (SNMPHostConfig, Optional[bool]) -> ABCSNMPBackend
    if use_cache is None:
        use_cache = get_force_stored_walks()
    if use_cache or snmp_config.is_usewalk_host:
        return StoredWalkSNMPBackend()

    if snmp_config.is_inline_snmp_host:
        return inline.InlineSNMPBackend(snmp_config.record_stats)

    return ClassicSNMPBackend()
