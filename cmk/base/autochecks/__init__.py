#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Caring about persistance of the discovered services (aka autochecks)"""

import logging
from contextlib import suppress
from typing import Callable, Dict, Iterable, Mapping, NamedTuple, Sequence

from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, CheckVariables, HostName, Item, ServiceName

from cmk.base.check_utils import ConfiguredService, LegacyCheckParameters
from cmk.base.discovered_labels import ServiceLabel

from .utils import AutocheckEntry, AutochecksStore

ComputeCheckParameters = Callable[
    [HostName, CheckPluginName, Item, LegacyCheckParameters],
    TimespecificParameters,
]
GetCheckVariables = Callable[[], CheckVariables]
GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]
HostOfClusteredService = Callable[[HostName, str], str]


class AutocheckServiceWithNodes(NamedTuple):
    service: AutocheckEntry
    nodes: Sequence[HostName]


logger = logging.getLogger("cmk.base.autochecks")


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""

    def __init__(self) -> None:
        super().__init__()
        self._autochecks: Dict[HostName, Sequence[ConfiguredService]] = {}
        # Extract of the autochecks: This cache is populated either on the way while
        # processing get_autochecks_of() or when directly calling discovered_labels_of().
        self._discovered_labels_of: Dict[
            HostName, Dict[ServiceName, Mapping[str, ServiceLabel]]
        ] = {}
        self._raw_autochecks_cache: Dict[HostName, Sequence[AutocheckEntry]] = {}

    def get_autochecks_of(
        self,
        hostname: HostName,
        compute_check_parameters: ComputeCheckParameters,
        get_service_description: GetServiceDescription,
        get_effective_hostname: HostOfClusteredService,
    ) -> Sequence[ConfiguredService]:
        if hostname not in self._autochecks:
            self._autochecks[hostname] = list(
                self._get_autochecks_of_uncached(
                    hostname,
                    compute_check_parameters,
                    get_service_description,
                    get_effective_hostname,
                )
            )
        return self._autochecks[hostname]

    def _get_autochecks_of_uncached(
        self,
        hostname: HostName,
        compute_check_parameters: ComputeCheckParameters,
        get_service_description: GetServiceDescription,
        get_effective_hostname: HostOfClusteredService,
    ) -> Iterable[ConfiguredService]:
        """Read automatically discovered checks of one host"""
        for autocheck_entry in self._read_raw_autochecks(hostname):
            service_name = get_service_description(hostname, *autocheck_entry.id())

            yield ConfiguredService(
                check_plugin_name=autocheck_entry.check_plugin_name,
                item=autocheck_entry.item,
                description=service_name,
                parameters=compute_check_parameters(
                    get_effective_hostname(hostname, service_name),
                    *autocheck_entry.id(),
                    autocheck_entry.parameters,
                ),
                discovered_parameters=autocheck_entry.parameters,
                service_labels={
                    name: ServiceLabel(name, value)
                    for name, value in autocheck_entry.service_labels.items()
                },
            )

    def discovered_labels_of(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        get_service_description: GetServiceDescription,
    ) -> Mapping[str, ServiceLabel]:
        # NOTE: this returns an empty labels object for non-existing services
        with suppress(KeyError):
            return self._discovered_labels_of[hostname][service_desc]

        hosts_labels = self._discovered_labels_of.setdefault(hostname, {})
        # Only read the raw autochecks here, do not compute the effective
        # check parameters. The latter would involve ruleset matching which
        # in turn would require already computed labels.
        for autocheck_entry in self._read_raw_autochecks(hostname):
            hosts_labels[
                get_service_description(
                    hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
                )
            ] = {n: ServiceLabel(n, v) for n, v in autocheck_entry.service_labels.items()}

        if (labels := hosts_labels.get(service_desc)) is not None:
            return labels
        return {}

    def _read_raw_autochecks(
        self,
        hostname: HostName,
    ) -> Sequence[AutocheckEntry]:
        if hostname not in self._raw_autochecks_cache:
            self._raw_autochecks_cache[hostname] = AutochecksStore(hostname).read()
        return self._raw_autochecks_cache[hostname]


def set_autochecks_of_real_hosts(
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
) -> None:
    store = AutochecksStore(hostname)
    # write new autochecks file for that host
    store.write(
        _consolidate_autochecks_of_real_hosts(
            hostname,
            new_services_with_nodes,
            store.read(),
        ),
    )


def _consolidate_autochecks_of_real_hosts(
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
    existing_autochecks: Sequence[AutocheckEntry],
) -> Sequence[AutocheckEntry]:
    consolidated = {
        discovered.id(): discovered
        for discovered, found_on_nodes in new_services_with_nodes
        if hostname in found_on_nodes
    }
    # overwrite parameters from existing ones for those which are kept
    new_services = {x.service.id() for x in new_services_with_nodes}
    consolidated.update((id_, ex) for ex in existing_autochecks if (id_ := ex.id()) in new_services)

    return list(consolidated.values())


def set_autochecks_of_cluster(
    nodes: Iterable[HostName],
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
    host_of_clustered_service: HostOfClusteredService,
    service_description: GetServiceDescription,
) -> None:
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    for node in nodes:
        new_autochecks = [
            existing
            for existing in AutochecksStore(node).read()
            if hostname
            != host_of_clustered_service(node, service_description(node, *existing.id()))
        ] + [
            discovered
            for discovered, found_on_nodes in new_services_with_nodes
            if node in found_on_nodes
        ]

        # write new autochecks file for that host
        AutochecksStore(node).write(_deduplicate(new_autochecks))

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    AutochecksStore(hostname).clear()


def _deduplicate(autochecks: Sequence[AutocheckEntry]) -> Sequence[AutocheckEntry]:
    """Cleanup duplicates

    (in particular versions pre 1.6.0p8 may have introduced some in the autochecks file)

    The first service is kept:

    >>> _deduplicate([
    ...    AutocheckEntry(CheckPluginName('a'), None, {'first': True}, {}),
    ...    AutocheckEntry(CheckPluginName('a'), None, {'first': False}, {}),
    ... ])[0].parameters
    {'first': True}

    """
    return list({a.id(): a for a in reversed(autochecks)}.values())


def remove_autochecks_of_host(
    hostname: HostName,
    remove_hostname: HostName,
    host_of_clustered_service: HostOfClusteredService,
    service_description: GetServiceDescription,
) -> int:
    store = AutochecksStore(hostname)
    existing_entries = store.read()
    new_entries = [
        existing
        for existing in existing_entries
        if remove_hostname
        != host_of_clustered_service(
            hostname,
            service_description(hostname, *existing.id()),
        )
    ]
    store.write(new_entries)

    return len(existing_entries) - len(new_entries)
