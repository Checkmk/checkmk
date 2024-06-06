#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, TypedDict

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import ServiceLabel
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.store import ObjectStore

from cmk.checkengine.checking import CheckPluginName, ConfiguredService, ServiceID
from cmk.checkengine.discovery._utils import DiscoveredItem
from cmk.checkengine.parameters import TimespecificParameters

__all__ = [
    "AutocheckServiceWithNodes",
    "AutocheckEntry",
    "AutochecksStore",
    "AutochecksManager",
    "DiscoveredService",
    "remove_autochecks_of_host",
    "set_autochecks_for_effective_host",
    "set_autochecks_of_cluster",
    "set_autochecks_of_real_hosts",
]


ComputeCheckParameters = Callable[
    [HostName, CheckPluginName, Item, Mapping[str, object]],
    TimespecificParameters,
]
GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]
GetEffectiveHost = Callable[[HostName, str], HostName]
GetEffectiveHostOfAc = Callable[[HostName, CheckPluginName, Item], HostName]


class AutocheckServiceWithNodes(NamedTuple):
    service: DiscoveredItem[AutocheckEntry]
    nodes: Sequence[HostName]


class AutocheckDict(TypedDict):
    check_plugin_name: str
    item: str | None
    parameters: Mapping[str, object]
    service_labels: Mapping[str, str]


class AutocheckEntry(NamedTuple):
    check_plugin_name: CheckPluginName
    item: Item
    parameters: Mapping[str, object]
    service_labels: Mapping[str, str]

    @staticmethod
    def _parse_parameters(parameters: object) -> Mapping[str, object]:
        if isinstance(parameters, dict):
            return {str(k): v for k, v in parameters.items()}

        raise ValueError(f"Invalid autocheck: invalid parameters: {parameters!r}")

    @staticmethod
    def _parse_labels(labels: object) -> Mapping[str, str]:
        if isinstance(labels, dict):
            return {str(k): str(v) for k, v in labels.items()}

        raise ValueError(f"Invalid autocheck: invalid labels: {labels!r}")

    @classmethod
    def load(cls, raw_dict: Mapping[str, object]) -> AutocheckEntry:
        return cls(
            check_plugin_name=CheckPluginName(str(raw_dict["check_plugin_name"])),
            item=None if (raw_item := raw_dict["item"]) is None else str(raw_item),
            parameters=cls._parse_parameters(raw_dict["parameters"]),
            service_labels=cls._parse_labels(raw_dict["service_labels"]),
        )

    def id(self) -> ServiceID:
        """The identity of the service.

        As long as this does not change, we're talking about "the same" service (but it might have changed).
        """
        return ServiceID(self.check_plugin_name, self.item)

    def comparator(self) -> tuple[Mapping[str, object], Mapping[str, str]]:
        return self.parameters, self.service_labels

    def dump(self) -> AutocheckDict:
        return {
            "check_plugin_name": str(self.check_plugin_name),
            "item": self.item,
            "parameters": self.parameters,
            "service_labels": self.service_labels,
        }


class _AutochecksSerializer:
    @staticmethod
    def serialize(entries: Sequence[AutocheckEntry]) -> bytes:
        return ("[\n%s]\n" % "".join(f"  {e.dump()!r},\n" for e in entries)).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Sequence[AutocheckEntry]:
        return [AutocheckEntry.load(d) for d in ast.literal_eval(raw.decode("utf-8"))]


class AutochecksStore:
    def __init__(self, host_name: HostName) -> None:
        self._host_name = host_name
        self._store = ObjectStore(
            Path(cmk.utils.paths.autochecks_dir, f"{host_name}.mk"),
            serializer=_AutochecksSerializer(),
        )

    def read(self) -> Sequence[AutocheckEntry]:
        try:
            return self._store.read_obj(default=[])
        except (ValueError, TypeError, KeyError, AttributeError, SyntaxError) as exc:
            raise MKGeneralException(
                f"Unable to parse autochecks of host {self._host_name}"
            ) from exc

    def write(self, entries: Sequence[AutocheckEntry]) -> None:
        self._store.write_obj(
            sorted(entries, key=lambda e: (str(e.check_plugin_name), str(e.item)))
        )

    def clear(self):
        try:
            self._store.path.unlink()
        except OSError:
            pass


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""

    def __init__(self) -> None:
        super().__init__()
        self._autochecks: dict[HostName, Sequence[ConfiguredService]] = {}
        # Extract of the autochecks: This cache is populated either on the way while
        # processing get_autochecks_of() or when directly calling discovered_labels_of().
        self._discovered_labels_of: dict[
            HostName, dict[ServiceName, Mapping[str, ServiceLabel]]
        ] = {}
        self._raw_autochecks_cache: dict[HostName, Sequence[AutocheckEntry]] = {}

    def get_autochecks_of(
        self,
        hostname: HostName,
        compute_check_parameters: ComputeCheckParameters,
        get_service_description: GetServiceDescription,
        get_effective_host: GetEffectiveHost,
    ) -> Sequence[ConfiguredService]:
        if hostname not in self._autochecks:
            self._autochecks[hostname] = list(
                self._get_autochecks_of_uncached(
                    hostname,
                    compute_check_parameters,
                    get_service_description,
                    get_effective_host,
                )
            )
        return self._autochecks[hostname]

    def _get_autochecks_of_uncached(
        self,
        hostname: HostName,
        compute_check_parameters: ComputeCheckParameters,
        get_service_description: GetServiceDescription,
        get_effective_host: GetEffectiveHost,
    ) -> Iterable[ConfiguredService]:
        """Read automatically discovered checks of one host"""
        for autocheck_entry in self._read_raw_autochecks(hostname):
            service_name = get_service_description(hostname, *autocheck_entry.id())

            yield ConfiguredService(
                check_plugin_name=autocheck_entry.check_plugin_name,
                item=autocheck_entry.item,
                description=service_name,
                parameters=compute_check_parameters(
                    get_effective_host(hostname, service_name),
                    *autocheck_entry.id(),
                    autocheck_entry.parameters,
                ),
                discovered_parameters=autocheck_entry.parameters,
                service_labels={
                    name: ServiceLabel(name, value)
                    for name, value in autocheck_entry.service_labels.items()
                },
                is_enforced=False,
            )

    def discovered_labels_of(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        get_service_description: GetServiceDescription,
    ) -> Mapping[str, ServiceLabel]:
        # NOTE: this returns an empty labels object for non-existing services
        if (loaded_labels := self._discovered_labels_of.get(hostname)) is not None:
            return loaded_labels.get(service_desc, {})

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
    # TODO: use set_autochecks_for_effective_host instead
    store = AutochecksStore(hostname)
    # write new autochecks file for that host
    store.write(
        _consolidate_autochecks_of_real_hosts(
            hostname,
            new_services_with_nodes,
            store.read(),
        )
    )


