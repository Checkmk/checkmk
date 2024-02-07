#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pydantic

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, type_defs

from cmk.plugins.lib import uptime


class Uptime(pydantic.BaseModel):
    """section: prometheus_uptime_v1"""

    seconds: float


def parse(string_table: type_defs.StringTable) -> uptime.Section:
    """
    >>> parse([['{"seconds": 2117}']])
    Section(uptime_sec=2117.0, message=None)
    >>> parse([['{"seconds": 5666.380061}']])
    Section(uptime_sec=5666.380061, message=None)
    """
    seconds = Uptime.model_validate_json(string_table[0][0]).seconds
    return uptime.Section(uptime_sec=seconds, message=None)


register.agent_section(
    name="prometheus_uptime_v1",
    parse_function=parse,
    parsed_section_name="uptime",
)
