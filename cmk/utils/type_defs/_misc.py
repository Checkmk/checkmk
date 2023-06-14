#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import sys
from collections.abc import Container, Mapping
from dataclasses import dataclass
from typing import Any, Literal, NewType, TypeAlias, TypedDict

__all__ = [
    "ServiceName",
    "ServicegroupName",
    "ContactgroupName",
    "AgentRawData",
    "HostOrServiceConditionRegex",
    "HostOrServiceConditionsSimple",
    "HostOrServiceConditionsNegated",
    "HostOrServiceConditions",
    "CheckPluginNameStr",
    "ActiveCheckPluginName",
    "Item",
    "Seconds",
    "Timestamp",
    "TimeRange",
    "ServiceState",
    "ServiceDetails",
    "ServiceAdditionalDetails",
    "MetricName",
    "MetricTuple",
    "ClusterMode",
    "LegacyCheckParameters",
    "ParametersTypeAlias",
    "DiscoveryResult",
    "SNMPDetectBaseType",
    "EvalableFloat",
    "EVERYTHING",
    "state_markers",
    "ExitSpec",
    "InfluxDBConnectionSpec",
]

ServiceName = str
ServicegroupName = str
ContactgroupName = str


AgentRawData = NewType("AgentRawData", bytes)

HostOrServiceConditionRegex = TypedDict(
    "HostOrServiceConditionRegex",
    {"$regex": str},
)
HostOrServiceConditionsSimple = list[HostOrServiceConditionRegex | str]
HostOrServiceConditionsNegated = TypedDict(
    "HostOrServiceConditionsNegated",
    {"$nor": HostOrServiceConditionsSimple},
)

HostOrServiceConditions = (
    HostOrServiceConditionsSimple | HostOrServiceConditionsNegated
)  # TODO: refine type

CheckPluginNameStr = str
ActiveCheckPluginName = str
Item = str | None


Seconds = int
Timestamp = int
TimeRange = tuple[int, int]

ServiceState = int
ServiceDetails = str
ServiceAdditionalDetails = str

MetricName = str
MetricTuple = tuple[
    MetricName,
    float,
    float | None,
    float | None,
    float | None,
    float | None,
]

JsonSerializable: TypeAlias = (
    dict[str, "JsonSerializable"] | list["JsonSerializable"] | str | int | float | bool | None
)


ClusterMode = Literal["native", "failover", "worst", "best"]

LegacyCheckParameters = None | Mapping[Any, Any] | tuple[Any, ...] | list[Any] | str | int | bool
ParametersTypeAlias = Mapping[str, Any]  # Modification may result in an incompatible API change.


@dataclass
class DiscoveryResult:
    # TODO(ml): Move to `autodiscovery` when the dependency to
    #           `cmk.base.config` has been inverted.
    self_new: int = 0
    self_removed: int = 0
    self_kept: int = 0
    self_total: int = 0
    self_new_host_labels: int = 0
    self_total_host_labels: int = 0
    clustered_new: int = 0
    clustered_old: int = 0
    clustered_vanished: int = 0
    clustered_ignored: int = 0

    # None  -> No error occured
    # ""    -> Not monitored (disabled host)
    # "..." -> An error message about the failed discovery
    error_text: str | None = None

    # An optional text to describe the services changed by the operation
    diff_text: str | None = None


# This def is used to keep the API-exposed object in sync with our
# implementation.
SNMPDetectBaseType = list[list[tuple[str, str, bool]]]


class EvalableFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""

    def __str__(self) -> str:
        return super().__repr__()

    def __repr__(self) -> str:
        if self > sys.float_info.max:
            return "1e%d" % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return "-1e%d" % (sys.float_info.max_10_exp + 1)
        return super().__repr__()


class _Everything(Container[Any]):
    def __contains__(self, other: object) -> bool:
        return True


EVERYTHING = _Everything()

# Symbolic representations of states in plugin output
# TODO(ml): Should probably be of type enum::int -> str
state_markers = ("", "(!)", "(!!)", "(?)")


class ExitSpec(TypedDict, total=False):
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: list[tuple[str, int]]
    restricted_address_mismatch: int
    legacy_pull_mode: int


InfluxDBConnectionSpec = dict[str, Any]
