#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.megaraid import expand_abbreviation

from .agent_based_api.v1 import register


class StorcliVDrive(NamedTuple):
    raid_type: str
    state: str
    access: str
    consistent: bool


StorcliVDrivesSection = Mapping[str, StorcliVDrive]


def parse_storcli_vdrives(string_table: StringTable) -> StorcliVDrivesSection:

    section: MutableMapping[str, StorcliVDrive] = {}

    controller_num = 0
    separator_count = 0

    for line in string_table:
        if line[0].startswith("-----"):
            separator_count += 1
        elif separator_count == 2:
            dg_vd, raid_type, rawstate, access, consistent = line[:5]
            section[f"C{controller_num}.{dg_vd}"] = StorcliVDrive(
                raid_type=raid_type,
                state=expand_abbreviation(rawstate),
                access=access,
                consistent=consistent == "Yes",
            )

        if separator_count == 3:
            # each controller has 3 separators, reset count and continue
            separator_count = 0
            controller_num += 1

    return section


register.agent_section(
    name="storcli_vdrives",
    parse_function=parse_storcli_vdrives,
)
