#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import SNMPHostConfig

from .snmp_backend import ABCSNMPBackend, ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from .cee.snmp_backend import inline
except ImportError:
    inline = None  # type: ignore[assignment]

__all__ = ["SNMPBackendFactory"]


class SNMPBackendFactory(object):  # pylint: disable=useless-object-inheritance
    @staticmethod
    def factory(snmp_config, *, enforce_stored_walks, record_inline_stats):
        # type: (SNMPHostConfig, bool, bool) -> ABCSNMPBackend
        if enforce_stored_walks or snmp_config.is_usewalk_host:
            return StoredWalkSNMPBackend()

        if inline:
            return inline.InlineSNMPBackend(record_inline_stats)

        return ClassicSNMPBackend()
