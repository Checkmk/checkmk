#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Caring about persistance of the discovered services (aka autochecks)"""

from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
import sys
from pathlib import Path

from six import ensure_str

from cmk.utils.check_utils import maincheckify
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    CheckVariables,
    HostName,
    Item,
    ServiceName,
)
from cmk.utils.log import console

from cmk.base.discovered_labels import DiscoveredServiceLabels, ServiceLabel
from cmk.base.check_utils import LegacyCheckParameters, Service

# this only ever applies to config.compute_check_parameters, whos
# signature has been broadened to accept CheckPluginNameStr
# *or* CheckPluginName alternatively (to ease migration).
# Once we're ready, it should only accept the CheckPluginName
ComputeCheckParameters = Callable[
    [HostName, Union[CheckPluginNameStr, CheckPluginName], Item, LegacyCheckParameters],
    Optional[LegacyCheckParameters]]
GetCheckVariables = Callable[[], CheckVariables]
GetServiceDescription = Callable[[HostName, CheckPluginName, Item], ServiceName]
HostOfClusteredService = Callable[[HostName, str], str]


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""
    def __init__(self) -> None:
        super(AutochecksManager, self).__init__()
        self._autochecks: Dict[HostName, List[Service]] = {}
        # Extract of the autochecks: This cache is populated either on the way while
        # processing get_autochecks_of() or when directly calling discovered_labels_of().
        self._discovered_labels_of: Dict[HostName, Dict[str, DiscoveredServiceLabels]] = {}
        self._raw_autochecks_cache: Dict[HostName, List[Service]] = {}

    def get_autochecks_of(
        self,
        hostname: str,
        compute_check_parameters: ComputeCheckParameters,
        service_description: GetServiceDescription,
    ) -> List[Service]:
        if hostname not in self._autochecks:
            self._autochecks[hostname] = self._get_autochecks_of_uncached(
                hostname, compute_check_parameters, service_description)
        return self._autochecks[hostname]

    def _get_autochecks_of_uncached(
        self,
        hostname: HostName,
        compute_check_parameters: ComputeCheckParameters,
        service_description: GetServiceDescription,
    ) -> List[Service]:
        """Read automatically discovered checks of one host"""
        return [
            Service(
                check_plugin_name=service.check_plugin_name,
                item=service.item,
                description=service.description,
                parameters=compute_check_parameters(
                    hostname,
                    service.check_plugin_name,
                    service.item,
                    service.parameters,
                ),
                service_labels=service.service_labels,
            ) for service in self._read_raw_autochecks(hostname, service_description)
        ]

    def discovered_labels_of(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        service_description: GetServiceDescription,
    ) -> DiscoveredServiceLabels:
        if hostname not in self._discovered_labels_of:
            # Only read the raw autochecks here, do not compute the effective
            # check parameters. The latter would involve ruleset matching which
            # in turn would require already computed labels.
            self._read_raw_autochecks(hostname, service_description)
        if service_desc not in self._discovered_labels_of[hostname]:
            self._discovered_labels_of[hostname][service_desc] = DiscoveredServiceLabels()
        return self._discovered_labels_of[hostname][service_desc]

    def _read_raw_autochecks(
        self,
        hostname: HostName,
        service_description: GetServiceDescription,
    ) -> List[Service]:
        if hostname not in self._raw_autochecks_cache:
            self._raw_autochecks_cache[hostname] = self._read_raw_autochecks_uncached(
                hostname,
                service_description,
            )
            # create cache from autocheck labels
            self._discovered_labels_of.setdefault(hostname, {})
            for service in self._raw_autochecks_cache[hostname]:
                self._discovered_labels_of[hostname][service.description] = service.service_labels
        return self._raw_autochecks_cache[hostname]

    # TODO: use store.load_object_from_file()
    # TODO: Common code with parse_autochecks_file? Cleanup.
    def _read_raw_autochecks_uncached(
        self,
        hostname: HostName,
        service_description: GetServiceDescription,
    ) -> List[Service]:
        """Read automatically discovered checks of one host"""
        path = _autochecks_path_for(hostname)
        try:
            autochecks_raw = _load_raw_autochecks(
                path=path,
                check_variables=None,
            )
        except SyntaxError as e:
            console.verbose("Syntax error in file %s: %s\n", path, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return []
        except Exception as e:
            console.verbose("Error in file %s:\n%s\n", path, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return []

        services: List[Service] = []
        for entry in autochecks_raw:
            try:
                item = entry["item"]
            except TypeError:  # pre 1.6 tuple!
                raise MKGeneralException(
                    "Invalid check entry '%r' of host '%s' (%s) found. This "
                    "entry is in pre Checkmk 1.6 format and needs to be converted. This is "
                    "normally done by \"cmk-update-config -v\" during \"omd update\". Please "
                    "execute \"cmk-update-config -v\" for convertig the old configuration." %
                    (entry, hostname, path))

            try:
                plugin_name = CheckPluginName(maincheckify(entry["check_plugin_name"]))
                assert item is None or isinstance(item, str)
            except Exception:
                raise MKGeneralException(
                    "Invalid check entry '%r' of host '%s' (%s) found. This "
                    "entry is in pre Checkmk 1.7 format and needs to be converted. This is "
                    "normally done by \"cmk-update-config -v\" during \"omd update\". Please "
                    "execute \"cmk-update-config -v\" for convertig the old configuration." %
                    (entry, hostname, path))

            labels = DiscoveredServiceLabels()
            for label_id, label_value in entry["service_labels"].items():
                labels.add_label(ServiceLabel(label_id, label_value))

            try:
                description = service_description(hostname, plugin_name, item)
            except Exception:
                continue  # ignore

            services.append(
                Service(
                    check_plugin_name=plugin_name,
                    item=item,
                    description=description,
                    parameters=entry["parameters"],
                    service_labels=labels,
                ))

        return services


def _autochecks_path_for(hostname: HostName) -> Path:
    return Path(cmk.utils.paths.autochecks_dir, hostname + ".mk")


def has_autochecks(hostname: HostName) -> bool:
    return _autochecks_path_for(hostname).exists()


def _load_raw_autochecks(
    *,
    path: Path,
    check_variables: Optional[Dict[str, Any]],
) -> Union[List[Dict[str, Any]], Tuple]:
    """Read raw autochecks and resolve parameters"""
    if not path.exists():
        return []

    console.vverbose("Loading autochecks from %s\n", path)
    with path.open(encoding="utf-8") as f:
        raw_file_content = f.read()

    if not raw_file_content.strip():
        return []

    try:
        return eval(raw_file_content, check_variables or {}, check_variables or {})
    except NameError as exc:
        raise MKGeneralException(
            "%s in an autocheck entry of host '%s' (%s). This entry is in pre Checkmk 1.7 "
            "format and needs to be converted. This is normally done by "
            "\"cmk-update-config -v\" during \"omd update\". Please execute "
            "\"cmk-update-config -v\" for converting the old configuration." %
            (str(exc).capitalize(), path.stem, path))


def parse_autochecks_file(
    hostname: HostName,
    service_description: GetServiceDescription,
    check_variables: Optional[Dict[str, Any]] = None,
) -> List[Service]:
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
        raise MKGeneralException("Unable to parse autochecks of host %s (%s): %s" %
                                 (hostname, path, e))

    services: List[Service] = []
    for entry in raw_autochecks:
        if not isinstance(entry, (tuple, dict)):
            continue

        service = _parse_autocheck_entry(hostname, entry, service_description)
        if service:
            services.append(service)

    return services


def _parse_autocheck_entry(
    hostname: HostName,
    entry: Union[Tuple, Dict],
    service_description: GetServiceDescription,
) -> Optional[Service]:
    if isinstance(entry, tuple):
        check_plugin_name, item, parameters = _parse_pre_16_tuple_autocheck_entry(entry)
        dict_service_labels = {}
    elif isinstance(entry, dict):
        check_plugin_name, item, parameters, dict_service_labels = \
            _parse_dict_autocheck_entry(entry)
    else:
        raise Exception("Invalid autocheck: Wrong type: %r" % entry)

    if not isinstance(check_plugin_name, str):
        raise Exception("Invalid autocheck: Wrong check plugin type: %r" % check_plugin_name)

    if isinstance(item, (int, float)):
        # NOTE: We exclude complex here. :-)
        item = str(int(item))
    elif not isinstance(item, (str, type(None))):
        raise Exception("Invalid autocheck: Wrong item type: %r" % item)

    try:
        # Pre 1.7 check plugins had dots in the check plugin name. With the new check API in
        # 1.7 they are replaced by '_', renaming e.g. 'cpu.loads' to 'cpu_loads'.
        plugin_name = CheckPluginName(maincheckify(check_plugin_name))
    except Exception:
        raise Exception("Invalid autocheck: Wrong check plugin name: %r" % check_plugin_name)

    try:
        description = service_description(hostname, plugin_name, item)
    except Exception:
        return None  # ignore

    return Service(
        check_plugin_name=plugin_name,
        item=item,
        description=description,
        parameters=parameters,
        service_labels=_parse_discovered_service_label_from_dict(dict_service_labels),
    )


def _parse_pre_16_tuple_autocheck_entry(entry: Tuple) -> Union[List, Tuple]:
    # drop hostname, legacy format with host in first column
    parts = entry[1:] if len(entry) == 4 else entry

    if len(parts) != 3:
        raise Exception("Invalid autocheck: Wrong length %d instead of 3" % len(parts))
    return parts


def _parse_dict_autocheck_entry(entry: Dict) -> Tuple:
    if set(entry) != {"check_plugin_name", "item", "parameters", "service_labels"}:
        raise MKGeneralException("Invalid autocheck: Wrong keys found: %r" % list(entry))

    return entry["check_plugin_name"], entry["item"], entry["parameters"], entry["service_labels"]


def _parse_discovered_service_label_from_dict(dict_service_labels: Dict) -> DiscoveredServiceLabels:
    labels = DiscoveredServiceLabels()
    if not isinstance(dict_service_labels, dict):
        return labels
    for key, value in dict_service_labels.items():
        if key is not None:
            labels.add_label(ServiceLabel(
                ensure_str(key),
                ensure_str(value),
            ))
    return labels


def set_autochecks_of_real_hosts(hostname: HostName, new_services: Sequence[Service],
                                 service_description: GetServiceDescription) -> None:
    new_autochecks: List[Service] = []

    # write new autochecks file, but take parameters from existing ones
    # for those checks which are kept
    for existing_service in parse_autochecks_file(hostname, service_description):
        if existing_service in new_services:
            new_autochecks.append(existing_service)

    for discovered_service in new_services:
        if discovered_service not in new_autochecks:
            new_autochecks.append(discovered_service)

    # write new autochecks file for that host
    save_autochecks_file(
        hostname,
        new_autochecks,
    )


def set_autochecks_of_cluster(nodes: List[HostName], hostname: HostName,
                              new_services: Sequence[Service],
                              host_of_clustered_service: HostOfClusteredService,
                              service_description: GetServiceDescription) -> None:
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    for node in nodes:
        new_autochecks: List[Service] = []
        for existing_service in parse_autochecks_file(node, service_description):
            if hostname != host_of_clustered_service(node, existing_service.description):
                new_autochecks.append(existing_service)

        for discovered_service in new_services:
            new_autochecks.append(discovered_service)

        new_autochecks = _remove_duplicate_autochecks(new_autochecks)

        # write new autochecks file for that host
        save_autochecks_file(node, new_autochecks)

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    remove_autochecks_file(hostname)


def _remove_duplicate_autochecks(autochecks: Sequence[Service]) -> List[Service]:
    """ Cleanup routine. Earlier versions (<1.6.0p8) may have introduced duplicates in the autochecks file"""
    seen: Set[Service] = set()
    cleaned_autochecks = []
    for service in autochecks:
        if service not in seen:
            seen.add(service)
            cleaned_autochecks.append(service)
    return cleaned_autochecks


def save_autochecks_file(
    hostname: HostName,
    services: Sequence[Service],
) -> None:
    path = _autochecks_path_for(hostname)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = []
    content.append("[")
    for service in sorted(services, key=lambda s: (s.check_plugin_name, s.item)):
        content.append("  %s," % service.dump_autocheck())
    content.append("]\n")
    store.save_file(path, "\n".join(content))


def remove_autochecks_file(hostname: HostName) -> None:
    try:
        _autochecks_path_for(hostname).unlink()
    except OSError:
        pass


def remove_autochecks_of_host(hostname: HostName, host_of_clustered_service: HostOfClusteredService,
                              service_description: GetServiceDescription) -> int:
    removed = 0
    new_items: List[Service] = []
    for existing_service in parse_autochecks_file(hostname, service_description):
        if hostname != host_of_clustered_service(hostname, existing_service.description):
            new_items.append(existing_service)
        else:
            removed += 1
    save_autochecks_file(hostname, new_items)
    return removed
