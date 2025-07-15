#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Abstract classes and types."""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from cmk.ccc.exceptions import MKException, MKGeneralException, MKSNMPError

from cmk.utils.sectionname import SectionName

from cmk.snmplib import OID, SNMPBackend, SNMPContext, SNMPHostConfig, SNMPRawValue, SNMPRowInfo

from ._utils import strip_snmp_value

__all__ = ["StoredWalkSNMPBackend"]


class StoredWalkSNMPBackend(SNMPBackend):
    def __init__(self, snmp_config: SNMPHostConfig, logger: logging.Logger, path: Path) -> None:
        super().__init__(snmp_config, logger)
        self.path: Final = path
        if not self.path.exists():
            raise MKSNMPError(f"No snmpwalk file {self.path}")

    def get(self, /, oid: OID, *, context: SNMPContext) -> SNMPRawValue | None:
        walk = self.walk(oid, context=context)
        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            return walk[0][1]
        if oid.endswith(".*") and len(walk) > 0:
            return walk[0][1]
        return None

    def walk(
        self,
        /,
        oid: OID,
        *,
        context: SNMPContext,
        section_name: SectionName | None = None,
        table_base_oid: OID | None = None,
    ) -> SNMPRowInfo:
        if oid.startswith("."):
            oid = oid[1:]

        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            dot_star = True
        else:
            oid_prefix = oid
            dot_star = False

        self._logger.debug(f"  Loading {oid}")
        lines = self.read_walk_data()

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
    def read_walk_from_path(path: Path, logger: logging.Logger) -> Sequence[str]:
        logger.debug(f"  Opening {path}")
        lines = []
        with path.open() as f:
            # Sometimes there are newlines in the data of snmpwalks.
            # Append the data to the last OID rather than throwing it away/skipping it.
            for line in f.readlines():
                if line.startswith("."):
                    lines.append(line)
                elif lines:
                    lines[-1] += line
        return lines

    def read_walk_data(self) -> Sequence[str]:
        try:
            return self.read_walk_from_path(self.path, self._logger)
        except OSError:
            raise MKSNMPError(f"No snmpwalk file {self.path}")

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
    def _to_bin_string(oid: OID) -> tuple[int, ...]:
        try:
            return tuple(map(int, oid.strip(".").split(".")))
        except MKException:
            raise
        except Exception:
            raise MKGeneralException(f"Invalid OID {oid}")

    @staticmethod
    def _collect_until(
        oid: OID, oid_prefix: OID, lines: Sequence[str], index: int, direction: int
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
                    value = parts[1]
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
