#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""API for agent based plugins
"""
# For an explanation of what is what see comments in __all__definition at the end

from cmk.base.api.agent_based.utils import (
    parse_string_table,
    all_of,
    any_of,
    contains,
    startswith,
    endswith,
    matches,
    equals,
    exists,
    not_contains,
    not_startswith,
    not_endswith,
    not_matches,
    not_equals,
    not_exists,
    get_rate,
    get_average,
)

from cmk.base.api.agent_based.value_store import get_value_store

from cmk.base.api.agent_based.section_types import SNMPTree, OIDEnd
from cmk.base.discovered_labels import HostLabel
from cmk.base.snmp_utils import OIDCached, OIDBytes

from . import register, state

__all__ = [
    # register functions
    "register",
    # SECTION related
    "SNMPTree",
    "OIDEnd",
    "OIDCached",
    "OIDBytes",
    "HostLabel",
    # utils
    "parse_string_table",
    # detect spec helper
    "all_of",
    "any_of",
    "contains",
    "startswith",
    "endswith",
    "matches",
    "equals",
    "exists",
    "not_contains",
    "not_startswith",
    "not_endswith",
    "not_matches",
    "not_equals",
    "not_exists",
    # CHECKING related
    "state",
    # persising values
    "get_value_store",
    # utils
    "get_rate",
    "get_average",
]
