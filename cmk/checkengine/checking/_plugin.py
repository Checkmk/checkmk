#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Protocol

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.parameters import merge_parameters
from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugin_backend import get_check_plugin
from cmk.checkengine.plugins import (
    CheckPlugin,
    CheckPluginName,
    ConfiguredService,
    ServiceID,
)

from ._checking import ABCCheckingConfig

__all__ = [
    "ServiceConfigurer",
    "merge_enforced_services",
    "AutocheckEntryProtocol",
]

type _DiscoveredLabels = Mapping[str, str]

type _Labels = Mapping[str, str]


class AutocheckEntryProtocol(Protocol):
    @property
    def check_plugin_name(self) -> CheckPluginName: ...

    @property
    def item(self) -> Item: ...

    @property
    def parameters(self) -> Mapping[str, object]: ...

    @property
    def service_labels(self) -> _DiscoveredLabels: ...


class ServiceConfigurer:
    def __init__(
        self,
        checking_config: ABCCheckingConfig,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        get_service_description: Callable[[HostName, CheckPluginName, Item], ServiceName],
        get_effective_host: Callable[[HostName, ServiceName, _Labels], HostName],
        get_service_labels: Callable[[HostName, ServiceName, _DiscoveredLabels], _Labels],
    ) -> None:
        self._checking_config = checking_config
        self._plugins = plugins
        self._get_service_description = get_service_description
        self._get_effective_host = get_effective_host
        self._get_service_labels = get_service_labels

    def _configure_autocheck(
        self,
        hostname: HostName,
        autocheck_entry: AutocheckEntryProtocol,
    ) -> ConfiguredService:
        # TODO: only call this function when we know "effective host" == hostname and simplify accordingly
        service_name = self._get_service_description(
            hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
        )
        labels = self._get_service_labels(hostname, service_name, autocheck_entry.service_labels)

        return ConfiguredService(
            check_plugin_name=autocheck_entry.check_plugin_name,
            item=autocheck_entry.item,
            description=service_name,
            parameters=compute_check_parameters(
                self._checking_config,
                self._plugins,
                self._get_effective_host(hostname, service_name, labels),
                autocheck_entry.check_plugin_name,
                autocheck_entry.item,
                labels,
                autocheck_entry.parameters,
            ),
            discovered_parameters=autocheck_entry.parameters,
            labels=labels,
            discovered_labels=autocheck_entry.service_labels,
            is_enforced=False,
        )

    def configure_autochecks(
        self,
        hostname: HostName,
        autocheck_entries: Iterable[AutocheckEntryProtocol],
    ) -> Sequence[ConfiguredService]:
        return [self._configure_autocheck(hostname, entry) for entry in autocheck_entries]


def merge_enforced_services(
    services: Mapping[HostAddress, Mapping[ServiceID, tuple[object, ConfiguredService]]],
    appears_on_cluster: Callable[[HostAddress, ServiceName, _DiscoveredLabels], bool],
    labels_of_service: Callable[[ServiceName, _DiscoveredLabels], _Labels],
) -> Iterable[ConfiguredService]:
    """Aggregate services from multiple nodes"""
    entries_by_id: dict[ServiceID, list[ConfiguredService]] = defaultdict(list)
    for node, node_services in services.items():
        for sid, (_, service) in node_services.items():
            if appears_on_cluster(node, service.description, service.discovered_labels):
                entries_by_id[sid].append(service)

    return [
        ConfiguredService(
            check_plugin_name=sid[0],
            item=sid[1],
            description=entries[0].description,
            parameters=TimespecificParameters(
                [ps for entry in entries for ps in entry.parameters.entries]
            ),
            # For consistency we also merge `discovered_{parameters,labels}`.
            # At the time of writing, they are always empty for enforced services.
            discovered_parameters=merge_parameters([e.discovered_parameters for e in entries], {}),
            discovered_labels=(
                discovered_labels := merge_parameters([e.discovered_labels for e in entries], {})
            ),
            labels=labels_of_service(entries[0].description, discovered_labels),
            is_enforced=True,
        )
        for sid, entries in entries_by_id.items()
    ]


def compute_check_parameters(
    checking_config: ABCCheckingConfig,
    plugins: Mapping[CheckPluginName, CheckPlugin],
    host_name: HostName,
    plugin_name: CheckPluginName,
    item: Item,
    service_labels: Mapping[str, str],
    params: Mapping[str, object],
) -> TimespecificParameters:
    """Compute effective check parameters.

    Honoring (in order of precedence):
     * the configured parameters
     * the discovered parameters
     * the plugins defaults
    """
    check_plugin = get_check_plugin(plugin_name, plugins)
    if check_plugin is None:  # handle vanished check plug-in
        return TimespecificParameters()

    configured_parameters = _get_configured_parameters(
        checking_config,
        host_name,
        service_labels,
        ruleset_name=check_plugin.check_ruleset_name,
        item=item,
    )

    return TimespecificParameters(
        [
            *configured_parameters.entries,
            TimespecificParameterSet.from_parameters(params),
            TimespecificParameterSet.from_parameters(check_plugin.check_default_parameters or {}),
        ]
    )


def _get_configured_parameters(
    checking_config: ABCCheckingConfig,
    host_name: HostName,
    service_labels: Mapping[str, str],
    *,  # the following are all the same type :-(
    ruleset_name: RuleSetName | None,
    item: Item,
) -> TimespecificParameters:
    if ruleset_name is None:
        return TimespecificParameters()

    return TimespecificParameters(
        [
            # parameters configured via checkgroup_parameters
            TimespecificParameterSet.from_parameters(p)
            for p in checking_config(host_name, item, service_labels, str(ruleset_name))
        ]
    )
