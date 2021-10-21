#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Caring about persistance of the discovered services (aka autochecks)"""

import logging
from contextlib import suppress
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, CheckVariables, HostName, Item, ServiceName

from cmk.base.check_utils import AutocheckService, LegacyCheckParameters, Service
from cmk.base.discovered_labels import ServiceLabel

from .migration import deduplicate_autochecks, parse_autocheck_entry
from .utils import AutocheckEntry, AutochecksSerializer

ComputeCheckParameters = Callable[
    [HostName, CheckPluginName, Item, LegacyCheckParameters], Optional[LegacyCheckParameters]
]
GetCheckVariables = Callable[[], CheckVariables]
GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]
HostOfClusteredService = Callable[[HostName, str], str]


class AutocheckServiceWithNodes(NamedTuple):
    service: AutocheckService
    nodes: Sequence[HostName]


logger = logging.getLogger("cmk.base.autochecks")


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""

    def __init__(self) -> None:
        super().__init__()
        self._autochecks: Dict[HostName, Sequence[Service]] = {}
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
    ) -> Sequence[Service]:
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
    ) -> Iterable[Service]:
        """Read automatically discovered checks of one host"""
        for autocheck_entry in self._read_raw_autochecks(hostname):
            try:
                service_name = get_service_description(
                    hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
                )
            except Exception:  # I dont't really know why this is ignored. Feels utterly wrong.
                continue

            yield Service(
                check_plugin_name=autocheck_entry.check_plugin_name,
                item=autocheck_entry.item,
                description=service_name,
                parameters=compute_check_parameters(
                    get_effective_hostname(hostname, service_name),
                    autocheck_entry.check_plugin_name,
                    autocheck_entry.item,
                    autocheck_entry.parameters,
                ),
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
            try:
                hosts_labels[
                    get_service_description(
                        hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
                    )
                ] = {n: ServiceLabel(n, v) for n, v in autocheck_entry.service_labels.items()}
            except Exception:
                continue  # ignore

        if (labels := hosts_labels.get(service_desc)) is not None:
            return labels
        return {}

    def _read_raw_autochecks(
        self,
        hostname: HostName,
    ) -> Sequence[AutocheckEntry]:
        if hostname not in self._raw_autochecks_cache:
            self._raw_autochecks_cache[hostname] = self._read_raw_autochecks_uncached(hostname)
        return self._raw_autochecks_cache[hostname]

    # TODO: use store.ObjectStore
    # TODO: Common code with parse_autochecks_services? Cleanup.
    def _read_raw_autochecks_uncached(
        self,
        hostname: HostName,
    ) -> Sequence[AutocheckEntry]:
        """Read automatically discovered checks of one host"""
        path = _autochecks_path_for(hostname)
        try:
            autochecks_raw = _load_raw_autochecks(
                path=path,
                check_variables=None,
            )
        except SyntaxError as e:
            logger.exception("Syntax error in file %s: %s", path, e)
            if cmk.utils.debug.enabled():
                raise
            return []
        except Exception as e:
            logger.exception("Error in file %s:\n%s", path, e)
            if cmk.utils.debug.enabled():
                raise
            return []

        autocheck_entries = []
        for entry in autochecks_raw:
            try:
                item = entry["item"]
            except TypeError:  # pre 1.6 tuple!
                raise MKGeneralException(
                    "Invalid check entry '%r' of host '%s' (%s) found. This "
                    "entry is in pre Checkmk 1.6 format and needs to be converted. This is "
                    'normally done by "cmk-update-config -v" during "omd update". Please '
                    'execute "cmk-update-config -v" for convertig the old configuration.'
                    % (entry, hostname, path)
                )

            try:
                plugin_name = CheckPluginName(maincheckify(entry["check_plugin_name"]))
                assert item is None or isinstance(item, str)
            except Exception:
                raise MKGeneralException(
                    "Invalid check entry '%r' of host '%s' (%s) found. This "
                    "entry is in pre Checkmk 2.0 format and needs to be converted. This is "
                    'normally done by "cmk-update-config -v" during "omd update". Please '
                    'execute "cmk-update-config -v" for convertig the old configuration.'
                    % (entry, hostname, path)
                )

            autocheck_entries.append(
                AutocheckEntry(
                    check_plugin_name=plugin_name,
                    item=item,
                    parameters=entry["parameters"],
                    service_labels=entry["service_labels"],
                )
            )

        return autocheck_entries


def _autochecks_path_for(hostname: HostName) -> Path:
    return Path(cmk.utils.paths.autochecks_dir, hostname + ".mk")


def _load_raw_autochecks(
    *,
    path: Path,
    check_variables: Optional[Dict[str, Any]],
) -> Union[Iterable[Dict[str, Any]], Tuple]:
    """Read raw autochecks and resolve parameters"""
    if not path.exists():
        return []

    logger.debug("Loading autochecks from %s", path)
    with path.open(encoding="utf-8") as f:
        raw_file_content = f.read()

    if not raw_file_content.strip():
        return []

    try:
        # This evaluation was needed to resolve references to variables in the autocheck
        # default parameters and to evaluate data structure declarations containing references to
        # variables.
        # Since Checkmk 2.0 we have a better API and need it only for compatibility. The parameters
        # are resolved now *before* they are written to the autochecks file, and earlier autochecks
        # files are resolved during cmk-update-config.
        return eval(  # pylint: disable=eval-used
            raw_file_content, check_variables or {}, check_variables or {}
        )
    except NameError as exc:
        raise MKGeneralException(
            "%s in an autocheck entry of host '%s' (%s). This entry is in pre Checkmk 1.7 "
            "format and needs to be converted. This is normally done by "
            '"cmk-update-config -v" during "omd update". Please execute '
            '"cmk-update-config -v" for converting the old configuration.'
            % (str(exc).capitalize(), path.stem, path)
        )


def parse_autochecks_services(
    hostname: HostName,
    service_description: GetServiceDescription,
    check_variables: Optional[Dict[str, Any]] = None,
) -> Sequence[AutocheckService]:
    """Read autochecks, but do not compute final check parameters"""
    path = _autochecks_path_for(hostname)
    try:
        raw_autochecks = _load_raw_autochecks(
            path=path,
            check_variables=check_variables,
        )
    except SyntaxError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException(
            "Unable to parse autochecks of host %s (%s): %s" % (hostname, path, e)
        )

    return [
        service
        for entry in raw_autochecks
        if isinstance(entry, (tuple, dict))
        and (service := _parse_autocheck_service(hostname, entry, service_description)) is not None
    ]


def _parse_autocheck_service(
    hostname: HostName,
    entry: Union[Tuple, Dict],
    service_description: GetServiceDescription,
) -> Optional[AutocheckService]:

    autocheck_entry = parse_autocheck_entry(entry)

    try:
        description = service_description(
            hostname, autocheck_entry.check_plugin_name, autocheck_entry.item
        )
    except Exception:
        return None  # ignore

    return AutocheckService(
        check_plugin_name=autocheck_entry.check_plugin_name,
        item=autocheck_entry.item,
        description=description,
        parameters=autocheck_entry.parameters,
        service_labels={n: ServiceLabel(n, v) for n, v in autocheck_entry.service_labels.items()},
    )


def set_autochecks_of_real_hosts(
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
    service_description: GetServiceDescription,
) -> None:
    # write new autochecks file for that host
    save_autochecks_services(
        hostname,
        _consolidate_autochecks_of_real_hosts(
            hostname,
            new_services_with_nodes,
            parse_autochecks_services(hostname, service_description),
        ),
    )


def _consolidate_autochecks_of_real_hosts(
    hostname: HostName,
    new_services_with_nodes: Sequence[AutocheckServiceWithNodes],
    existing_autochecks: Sequence[AutocheckService],
) -> Sequence[AutocheckService]:
    consolidated = {
        discovered.id(): discovered
        for discovered, found_on_nodes in new_services_with_nodes
        if hostname in found_on_nodes
    }
    # overwrite parameters from existing ones for those which are kept
    new_services = {x.service.id() for x in new_services_with_nodes}
    consolidated.update((ex.id(), ex) for ex in existing_autochecks if ex.id() in new_services)

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
            for existing in parse_autochecks_services(node, service_description)
            if hostname != host_of_clustered_service(node, existing.description)
        ] + [
            discovered
            for discovered, found_on_nodes in new_services_with_nodes
            if node in found_on_nodes
        ]

        # write new autochecks file for that host
        save_autochecks_services(node, deduplicate_autochecks(new_autochecks))

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    remove_autochecks_file(hostname)


