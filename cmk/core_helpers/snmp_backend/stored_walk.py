#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Abstract classes and types."""

from typing import List, Optional, Tuple

import cmk.utils.agent_simulator as agent_simulator
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException, MKSNMPError
from cmk.utils.log import console
from cmk.utils.type_defs import AgentRawData, SectionName

import cmk.snmplib.snmp_cache as snmp_cache
from cmk.snmplib.type_defs import OID, SNMPBackend, SNMPContextName, SNMPRawValue, SNMPRowInfo

from ._utils import strip_snmp_value

__all__ = ["StoredWalkSNMPBackend"]


class StoredWalkSNMPBackend(SNMPBackend):
    def get(
        self, oid: OID, context_name: Optional[SNMPContextName] = None
    ) -> Optional[SNMPRawValue]:
        walk = self.walk(oid)
        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            return walk[0][1]
        if oid.endswith(".*") and len(walk) > 0:
            return walk[0][1]
        return None

    def walk(
        self,
        oid: OID,
        section_name: Optional[SectionName] = None,
        table_base_oid: Optional[OID] = None,
        context_name: Optional[SNMPContextName] = None,
    ) -> SNMPRowInfo:
        if oid.startswith("."):
            oid = oid[1:]

        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            dot_star = True
        else:
            oid_prefix = oid
            dot_star = False

        host_cache = snmp_cache.host_cache()
        try:
            lines = host_cache[self.config.hostname]
        except KeyError:
            path = cmk.utils.paths.snmpwalks_dir + "/" + self.config.hostname
            console.vverbose("  Loading %s from %s\n" % (oid, path))
            try:
                lines = StoredWalkSNMPBackend.read_walk_data(path)
            except IOError:
                raise MKSNMPError("No snmpwalk file %s" % path)
            host_cache[self.config.hostname] = lines

        begin = 0
        end = len(lines)
        hit = None
        while end - begin > 0:
            current = (begin + end) // 2
            parts = lines[current].split(None, 1)
            comp = parts[0]
            hit = StoredWalkSNMPBackend._compare_oids(oid_prefix, comp)
            if hit == 0:
                break
            if hit == 1:  # we are too low
                begin = current + 1
            else:
                end = current

        if hit != 0:
            return []  # not found

        rowinfo = StoredWalkSNMPBackend._collect_until(oid, oid_prefix, lines, current, -1)
        rowinfo.reverse()
        rowinfo += StoredWalkSNMPBackend._collect_until(oid, oid_prefix, lines, current + 1, 1)

        if dot_star:
            return [rowinfo[0]]

        return rowinfo

    @staticmethod
    def read_walk_data(path: str):
        lines = []
        with open(path) as f:
            # Sometimes there are newlines in the data of snmpwalks.
            # Append the data to the last OID rather than throwing it away/skipping it.
            for line in f.readlines():
                if line.startswith("."):
                    lines.append(line)
                elif lines:
                    lines[-1] += line
        return lines

    @staticmethod
    def _compare_oids(a: OID, b: OID) -> int:
        aa = StoredWalkSNMPBackend._to_bin_string(a)
        bb = StoredWalkSNMPBackend._to_bin_string(b)
        if len(aa) <= len(bb) and bb[: len(aa)] == aa:
            result = 0
        else:
            result = (aa > bb) - (aa < bb)
        return result

    @staticmethod
    def _to_bin_string(oid: OID) -> Tuple[int, ...]:
        try:
            return tuple(map(int, oid.strip(".").split(".")))
        except Exception:
            raise MKGeneralException("Invalid OID %s" % oid)

    @staticmethod
    def _collect_until(
        oid: OID, oid_prefix: OID, lines: List[str], index: int, direction: int
    ) -> SNMPRowInfo:
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
            if o.startswith("."):
                o = o[1:]
            if o == oid or o.startswith(oid_prefix + "."):
                if len(parts) > 1:
                    # FIXME: This encoding ping-pong os horrible...
                    value = agent_simulator.process(
                        AgentRawData(
                            parts[1].encode(),
                        ),
                    ).decode()
                else:
                    value = ""
                # Fix for missing starting oids
                rows.append(("." + o, strip_snmp_value(value)))
                index += direction
                if index < 0 or index >= len(lines):
                    break
            else:
                break
        return rows
