#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Abstract classes and types."""

from typing import List, Optional, Tuple

from six import ensure_binary, ensure_str

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.paths
import cmk.utils.snmp_cache as snmp_cache
from cmk.utils.exceptions import MKGeneralException, MKSNMPError
from cmk.utils.log import console
from cmk.utils.type_defs import (
    ABCSNMPBackend,
    CheckPluginName,
    ContextName,
    OID,
    RawValue,
    SNMPRowInfo,
)

from ._utils import strip_snmp_value

__all__ = ["StoredWalkSNMPBackend"]


class StoredWalkSNMPBackend(ABCSNMPBackend):
    def get(self, oid, context_name=None):
        # type: (OID, Optional[ContextName]) -> Optional[RawValue]
        walk = self.walk(oid)
        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            return walk[0][1]
        if oid.endswith(".*") and len(walk) > 0:
            return walk[0][1]
        return None

    def walk(self, oid, check_plugin_name=None, table_base_oid=None, context_name=None):
        # type: (OID, Optional[CheckPluginName], Optional[OID], Optional[ContextName]) -> SNMPRowInfo
        if oid.startswith("."):
            oid = oid[1:]

        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            dot_star = True
        else:
            oid_prefix = oid
            dot_star = False

        path = cmk.utils.paths.snmpwalks_dir + "/" + self.config.hostname

        console.vverbose("  Loading %s from %s\n" % (oid, path))

        if snmp_cache.host_cache_contains(self.config.hostname):
            lines = snmp_cache.host_cache_get(self.config.hostname)
        else:
            try:
                lines = open(path).readlines()
            except IOError:
                raise MKSNMPError("No snmpwalk file %s" % path)
            snmp_cache.host_cache_set(self.config.hostname, lines)

        begin = 0
        end = len(lines)
        hit = None
        while end - begin > 0:
            current = (begin + end) // 2
            # skip over values including newlines to the next oid
            while not lines[current].startswith(".") and current < end:
                current += 1
            parts = lines[current].split(None, 1)
            comp = parts[0]
            hit = self._compare_oids(oid_prefix, comp)
            if hit == 0:
                break
            if hit == 1:  # we are too low
                begin = current + 1
            else:
                end = current

        if hit != 0:
            return []  # not found

        rowinfo = self._collect_until(oid, oid_prefix, lines, current, -1)
        rowinfo.reverse()
        rowinfo += self._collect_until(oid, oid_prefix, lines, current + 1, 1)

        if dot_star:
            return [rowinfo[0]]

        return rowinfo

    def _compare_oids(self, a, b):
        # type: (OID, OID) -> int
        aa = self._to_bin_string(a)
        bb = self._to_bin_string(b)
        if len(aa) <= len(bb) and bb[:len(aa)] == aa:
            result = 0
        else:
            result = (aa > bb) - (aa < bb)
        return result

    def _to_bin_string(self, oid):
        # type: (OID) -> Tuple[int, ...]
        try:
            return tuple(map(int, oid.strip(".").split(".")))
        except Exception:
            raise MKGeneralException("Invalid OID %s" % oid)

    def _collect_until(self, oid, oid_prefix, lines, index, direction):
        # type: (OID, OID, List[str], int, int) -> SNMPRowInfo
        rows = []
        # Handle case, where we run after the end of the lines list
        if index >= len(lines):
            if direction > 0:
                return []
            index -= 1
        while True:
            line = lines[index]
            parts = line.split(None, 1)
            o = parts[0]
            if o.startswith('.'):
                o = o[1:]
            if o == oid or o.startswith(oid_prefix + "."):
                if len(parts) > 1:
                    # FIXME: This encoding ping-pong os horrible...
                    value = ensure_str(agent_simulator.process(ensure_binary(parts[1])))
                else:
                    value = ""
                # Fix for missing starting oids
                rows.append(('.' + o, strip_snmp_value(value)))
                index += direction
                if index < 0 or index >= len(lines):
                    break
            else:
                break
        return rows