def _consolidate_autochecks_of_real_hosts(
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
    existing_autochecks: Sequence[AutocheckEntry],
) -> Sequence[AutocheckEntry]:
    consolidated = {
        DiscoveredService.id(discovered): DiscoveredService.newer(discovered)
        for discovered, found_on_nodes in new_services_with_nodes
        if hostname in found_on_nodes
    }

    new_services = {DiscoveredService.id(x.service) for x in new_services_with_nodes}
    consolidated.update(
        (id_, ex)
        for ex in existing_autochecks
        if (id_ := ex.id()) in new_services and id_ not in consolidated
    )
    return list(consolidated.values())


def set_autochecks_of_cluster(
    nodes: Iterable[HostName],
    hostname: HostName,
    new_services_with_nodes_by_host: Mapping[HostName, Sequence[AutocheckServiceWithNodes]],
    get_effective_host: GetEffectiveHost,
    get_service_description: GetServiceDescription,
) -> None:
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""

    def get_effective_host_by_id(
        host: HostName, plugin_name: CheckPluginName, item: Item
    ) -> HostName:
        return get_effective_host(host, get_service_description(host, plugin_name, item))

    for node in nodes:
        set_autochecks_for_effective_host(
            autochecks_owner=node,
            effective_host=hostname,
            new_services=[
                DiscoveredService.newer(discovered)
                for discovered, found_on_nodes in new_services_with_nodes_by_host[node]
                if node in found_on_nodes
            ],
            get_effective_host=get_effective_host_by_id,
        )

    # Check whether the cluster host autocheck files are still existent.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    AutochecksStore(hostname).clear()


def set_autochecks_for_effective_host(
    autochecks_owner: HostName,
    effective_host: HostName,
    new_services: Iterable[AutocheckEntry],
    get_effective_host: GetEffectiveHostOfAc,
) -> None:
    """A set all services of an effective host, and leave all other services alone."""
    store = AutochecksStore(autochecks_owner)
    store.write(
        _deduplicate(
            [
                *(
                    existing
                    for existing in store.read()
                    if effective_host != get_effective_host(autochecks_owner, *existing.id())
                ),
                *new_services,
            ]
        )
    )


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
    get_effective_host: GetEffectiveHost,
    get_service_description: GetServiceDescription,
) -> int:
    """Remove all autochecks of a host while being cluster-aware

    Cluster aware means that the autocheck files of the nodes are handled. Instead
    of removing the whole file the file is loaded and only the services associated
    with the given cluster are removed."""
    store = AutochecksStore(hostname)
    existing_entries = store.read()
    new_entries = [
        existing
        for existing in existing_entries
        if remove_hostname
        != get_effective_host(
            hostname,
            get_service_description(hostname, *existing.id()),
        )
    ]
    store.write(new_entries)

    return len(existing_entries) - len(new_entries)


class DiscoveredService:
    @staticmethod
    def check_plugin_name(discovered_item: DiscoveredItem[AutocheckEntry]) -> CheckPluginName:
        return DiscoveredService.older(discovered_item).check_plugin_name

    @staticmethod
    def item(discovered_item: DiscoveredItem[AutocheckEntry]) -> Item:
        return DiscoveredService.older(discovered_item).item

    @staticmethod
    def id(discovered_item: DiscoveredItem[AutocheckEntry]) -> ServiceID:
        return DiscoveredService.older(discovered_item).id()

    @staticmethod
    def older(discovered_item: DiscoveredItem[AutocheckEntry]) -> AutocheckEntry:
        if discovered_item.previous is not None:
            return discovered_item.previous
        if discovered_item.new is not None:
            return discovered_item.new
        raise ValueError("Neither previous nor new service is set.")

    @staticmethod
    def newer(discovered_item: DiscoveredItem[AutocheckEntry]) -> AutocheckEntry:
        if discovered_item.new is not None:
            return discovered_item.new
        if discovered_item.previous is not None:
            return discovered_item.previous
        raise ValueError("Neither previous nor new service is set.")
