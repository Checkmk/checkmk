#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Version 0
---------

.. warning::
    This Version of the **Check API** is only used during development
    and should not be used for production code.

    It may change at any time without notice.

"""
# For an explanation of what is what see comments in __all__definition at the end

from cmk.snmplib.type_defs import OIDBytes, OIDCached, OIDEnd

from cmk.base.api.agent_based.checking_classes import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    ServiceLabel,
    state,
)
from cmk.base.api.agent_based.type_defs import SNMPTree
from cmk.base.api.agent_based.utils import (
    all_of,
    any_of,
    check_levels,
    check_levels_predictive,
    contains,
    endswith,
    equals,
    exists,
    get_average,
    get_rate,
    matches,
    not_contains,
    not_endswith,
    not_equals,
    not_exists,
    not_matches,
    not_startswith,
    parse_to_string_table,
    startswith,
)
from cmk.base.api.agent_based.value_store import get_value_store
from cmk.base.discovered_labels import HostLabel

from . import register, render, clusterize, type_defs

__all__ = [
    "all_of",
    "any_of",
    "check_levels",
    "check_levels_predictive",
    "clusterize",
    "contains",
    "endswith",
    "equals",
    "exists",
    "get_average",
    "get_rate",
    "get_value_store",
    "HostLabel",
    "IgnoreResults",
    "IgnoreResultsError",
    "matches",
    "Metric",
    "not_contains",
    "not_endswith",
    "not_equals",
    "not_exists",
    "not_matches",
    "not_startswith",
    "OIDBytes",
    "OIDCached",
    "OIDEnd",
    "parse_to_string_table",
    "register",
    "render",
    "Result",
    "Service",
    "ServiceLabel",
    "SNMPTree",
    "startswith",
    "state",
    "type_defs",
]
