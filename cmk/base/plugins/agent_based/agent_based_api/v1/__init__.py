#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Version 1
---------

.. warning::
    This Version of the **Check API** is still under development
    and may change untils checkmk version 1.7 is released.

    Do not use it (yet) for production code.
    It may change at any time without notice.

"""
# For an explanation of what is what see comments in __all__definition at the end

from cmk.utils.regex import regex
from cmk.snmplib.type_defs import OIDBytes, OIDCached, OIDEnd

from cmk.base.api.agent_based.checking_classes import (
    IgnoreResults,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow
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
    startswith,
    GetRateError,
)
from cmk.base.api.agent_based.value_store import get_value_store
from cmk.base.discovered_labels import HostLabel

from . import register, render, clusterize, type_defs

__all__ = [
    # the order is relevant for the shinx doc!
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
    "regex",
    "register",
    "render",
    "Result",
    "Service",
    "ServiceLabel",
    "SNMPTree",
    "State",
    "TableRow",
    "type_defs",
    "GetRateError",
]
