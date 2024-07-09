#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_redis_info(string_table: StringTable) -> Section:
    parsed: dict = {}
    instance = {}
    inst_section = {}
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            name, host, port = line[0][3:-3].split("|")
            instance = parsed.setdefault(
                name.replace(";", ":"),
                {
                    "host": host,
                    "port": port,
                },
            )
            continue

        if not instance:
            continue

        if line[0] == "error":
            instance[line[0]] = ": ".join(line[1:])
            continue

        if line[0].startswith("#"):
            inst_section = instance.setdefault(line[0].split()[-1], {})
            continue

        raw_value = ":".join(line[1:])
        try:
            value: int | float = int(raw_value)
        except ValueError:
            pass
        else:
            inst_section[line[0]] = value
            continue

        try:
            value = float(raw_value)
        except ValueError:
            pass
        else:
            inst_section[line[0]] = value
            continue

        inst_section[line[0]] = raw_value

    return parsed


agent_section_redis_info = AgentSection(name="redis_info", parse_function=parse_redis_info)
