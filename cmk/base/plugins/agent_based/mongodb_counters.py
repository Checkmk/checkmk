#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, MutableMapping

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable

# <<<mongodb_counters>>>
# opcounters getmore 477157
# opcounters insert 133537
# opcounters update 325682
# opcounters command 4600490
# opcounters query 875935
# opcounters delete 105560
# opcountersRepl getmore 0
# opcountersRepl insert 32595
# opcountersRepl update 1147
# opcountersRepl command 1
# opcountersRepl query 0
# opcountersRepl delete 31786

Section = Mapping[str, Mapping[str, int]]


def parse_mongodb_counters(string_table: StringTable) -> Section:
    parsed: MutableMapping[str, MutableMapping[str, int]] = {}
    for line in string_table:
        document, counter_name, *counter_values = line

        # the documentation says that this should only happen from 5.1 onwards:
        # https://docs.mongodb.com/v5.1/reference/command/serverStatus/#mongodb-serverstatus-serverstatus.opcounters.deprecated
        # however, according to SUP-8433, this can also happen with earlier version (4.2.15)
        if counter_name == "deprecated":
            continue

        parsed.setdefault(document, {})[counter_name] = int(counter_values[0])
    return parsed


register.agent_section(
    name="mongodb_counters",
    parse_function=parse_mongodb_counters,
)
