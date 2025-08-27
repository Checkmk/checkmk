#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Final, NamedTuple

from cmk.agent_based.v2 import CheckResult, DiscoveryResult
from cmk.discover_plugins import PluginLocation
from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import Item

from ._common import LegacyPluginLocation, RuleSetTypeName
from ._sections import ParsedSectionName

type CheckFunction = Callable[..., CheckResult]
type DiscoveryFunction = Callable[..., DiscoveryResult]


class CheckPluginName(str):
    MANAGEMENT_PREFIX: Final = "mgmt_"

    def is_management_name(self) -> bool:
        return self.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> CheckPluginName:
        if self.is_management_name():
            return self
        return CheckPluginName(f"{self.MANAGEMENT_PREFIX}{self}")

    def create_basic_name(self) -> CheckPluginName:
        if self.is_management_name():
            return CheckPluginName(self[len(self.MANAGEMENT_PREFIX) :])
        return self


class CheckPlugin(NamedTuple):
    name: CheckPluginName
    sections: list[ParsedSectionName]
    service_name: str
    discovery_function: DiscoveryFunction
    discovery_default_parameters: Mapping[str, object] | None
    discovery_ruleset_name: RuleSetName | None
    discovery_ruleset_type: RuleSetTypeName
    check_function: CheckFunction
    check_default_parameters: Mapping[str, object] | None
    check_ruleset_name: RuleSetName | None
    cluster_check_function: CheckFunction | None
    location: PluginLocation | LegacyPluginLocation


class ServiceID(NamedTuple):
    name: CheckPluginName
    item: Item
