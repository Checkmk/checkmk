#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import register
from .utils.azure import parse_resources

# This section contains data for both the postgresql and mysql checks
register.agent_section(
    name="azure_servers",
    parse_function=parse_resources,
)
