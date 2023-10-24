#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.prism import load_json

Section = dict[str, Any]


def parse_prism_host(string_table: StringTable) -> Section:
    return load_json(string_table)


register.agent_section(
    name="prism_host",
    parse_function=parse_prism_host,
)
