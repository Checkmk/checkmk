#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.plugins.lib.prism import load_json

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, Any]


def parse_prism_vm(string_table: StringTable) -> Section:
    return load_json(string_table)


register.agent_section(
    name="prism_vm",
    parse_function=parse_prism_vm,
)
