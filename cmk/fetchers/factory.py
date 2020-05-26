#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.type_defs import (
    ABCSNMPBackend,
    CheckPluginName,
    ContextName,
    OID,
    RawValue,
    SNMPHostConfig,
    SNMPRowInfo,
)

from .snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from .cee.snmp_backend import inline
except ImportError:
    inline = None  # type: ignore[assignment]

__all__ = ["SNMPBackendFactory"]


class SNMPBackendFactory(object):  # pylint: disable=useless-object-inheritance
    @staticmethod
    def _factory(snmp_config, *, use_cache):
        # type: (SNMPHostConfig, bool) -> ABCSNMPBackend
        if use_cache or snmp_config.is_usewalk_host:
            return StoredWalkSNMPBackend()

        if snmp_config.is_inline_snmp_host:
            return inline.InlineSNMPBackend(snmp_config.record_stats)

        return ClassicSNMPBackend()

    @classmethod
    def get(cls, snmp_config, *, use_cache, oid, context_name=None):
        # type: (SNMPHostConfig, bool, OID, Optional[ContextName]) -> Optional[RawValue]
        return cls._factory(snmp_config, use_cache=use_cache).get(snmp_config,
                                                                  oid=oid,
                                                                  context_name=context_name)

    @classmethod
    def walk(cls,
             snmp_config,
             *,
             use_cache,
             oid,
             context_name=None,
             check_plugin_name=None,
             table_base_oid=None):
        # type: (SNMPHostConfig, bool, OID, Optional[CheckPluginName], Optional[OID], Optional[ContextName]) -> SNMPRowInfo
        return cls._factory(snmp_config,
                            use_cache=use_cache).walk(snmp_config,
                                                      oid=oid,
                                                      context_name=context_name,
                                                      check_plugin_name=check_plugin_name,
                                                      table_base_oid=table_base_oid)
