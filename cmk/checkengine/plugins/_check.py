#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, NamedTuple, Protocol

from cmk.ccc.hostaddress import HostName
from cmk.ccc.validatedstr import ValidatedString

from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.checkresults import ServiceCheckResult
from cmk.checkengine.fetcher import HostKey
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.sectionparser import ParsedSectionName, Provider

from cmk.agent_based.v2 import CheckResult, DiscoveryResult
from cmk.discover_plugins import PluginLocation

from ._common import LegacyPluginLocation, RuleSetTypeName

type CheckFunction = Callable[..., CheckResult]
type DiscoveryFunction = Callable[..., DiscoveryResult]


class CheckPluginName(ValidatedString):
    MANAGEMENT_PREFIX: Final = "mgmt_"

    def is_management_name(self) -> bool:
        return self._value.startswith(self.MANAGEMENT_PREFIX)

    def create_management_name(self) -> CheckPluginName:
        if self.is_management_name():
            return self
        return CheckPluginName(f"{self.MANAGEMENT_PREFIX}{self._value}")

    def create_basic_name(self) -> CheckPluginName:
        if self.is_management_name():
            return CheckPluginName(self._value[len(self.MANAGEMENT_PREFIX) :])
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


@dataclass(frozen=True)
class ConfiguredService:
    """A service with all information derived from the config"""

    check_plugin_name: CheckPluginName
    item: Item
    description: ServiceName
    parameters: TimespecificParameters
    discovered_parameters: Mapping[str, object]
    labels: Mapping[str, str]
    discovered_labels: Mapping[str, str]
    is_enforced: bool

    def id(self) -> ServiceID:
        return ServiceID(self.check_plugin_name, self.item)

    def sort_key(self) -> ServiceID:
        """Allow to sort services

        Basically sort by id(). Unfortunately we have plugins with *AND* without
        items.
        """
        return ServiceID(self.check_plugin_name, self.item or "")


@dataclass(frozen=True)
class AggregatedResult:
    service: ConfiguredService
    data_received: bool
    result: ServiceCheckResult
    cache_info: tuple[int, int] | None


class _CheckerFunction(Protocol):
    def __call__(
        self,
        host_name: HostName,
        service: ConfiguredService,
        *,
        providers: Mapping[HostKey, Provider],
    ) -> AggregatedResult: ...


@dataclass(frozen=True)
class CheckerPlugin:
    sections: Sequence[ParsedSectionName]
    function: _CheckerFunction
    default_parameters: Mapping[str, object] | None
    ruleset_name: RuleSetName | None
    discovery_ruleset_name: RuleSetName | None
