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

from cmk.utils.type_defs import OIDCached, OIDBytes, OIDEnd

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
    check_levels,
    check_levels_predictive,
    get_rate,
    get_average,
)

from cmk.base.api.agent_based.value_store import get_value_store

from cmk.base.api.agent_based.checking_types import (
    IgnoreResults,
    IgnoreResultsError,
    management_board,
    Metric,
    Parameters,
    Result,
    Service,
    ServiceLabel,
)
from cmk.base.api.agent_based.section_types import SNMPTree
from cmk.base.discovered_labels import HostLabel

from . import register, render, state

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
    "render",
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
    "IgnoreResults",
    "IgnoreResultsError",
    "management_board",
    "Metric",
    "Parameters",  # typing only!
    "Result",
    "Service",
    "ServiceLabel",
    "state",
    # persising values
    "get_value_store",
    # utils
    "check_levels",
    "check_levels_predictive",
    "get_rate",
    "get_average",
]
