#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
New in this version
-------------------

This section lists the most important changes you have to be
aware of when migrating your plug-in to this API version.

Note that changes are expressed in relation to the API version 1.

You can find a script in `doc/treasures/migration_helpers/` that
will do most of the migration for you. This script is not officially
supported, so use at your own risk.

`type_defs` module is dissolved
*******************************
The `type_defs` module has been dissolved.
All types are now directly imported from the `v2` module.

`check_levels` signature changed
********************************

The new :func:`check_levels` function is designed to work well with the
levels elements from the new `rulesets API v1`.
These can be found in :mod:`cmk.rulesets.v1.form_specs`.

The types of the arguments have been added to the API and can be found in
:mod:`cmk.agent_based.v2`.


Registration is replaced by a discovery approach
************************************************

This is the main reason for the introduction of this new API version.
Plugins are no longer registered during import, but only created and
picked up later by the backend.
To realize this, we introduced four new classes:

* :class:`AgentSection` replacing :func:`register.agent_section`
* :class:`SimpleSNMPSection` and :class:`SNMPSection` replacing :func:`register.snmp_section`
* :class:`CheckPlugin` replacing :func:`register.check_plugin`
* :class:`InventoryPlugin` replacing :func:`register.inventory_plugin`

The arguments of these have barely changed (see next paragraph), resulting
in easy to automate changes (see
`this commit <https://github.com/Checkmk/checkmk/commit/6e7c9010ae370b30be904c6589ccdc75498482f7>`_
for instance).

Changed arguments and validation for Agent and SNMP sections
************************************************************

We slightly adopted the arguments to the above-mentioned `Section` classes.
We now favor type annotations over runtime validation.
To get slightly easier type annotations, `parse_function` is no longer optional.

Removed wrapper for regex creation :func:`regex`
************************************************

This has been removed. See its documentation for the reasoning.
You can use pythons :func:`re.compile` as drop-in replacement.

Added rendering function :func:`time_offset`
********************************************

On popular demand we add a function to render a number of seconds that might be negative.

"""

from cmk.agent_based.v1 import (
    all_of,
    any_of,
    Attributes,
    contains,
    endswith,
    equals,
    exists,
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
from cmk.agent_based.v1._detection import SNMPDetectSpecification  # sorry
from cmk.agent_based.v1.register import RuleSetType
from cmk.agent_based.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    HostLabelGenerator,
    InventoryResult,
)

from . import clusterize, render
from ._check_levels import check_levels, FixedLevelsT, LevelsT, NoLevelsT, PredictiveLevelsT
from ._get_average import get_average
from ._plugins import (
    AgentParseFunction,
    AgentSection,
    CheckPlugin,
    entry_point_prefixes,
    InventoryPlugin,
    SimpleSNMPSection,
    SNMPSection,
)

StringTable = list[list[str]]
StringByteTable = list[list[str | list[int]]]


__all__ = [
    "entry_point_prefixes",
    # the order is relevant for the sphinx doc!
    "AgentSection",
    "AgentParseFunction",
    "CheckPlugin",
    "SNMPSection",
    "SimpleSNMPSection",
    "SNMPDetectSpecification",
    "InventoryPlugin",
    "CheckResult",
    "DiscoveryResult",
    "HostLabelGenerator",
    "InventoryResult",
    "StringByteTable",
    "StringTable",
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
    "LevelsT",
    "FixedLevelsT",
    "NoLevelsT",
    "PredictiveLevelsT",
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
    "GetRateError",
]