def save_autochecks_services(
    hostname: HostName,
    services: Sequence[AutocheckService],
) -> None:
    save_autochecks(
        hostname,
        [
            AutocheckEntry(
                check_plugin_name=s.check_plugin_name,
                item=s.item,
                parameters=s.parameters,
                service_labels={l.name: l.value for l in s.service_labels.values()},
            )
            for s in sorted(services)
        ],
    )


def save_autochecks(hostname: HostName, entries: Sequence[AutocheckEntry]) -> None:
    store.ObjectStore(
        _autochecks_path_for(hostname),
        serializer=AutochecksSerializer(),
    ).write_obj(entries)


def remove_autochecks_file(hostname: HostName) -> None:
    try:
        _autochecks_path_for(hostname).unlink()
    except OSError:
        pass


def remove_autochecks_of_host(
    hostname: HostName,
    remove_hostname: HostName,
    host_of_clustered_service: HostOfClusteredService,
    service_description: GetServiceDescription,
) -> int:
    existing_services = parse_autochecks_services(hostname, service_description)
    new_services = [
        existing
        for existing in existing_services
        if remove_hostname
        != host_of_clustered_service(
            hostname,
            existing.description,
        )
    ]

    save_autochecks_services(hostname, new_services)
    return len(existing_services) - len(new_services)
