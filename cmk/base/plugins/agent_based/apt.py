#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional, Sequence

from .agent_based_api.v1 import register, regex
from .agent_based_api.v1.type_defs import StringTable

from .utils.apt import NOTHING_PENDING_FOR_INSTALLATION

_SEC_REGEX = regex("^[^\\(]*\\(.* (Debian-Security:|Ubuntu:[^/]*/[^-]*-security)")


class Section(NamedTuple):
    updates: Sequence[str]
    removals: Sequence[str]
    sec_updates: Sequence[str]


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
    if "security update" in first_line[0]:
        first_line = string_table[1]

    parts = first_line[0].split()
    if len(parts) < 3:
        return False

    action = parts[0]
    version = parts[2]
    return action in ('Inst', 'Remv') and version.startswith("[") and version.endswith("]")


def parse_apt(string_table: StringTable) -> Optional[Section]:
    if not _data_is_valid(string_table):
        return None

    updates = []
    removals = []
    sec_updates = []

    for line in string_table:
        if not line[0].startswith(("Inst", "Remv")):
            continue
        _inst, packet, _version = line[0].split(None, 2)
        if line[0].startswith("Remv"):
            removals.append(packet)
        elif _SEC_REGEX.match(line[0]):
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
