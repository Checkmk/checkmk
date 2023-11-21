#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Agent based API v2

New/changed:

  * The registration is replaced by a discovery approach
  * Agent/SNMP sections:
    * parse_function is no longer optional
    * no runtime validation of the parse function - respect the type annotations!

"""
# pylint: disable=duplicate-code

from ..v1 import (
    all_of,
    any_of,
    Attributes,
    check_levels,
    check_levels_predictive,
    contains,
    endswith,
    equals,
    exists,
    get_average,
    get_rate,
    get_value_store,
    GetRateError,
    HostLabel,
    IgnoreResults,
    IgnoreResultsError,
    matches,
    Metric,
    not_contains,
    not_endswith,
    not_equals,
    not_exists,
    not_matches,
    not_startswith,
    OIDBytes,
    OIDCached,
    OIDEnd,
    Result,
    Service,
    ServiceLabel,
    SNMPTree,
    startswith,
    State,
    TableRow,
)
from ..v1._detection import SNMPDetectSpecification  # sorry
from ..v1.register import RuleSetType
from . import clusterize, render, type_defs
from ._plugins import AgentSection, CheckPlugin, InventoryPlugin, SimpleSNMPSection, SNMPSection

__all__ = [
    # the order is relevant for the sphinx doc!
    "AgentSection",
    "CheckPlugin",
    "SNMPSection",
    "SimpleSNMPSection",
    "SNMPDetectSpecification",
    "InventoryPlugin",
    # begin with section stuff
    "all_of",
    "any_of",
    "exists",
    "equals",
    "startswith",
    "endswith",
    "contains",
    "matches",
    "not_exists",
    "not_equals",
    "not_contains",
    "not_endswith",
    "not_matches",
    "not_startswith",
    "Attributes",
    "check_levels",
    "check_levels_predictive",
    "clusterize",
    "get_average",
    "get_rate",
    "get_value_store",
    "HostLabel",
    "IgnoreResults",
    "IgnoreResultsError",
    "Metric",
    "OIDBytes",
    "OIDCached",
    "OIDEnd",
    "render",
    "Result",
    "RuleSetType",
    "Service",
    "ServiceLabel",
    "SNMPTree",
    "State",
    "TableRow",
    "type_defs",
    "GetRateError",
]
