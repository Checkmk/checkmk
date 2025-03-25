#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import StringTable

# this is the truth, but Sequence/tuple would be more desirable than a list.
Section = tuple[int | None, Mapping[str, list[list[str]]]]


def parse_db2_dbs(string_table: StringTable) -> Section:
    current_instance = None
    dbs: dict[str, list[list[str]]] = {}
    global_timestamp = None
    for line in string_table:
        if line[0].startswith("TIMESTAMP") and not current_instance:
            global_timestamp = int(line[1])
            continue

        if line[0].startswith("[[["):
            current_instance = line[0][3:-3]
            dbs[current_instance] = []
        elif current_instance:
            dbs[current_instance].append(line)

    return global_timestamp, dbs
