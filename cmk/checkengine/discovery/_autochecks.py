#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple, Protocol, TypedDict

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.store import ObjectStore

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import Labels
from cmk.utils.servicename import Item, ServiceName

from cmk.checkengine.checking import CheckPluginName, ConfiguredService, ServiceID
from cmk.checkengine.discovery._utils import DiscoveredItem

__all__ = [
    "AutocheckServiceWithNodes",
    "AutocheckEntry",
    "AutochecksStore",
    "AutochecksManager",
    "AutochecksConfig",
    "remove_autochecks_of_host",
    "set_autochecks_for_effective_host",
    "set_autochecks_of_cluster",
    "set_autochecks_of_real_hosts",
]


_GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]


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


_GetEffectiveHost = Callable[[HostName, AutocheckEntry], HostName]


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


def merge_cluster_autochecks(
    autochecks: Mapping[HostName, Sequence[AutocheckEntry]],
    active_nodes: Sequence[HostName],
    appears_on_cluster: Callable[[HostName, AutocheckEntry], bool],
) -> Sequence[AutocheckEntry]:
    # filter for cluster and flatten:
    entries = {
        node_name: e
        for node_name, entries in autochecks.items()
        for e in entries
        if appears_on_cluster(node_name, e)
    }

    # group by service id and reverse order to make the first node win in merging
    # but prioritize the current active nodes
    entries_by_id: dict[ServiceID, list[AutocheckEntry]] = defaultdict(list)
    for node_name, entry in sorted(entries.items(), key=lambda x: x[0] not in active_nodes):
        entries_by_id[entry.id()].insert(0, entry)

    return [
        AutocheckEntry(
            *id,
            parameters={k: v for e in entries for k, v in e.parameters.items()},
            service_labels={k: v for e in entries for k, v in e.service_labels.items()},
        )
        for id, entries in entries_by_id.items()
    ]


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager.

    When trying to remove this cache (which we should consider), make sure to keep
    the case of overlapping clusters in mind. Autochecks of a node might be read
    multiple times (to a degree where it's not accepteble).
    """

    def __init__(self) -> None:
        super().__init__()
        self._configured_services_cache: dict[HostName, Sequence[ConfiguredService]] = {}
        self._raw_autochecks_cache: dict[HostName, Sequence[AutocheckEntry]] = {}

    def get_autochecks(
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
        discovered.newer.id(): discovered.newer
        for discovered, found_on_nodes in new_services_with_nodes
        if hostname in found_on_nodes
    }

    new_services = {x.service.newer.id() for x in new_services_with_nodes}
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
    get_effective_host: _GetEffectiveHost,
) -> None:
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""

    for node in nodes:
        set_autochecks_for_effective_host(
            autochecks_owner=node,
            effective_host=hostname,
            new_services=[
                discovered.newer  # TODO: really? new_er_?
                for discovered, found_on_nodes in new_services_with_nodes_by_host[node]
                if node in found_on_nodes
            ],
            get_effective_host=get_effective_host,
        )

    # Check whether the cluster host autocheck files are still existent.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    AutochecksStore(hostname).clear()


def set_autochecks_for_effective_host(
    autochecks_owner: HostName,
    effective_host: HostName,
    new_services: Iterable[AutocheckEntry],
    get_effective_host: _GetEffectiveHost,
) -> None:
    """Set all services of an effective host, and leave all other services alone."""
    store = AutochecksStore(autochecks_owner)
    store.write(
        _deduplicate(
            [
                *(
                    existing
                    for existing in store.read()
                    if effective_host != get_effective_host(autochecks_owner, existing)
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
    get_effective_host: _GetEffectiveHost,
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
        if remove_hostname != get_effective_host(hostname, existing)
    ]
    store.write(new_entries)

    return len(existing_entries) - len(new_entries)


class DiscoveredLabelsCache:
    """Cache for discovered labels of services

    This is insane.

    We need this because we insist on looking up the labels of a service by its name.
    Discovered labels are attached to the autocheck entry, which is identified by the
    service ID (check plugin name and item).
    We read all of the autochecks, compute all the service names, and then see if one
    matches.

    Ironically, at the start we already knew the service ID. We just forgot about it.
    """

    def __init__(
        self,
        clusters: Mapping[HostName, Sequence[HostName]],
        get_autochecks: Callable[[HostName], Sequence[AutocheckEntry]],
    ) -> None:
        self._clusters = clusters
        self._get_autochecks = get_autochecks
        self._discovered_labels_of: dict[HostName, Mapping[ServiceName, Labels]] = {}

    def discovered_labels_of(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        get_service_description: _GetServiceDescription,
        get_effective_host: _GetEffectiveHost,
    ) -> Labels:
        # NOTE: this returns an empty labels object for non-existing services
        if (hosts_service_labels := self._discovered_labels_of.get(hostname)) is None:
            hosts_service_labels = self._discovered_labels_of.setdefault(
                hostname,
                self._get_hosts_discovered_service_labels(
                    hostname,
                    get_service_description,
                    get_effective_host,
                ),
            )

        return hosts_service_labels.get(service_desc, {})

    def _get_hosts_discovered_service_labels(
        self,
        host_name: HostName,
        get_service_description: _GetServiceDescription,
        get_effective_host: _GetEffectiveHost,
    ) -> Mapping[ServiceName, Labels]:
        return (
            self._get_real_hosts_discovered_service_labels(host_name, get_service_description)
            if (nodes := self._clusters.get(host_name)) is None
            else self._get_clusters_discovered_service_labels(
                host_name, nodes, get_service_description, get_effective_host
            )
        )

    def _get_real_hosts_discovered_service_labels(
        self,
        node_name: HostName,
        get_service_description: _GetServiceDescription,
    ) -> Mapping[ServiceName, Labels]:
        return {
            get_service_description(
                node_name, autocheck_entry.check_plugin_name, autocheck_entry.item
            ): autocheck_entry.service_labels
            for autocheck_entry in self._get_autochecks(node_name)
        }

    def _get_clusters_discovered_service_labels(
        self,
        cluster_name: HostName,
        nodes: Sequence[HostName],
        get_service_description: _GetServiceDescription,
        get_effective_host: _GetEffectiveHost,
    ) -> Mapping[ServiceName, Labels]:
        return {
            get_service_description(
                cluster_name, autocheck_entry.check_plugin_name, autocheck_entry.item
            ): autocheck_entry.service_labels
            for autocheck_entry in merge_cluster_autochecks(
                {node: self._get_autochecks(node) for node in nodes},
                nodes,
                lambda node_name, entry: (get_effective_host(node_name, entry) == cluster_name),
            )
        }


# TODO: We shouldn't need a protocol for configuration options
class AutochecksConfig(Protocol):
    """Interface for the autochecks configuration

    For many of these we currently only use the service id,
    but only because the use of the discovered labels is obfuscated
    by the DiscoveredLabelsCache.
    """

    def ignore_plugin(self, host_name: HostName, plugin_name: CheckPluginName) -> bool: ...

    def ignore_service(self, host_name: HostName, entry: AutocheckEntry) -> bool: ...

    def effective_host(self, host_name: HostName, entry: AutocheckEntry) -> HostName: ...

    def service_description(self, host_name: HostName, entry: AutocheckEntry) -> ServiceName: ...
