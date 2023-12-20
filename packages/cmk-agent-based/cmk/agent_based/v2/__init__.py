#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
New in this version
-------------------

This section lists the most important changes you have to be
aware of when migrating your plugin to this API version.

Note that changes are expressed in relation to the API version 1.

You can find a script in `doc/treasures/migration_helpers/` that
will do most of the migration for you.


`check_levels` renamed to `check_levels_fixed`
**********************************************

This renaming allows us to provide a new `check_levels` function,
that is particularly designed to work well with the `Levels` element
from the new `rulesets API v1`.


Registration is replaced by a discovery approach
************************************************

This is the main reason for the introduction of this new API version.
Plugins are no longer registered during import, but only created and
picked up later by the backend.
To realize this, we introduced four new classes:
* :class:`AgentSection` replacing :func:`register.agent_section`
* :class:`SimpleSNMPSection` and :class:`SNMPSection` replacing :func:`register.snmp_section`
* :class:`Checkplugin` replacing :func:`register.check_plugin`
* :class:`InventoryPlugin` replacing :func:`register.inventory_plugin`

The arguments of these have barely changed (see next paragraph), resulting
in easy to automate changes (see
`this commit <https://github.com/Checkmk/checkmk/commit/6e7c9010ae370b30be904c6589ccdc75498482f7>`_
for instance).

Changed arguments and validation for Agent and SNMP sections
************************************************************

We slightly adopted the arguments to the above mentioned `Section` classes.
We now favor type annotations over runtime validation.
To get slightly easier type annotations, `parse_function` is no longer optional.

Removed wrapper for regex creation :func:`regex`
************************************************

This has been removed. See its documentation for the reasoning.
You can use pythons :func:`re.compile` as drop-in replacement.

"""
# pylint: disable=duplicate-code

from ..v1 import all_of, any_of, Attributes
from ..v1 import check_levels as check_levels_fixed
from ..v1 import (
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
    "check_levels_fixed",
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
