#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.mobileiron import parse_mobileiron, parse_mobileiron_source_host

register.agent_section(
    name="mobileiron_section",
    parse_function=parse_mobileiron,
)

register.agent_section(
    name="mobileiron_source_host",
    parse_function=parse_mobileiron_source_host,
)
