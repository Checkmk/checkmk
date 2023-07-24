#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.labels import ServiceLabel
from cmk.utils.servicename import ServiceName
from cmk.utils.store import ObjectStore

from cmk.checkengine.check_table import ConfiguredService, ServiceID
from cmk.checkengine.checking import CheckPluginName, Item
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import TimespecificParameters

__all__ = ["AutocheckServiceWithNodes", "AutocheckEntry", "AutochecksStore", "AutochecksManager"]


ComputeCheckParameters = Callable[
    [HostName, CheckPluginName, Item, LegacyCheckParameters],
    TimespecificParameters,
]
GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]
GetEffectviveHost = Callable[[HostName, str], HostName]


class AutocheckServiceWithNodes(NamedTuple):
    service: AutocheckEntry
    nodes: Sequence[HostName]


# If we switched to something less stupid than "LegacyCheckParameters", see
# if we can use pydantic
class AutocheckEntry(NamedTuple):
    check_plugin_name: CheckPluginName
    item: Item
    parameters: LegacyCheckParameters
    service_labels: Mapping[str, str]

    @staticmethod
    def _parse_parameters(parameters: object) -> LegacyCheckParameters:
        # Make sure it's a 'LegacyCheckParameters' (mainly done for mypy).
        if parameters is None or isinstance(parameters, (dict, tuple, list, str, int, bool)):
            return parameters
        # I have no idea what else it could be (LegacyCheckParameters is quite pointless).
        raise ValueError(f"Invalid autocheck: invalid parameters: {parameters!r}")

    @classmethod
    def load(cls, raw_dict: Mapping[str, Any]) -> AutocheckEntry:
        return cls(
            check_plugin_name=CheckPluginName(raw_dict["check_plugin_name"]),
            item=None if (raw_item := raw_dict["item"]) is None else str(raw_item),
            parameters=cls._parse_parameters(raw_dict["parameters"]),
            service_labels={str(n): str(v) for n, v in raw_dict["service_labels"].items()},
        )

    def id(self) -> ServiceID:
        """The identity of the service.

        As long as this does not change, we're talking about "the same" service (but it might have changed).
        """
        return ServiceID(self.check_plugin_name, self.item)

    def dump(self) -> Mapping[str, Any]:
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
        get_effective_host: GetEffectviveHost,
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
        get_effective_host: GetEffectviveHost,
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
    get_effective_host: GetEffectviveHost,
    get_service_description: GetServiceDescription,
) -> None:
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    for node in nodes:
        new_autochecks = [
            existing
            for existing in AutochecksStore(node).read()
            if hostname != get_effective_host(node, get_service_description(node, *existing.id()))
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
    get_effective_host: GetEffectviveHost,
    get_service_description: GetServiceDescription,
) -> int:
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
