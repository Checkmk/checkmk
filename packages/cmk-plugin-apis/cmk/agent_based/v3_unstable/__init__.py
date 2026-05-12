#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
New in this version
-------------------

This section lists the most important changes you have to be
aware of when migrating your plug-in to this API version.

Note that changes are expressed in relation to the API version 2.

.. warning::
   This is an **unstable** API version. It may change without notice.

:class:`Metric` is a new class (not an extension of v2)
*********************************************************

:class:`Metric` is a **new dataclass**, not an extension of the v1/v2
:class:`Metric` NamedTuple. It is not a drop-in replacement: existing code
that unpacks or subclasses the v2 :class:`Metric` will need to be updated.

The new class adds a ``lower_levels`` argument — a pair of lower warn/crit
thresholds. This information is used by the graphing system for visualization
and does not affect the service state.

Example::

    Metric("temperature", 42.0, levels=(80, 90), lower_levels=(5, 0))

"""

import string as _string
from collections.abc import Callable as _Callable
from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from dataclasses import dataclass as _dataclass
from typing import Any as _Any
from typing import Final as _Final

from cmk.agent_based.v2 import (
    AgentParseFunction,
    AgentSection,
    all_of,
    any_of,
    Attributes,
    clusterize,
    contains,
    DiscoveryResult,
    endswith,
    equals,
    exists,
    get_average,
    get_rate,
    get_value_store,
    GetRateError,
    HostLabel,
    HostLabelGenerator,
    IgnoreResults,
    IgnoreResultsError,
    InventoryPlugin,
    InventoryResult,
    matches,
    not_contains,
    not_endswith,
    not_equals,
    not_exists,
    not_matches,
    not_startswith,
    OIDBytes,
    OIDCached,
    OIDEnd,
    render,
    Result,
    RuleSetType,
    Service,
    ServiceLabel,
    SimpleSNMPSection,
    SNMPDetectSpecification,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringByteTable,
    StringTable,
    TableRow,
)

from ._check_levels import (
    check_levels,
    FixedLevelsT,
    LevelsT,
    NoLevelsT,
    PredictiveLevelsT,
)
from ._checking_classes import Metric

type _DiscoveryFunction = _Callable[..., DiscoveryResult]
type CheckResult = _Iterable[IgnoreResults | Metric | Result]
type _CheckFunction = _Callable[..., CheckResult]


# A plug-in name must be a non-empty string consisting only
# of letters A-z, digits and the underscore.
_VALID_CHARACTERS: _Final = _string.ascii_letters + "_" + _string.digits


def _validate_name(raw: str) -> str:
    if not isinstance(raw, str):
        raise TypeError(f"Names must be non-empty strings: {raw!r}")
    if not raw:
        raise ValueError(f"Names must be non-empty strings: {raw!r}")

    if invalid := "".join(c for c in raw if c not in _VALID_CHARACTERS):
        raise ValueError(f"Invalid characters in {raw!r}: {invalid!r}")

    return raw


@_dataclass(frozen=True, kw_only=True)
class CheckPlugin:
    name: str
    sections: list[str] | None = None
    service_name: str
    discovery_function: _DiscoveryFunction
    discovery_default_parameters: _Mapping[str, object] | None = None
    discovery_ruleset_name: str | None = None
    discovery_ruleset_type: RuleSetType = RuleSetType.MERGED
    check_function: _CheckFunction
    check_default_parameters: _Mapping[str, object] | None = None
    check_ruleset_name: str | None = None
    cluster_check_function: _CheckFunction | None = None

    def __post_init__(self) -> None:
        _ = _validate_name(self.name)


def entry_point_prefixes() -> _Mapping[
    type[
        AgentSection[_Any]
        | CheckPlugin
        | InventoryPlugin
        | SimpleSNMPSection[_Any, _Any]
        | SNMPSection[_Any, _Any]
    ],
    str,
]:
    """Return the types of plug-ins and their respective prefixes that can be discovered by Checkmk.

    These types can be used to create plug-ins that can be discovered by Checkmk.
    To be discovered, the plug-in must be of one of the types returned by this function and its name
    must start with the corresponding prefix.

    Example:
    ********

    >>> for plugin_type, prefix in entry_point_prefixes().items():
    ...     print(f'{prefix}... = {plugin_type.__name__}(...)')
    snmp_section_... = SimpleSNMPSection(...)
    snmp_section_... = SNMPSection(...)
    agent_section_... = AgentSection(...)
    check_plugin_... = CheckPlugin(...)
    inventory_plugin_... = InventoryPlugin(...)
    """
    return {
        SimpleSNMPSection: "snmp_section_",
        SNMPSection: "snmp_section_",
        AgentSection: "agent_section_",
        CheckPlugin: "check_plugin_",
        InventoryPlugin: "inventory_plugin_",
    }


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
