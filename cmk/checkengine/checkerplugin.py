#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.checkresults import ServiceCheckResult
from cmk.checkengine.fetcher import HostKey
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.plugins import CheckPluginName, ParsedSectionName, ServiceID
from cmk.checkengine.sectionparser import Provider
from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import Item, ServiceName


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
