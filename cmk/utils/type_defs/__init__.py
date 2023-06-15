#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk wide type definitions"""

__all__ = [
    "ValidatedString",
    "AgentRawData",
    "CheckPluginNameStr",
    "ContactgroupName",
    "HostOrServiceConditionRegex",
    "HostOrServiceConditions",
    "HostOrServiceConditionsNegated",
    "HostOrServiceConditionsSimple",
    "Item",
    "LegacyCheckParameters",
    "MetricName",
    "ParametersTypeAlias",
    "RuleSetName",
    "Seconds",
    "SectionName",
    "ServiceAdditionalDetails",
    "ServiceDetails",
    "ServiceName",
    "ServiceState",
    "state_markers",
    "TimeRange",
    "Timestamp",
    "HostName",
    "HostAddress",
]


from cmk.utils.hostaddress import HostAddress, HostName

from ._misc import (
    AgentRawData,
    CheckPluginNameStr,
    ContactgroupName,
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
    HostOrServiceConditionsNegated,
    HostOrServiceConditionsSimple,
    Item,
    LegacyCheckParameters,
    MetricName,
    ParametersTypeAlias,
    Seconds,
    ServiceAdditionalDetails,
    ServiceDetails,
    ServiceName,
    ServiceState,
    state_markers,
    TimeRange,
    Timestamp,
)
from .pluginname import RuleSetName, SectionName, ValidatedString
