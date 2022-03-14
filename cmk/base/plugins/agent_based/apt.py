#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional, Sequence

from .agent_based_api.v1 import regex, register
from .agent_based_api.v1.type_defs import StringTable
from .utils.apt import ESM_ENABLED, ESM_NOT_ENABLED, NOTHING_PENDING_FOR_INSTALLATION

DEBIAN_SEC = "Debian-Security"
_SEC_REGEX = regex(f"^[^\\(]*\\(.* ({DEBIAN_SEC}:|Ubuntu[^/]*/[^/]*-\\bsecurity\\b)")


class Section(NamedTuple):
    updates: Sequence[str]
    removals: Sequence[str]
    sec_updates: Sequence[str]
    no_esm_support: bool = False


def _trim_esm_enabled_warning(string_table: StringTable) -> StringTable:
    """Trims infra warning of the format:
    *The following packages could receive security updates with UA Infra: ESM service enabled:
    libglib2.0-data libglib2.0-0
    Learn more about UA Infra: ESM service for Ubuntu 16.04 at https://ubuntu.com/16-04

    Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
    applicable law.
    """
    if ESM_ENABLED in string_table[0][0]:
        return string_table[5:]
    return string_table


# Check that the apt section is in valid format of mk_apt plugin and not
# from the apt agent plugin which can be found on the Checkmk exchange.
def _data_is_valid(string_table: StringTable) -> bool:
    if not string_table:
        return False

    first_line = string_table[0]
    if len(first_line) != 1:
        return False

    if first_line[0] == NOTHING_PENDING_FOR_INSTALLATION:
        return True

    # Newer versions of apt display something like
    # 3 esm-infra security updates
    # 10 standard security updates
    # 1 standard security update
    # We also observed kernel security updates on debian, the version can then also be found
    # in the second line
    if any(s in first_line[0] for s in ("security update", DEBIAN_SEC)):
        first_line = string_table[1]

    parts = first_line[0].split()
    if len(parts) < 3:
        return False

    action = parts[0]
    version = parts[2]
    return action in ("Inst", "Remv") and version.startswith("[") and version.endswith("]")


def _is_security_update(update: str) -> bool:
    """Is the update a security update
    >>> _is_security_update("Inst tzdata (2021e-0ubuntu0.16.04+esm1 UbuntuESM:16.04/xenial-infra-security [all])")
    True
    >>> _is_security_update("Inst linux-image-4.19.0-19-amd64 (4.19.232-1 Debian-Security:10/oldstable [amd64])")
    True
    """
    return bool(_SEC_REGEX.match(update))


def parse_apt(string_table: StringTable) -> Optional[Section]:
    if ESM_NOT_ENABLED in string_table[0][0]:
        return Section(updates=[], removals=[], sec_updates=[], no_esm_support=True)

    trimmed_string_table = _trim_esm_enabled_warning(string_table)

    if not _data_is_valid(trimmed_string_table):
        return None

    updates = []
    removals = []
    sec_updates = []

    for line in trimmed_string_table:
        if not line[0].startswith(("Inst", "Remv")):
            continue
        _inst, packet, _version = line[0].split(None, 2)
        if line[0].startswith("Remv"):
            removals.append(packet)
        elif _is_security_update(line[0]):
            sec_updates.append(packet)
        else:
            updates.append(packet)

    return Section(
        updates,
        removals,
        sec_updates,
    )


register.agent_section(
    name="apt",
    parse_function=parse_apt,
)
