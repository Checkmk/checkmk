#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
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

__all__ = [
    "AggregatedResult",
    "CheckPlugin",
    "CheckPluginName",
    "ConfiguredService",
    "ServiceConfigurer",
    "ServiceID",
    "AutocheckEntryProtocol",
]


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
    """A service with almost all information derived from the config

    Currently missing the configured service labels.
    """

    check_plugin_name: CheckPluginName
    item: Item
    description: ServiceName
    parameters: TimespecificParameters
    discovered_parameters: Mapping[str, object]
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


class AutocheckEntryProtocol(Protocol):
    @property
    def check_plugin_name(self) -> CheckPluginName: ...

    @property
    def item(self) -> Item: ...

    @property
    def parameters(self) -> Mapping[str, object]: ...

    @property
    def service_labels(self) -> Mapping[str, str]: ...


class ServiceConfigurer:
    def __init__(
        self,
        compute_check_parameters: Callable[
            [HostName, CheckPluginName, Item, Mapping[str, object]], TimespecificParameters
        ],
        get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
        get_effective_host: Callable[[HostName, str], HostName],
    ) -> None:
        self._compute_check_parameters = compute_check_parameters
        self._get_service_description = get_service_description
        self._get_effective_host = get_effective_host

    def _configure_autocheck(
        self, hostname: HostName, autocheck_entry: AutocheckEntryProtocol
    ) -> ConfiguredService:
        # TODO: only call this function when we know "effective host" == hostname and simplify accordingly
        service_name = self._get_service_description(
            hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
        )

        return ConfiguredService(
            check_plugin_name=autocheck_entry.check_plugin_name,
            item=autocheck_entry.item,
            description=service_name,
            parameters=self._compute_check_parameters(
                self._get_effective_host(hostname, service_name),
                autocheck_entry.check_plugin_name,
                autocheck_entry.item,
                autocheck_entry.parameters,
            ),
            discovered_parameters=autocheck_entry.parameters,
            discovered_labels=autocheck_entry.service_labels,
            is_enforced=False,
        )

    def configure_autochecks(
        self, hostname: HostName, autocheck_entries: Iterable[AutocheckEntryProtocol]
    ) -> Sequence[ConfiguredService]:
        return [self._configure_autocheck(hostname, entry) for entry in autocheck_entries]


@dataclass(frozen=True)
class AggregatedResult:
    service: ConfiguredService
    data_received: bool
    result: ServiceCheckResult
    cache_info: tuple[int, int] | None


class CheckFunction(Protocol):
    def __call__(
        self,
        host_name: HostName,
        service: ConfiguredService,
        *,
        providers: Mapping[HostKey, Provider],
    ) -> AggregatedResult: ...


@dataclass(frozen=True)
class CheckPlugin:
    sections: Sequence[ParsedSectionName]
    function: CheckFunction
    default_parameters: Mapping[str, object] | None
    ruleset_name: RuleSetName | None
    discovery_ruleset_name: RuleSetName | None
