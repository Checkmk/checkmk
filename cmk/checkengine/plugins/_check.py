#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, NamedTuple, Protocol

from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.validatedstr import ValidatedString

from cmk.checkengine.checkresults import ServiceCheckResult
from cmk.checkengine.fetcher import HostKey
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.sectionparser import ParsedSectionName, Provider


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
