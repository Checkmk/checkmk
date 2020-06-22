#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Caring about persistance of the discovered services (aka autochecks)"""

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import sys
import ast
from pathlib import Path

from six import ensure_str

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckVariables, PluginName
from cmk.utils.log import console

from cmk.base.discovered_labels import DiscoveredServiceLabels, ServiceLabel
from cmk.utils.type_defs import HostName, ServiceName
from cmk.base.check_utils import CheckPluginName, CheckParameters, DiscoveredService, Item, Service

ComputeCheckParameters = Callable[[HostName, CheckPluginName, Item, CheckParameters],
                                  Optional[CheckParameters]]
GetCheckVariables = Callable[[], CheckVariables]
GetServiceDescription = Callable[[HostName, Union[CheckPluginName, PluginName], Item], ServiceName]
HostOfClusteredService = Callable[[HostName, str], str]


class AutochecksManager:
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""
    def __init__(self):
        # type: () -> None
        super(AutochecksManager, self).__init__()
        self._autochecks = {}  # type: Dict[HostName, List[Service]]
        # Extract of the autochecks: This cache is populated either on the way while
        # processing get_autochecks_of() or when directly calling discovered_labels_of().
        self._discovered_labels_of = {}  # type: Dict[HostName, Dict[str, DiscoveredServiceLabels]]
        self._raw_autochecks_cache = {}  # type: Dict[HostName, List[Service]]

    def get_autochecks_of(self, hostname, compute_check_parameters, service_description,
                          get_check_variables):
        # type: (str, ComputeCheckParameters, GetServiceDescription, GetCheckVariables) -> List[Service]
        if hostname not in self._autochecks:
            self._autochecks[hostname] = self._get_autochecks_of_uncached(
                hostname, compute_check_parameters, service_description, get_check_variables)
        return self._autochecks[hostname]

    def _get_autochecks_of_uncached(self, hostname, compute_check_parameters, service_description,
                                    get_check_variables):
        # type: (HostName, ComputeCheckParameters, GetServiceDescription, GetCheckVariables) -> List[Service]
        """Read automatically discovered checks of one host"""
        return [
            Service(
                check_plugin_name=service.check_plugin_name,
                item=service.item,
                description=service.description,
                parameters=compute_check_parameters(hostname, service.check_plugin_name,
                                                    service.item, service.parameters),
                service_labels=service.service_labels,
            ) for service in self._read_raw_autochecks(hostname, service_description,
                                                       get_check_variables)
        ]

    def discovered_labels_of(self, hostname, service_desc, service_description,
                             get_check_variables):
        # type: (HostName, ServiceName, GetServiceDescription, GetCheckVariables) -> DiscoveredServiceLabels
        if hostname not in self._discovered_labels_of:
            # Only read the raw autochecks here, do not compute the effective
            # check parameters. The latter would involve ruleset matching which
            # in turn would require already computed labels.
            self._read_raw_autochecks(hostname, service_description, get_check_variables)
        if service_desc not in self._discovered_labels_of[hostname]:
            self._discovered_labels_of[hostname][service_desc] = DiscoveredServiceLabels()
        return self._discovered_labels_of[hostname][service_desc]

    def _read_raw_autochecks(self, hostname, service_description, get_check_variables):
        # type: (HostName, GetServiceDescription, GetCheckVariables) -> List[Service]
        if hostname not in self._raw_autochecks_cache:
            self._raw_autochecks_cache[hostname] = self._read_raw_autochecks_uncached(
                hostname, service_description, get_check_variables)
            # create cache from autocheck labels
            self._discovered_labels_of.setdefault(hostname, {})
            for service in self._raw_autochecks_cache[hostname]:
                self._discovered_labels_of[hostname][service.description] = service.service_labels
        return self._raw_autochecks_cache[hostname]

    # TODO: use store.load_object_from_file()
    # TODO: Common code with parse_autochecks_file? Cleanup.
    def _read_raw_autochecks_uncached(self, hostname, service_description, get_check_variables):
        # type: (HostName, GetServiceDescription, GetCheckVariables) -> List[Service]
        """Read automatically discovered checks of one host"""
        result = []  # type: List[Service]
        path = _autochecks_path_for(hostname)
        if not path.exists():
            return result

        check_variables = get_check_variables()
        try:
            console.vverbose("Loading autochecks from %s\n", path)
            with path.open(encoding="utf-8") as f:
                autochecks_raw = eval(f.read(), check_variables,
                                      check_variables)  # type: List[Dict]
        except SyntaxError as e:
            console.verbose("Syntax error in file %s: %s\n", path, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return result
        except Exception as e:
            console.verbose("Error in file %s:\n%s\n", path, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return result

        for entry in autochecks_raw:
            if isinstance(entry, tuple):
                raise MKGeneralException(
                    "Invalid check entry '%r' of host '%s' (%s) found. This "
                    "entry is in pre Checkmk 1.6 format and needs to be converted. This is "
                    "normally done by \"cmk-update-config -v\" during \"omd update\". Please "
                    "execute \"cmk-update-config -v\" for convertig the old configuration." %
                    (entry, hostname, path))

            labels = DiscoveredServiceLabels()
            for label_id, label_value in entry["service_labels"].items():
                labels.add_label(ServiceLabel(label_id, label_value))

            # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
            # items from existing autocheck files for compatibility. TODO remove this one day
            item = entry["item"]

            if not isinstance(entry["check_plugin_name"], str):
                raise MKGeneralException("Invalid entry '%r' in check table of host '%s': "
                                         "The check type must be a string." % (entry, hostname))

            check_plugin_name = str(entry["check_plugin_name"])

            try:
                description = service_description(hostname, check_plugin_name, item)
            except Exception:
                continue  # ignore

            result.append(
                Service(
                    check_plugin_name=check_plugin_name,
                    item=item,
                    description=description,
                    parameters=entry["parameters"],
                    service_labels=labels,
                ))

        return result


def _autochecks_path_for(hostname):
    # type: (HostName) -> Path
    return Path(cmk.utils.paths.autochecks_dir, hostname + ".mk")


def has_autochecks(hostname):
    # type: (HostName) -> bool
    return _autochecks_path_for(hostname).exists()


def parse_autochecks_file(hostname, service_description):
    # type: (HostName, GetServiceDescription) -> List[DiscoveredService]
    """Read autochecks, but do not compute final check parameters"""
    services = []  # type: List[DiscoveredService]
    path = _autochecks_path_for(hostname)
    if not path.exists():
        return services

    try:
        with path.open(encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Unable to parse autochecks file %s: %s" % (path, e))

    for child in ast.iter_child_nodes(tree):
        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        if not isinstance(child, ast.Expr) and isinstance(
                child.value,  # type: ignore[attr-defined]
                ast.List):
            continue  # We only care about top level list

        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        for entry in child.value.elts:  # type: ignore[attr-defined]
            if not isinstance(entry, (ast.Tuple, ast.Dict)):
                continue

            service = _parse_autocheck_entry(hostname, entry, service_description)
            if service:
                services.append(service)

    return services


def _parse_autocheck_entry(hostname, entry, service_description):
    # type: (HostName, Union[ast.Tuple, ast.Dict], GetServiceDescription) -> Optional[DiscoveredService]
    if isinstance(entry, ast.Tuple):
        ast_check_plugin_name, ast_item, ast_parameters_unresolved = _parse_pre_16_tuple_autocheck_entry(
            entry)
        ast_service_labels = ast.Dict()
    elif isinstance(entry, ast.Dict):
        ast_check_plugin_name, ast_item, ast_parameters_unresolved, ast_service_labels = \
            _parse_dict_autocheck_entry(entry)
    else:
        raise Exception("Invalid autocheck: Wrong type: %r" % entry)

    if not isinstance(ast_check_plugin_name, ast.Str):
        raise Exception("Invalid autocheck: Wrong check plugin type: %r" % ast_check_plugin_name)
    check_plugin_name = ast_check_plugin_name.s

    item = None  # type: Item
    if isinstance(ast_item, ast.Str):
        item = ast_item.s
    elif isinstance(ast_item, ast.Num) and isinstance(ast_item.n, (int, float)):
        # NOTE: We exclude complex here. :-)
        item = "%s" % int(ast_item.n)
    elif _ast_node_is_none(ast_item):
        item = None
    else:
        raise Exception("Invalid autocheck: Wrong item type: %r" % ast_item)

    try:
        description = service_description(hostname, check_plugin_name, item)
    except Exception:
        return None  # ignore

    return DiscoveredService(
        check_plugin_name,
        item,
        description,
        _parse_unresolved_parameters_from_ast(ast_parameters_unresolved),
        service_labels=_parse_discovered_service_label_from_ast(ast_service_labels))


def _ast_node_is_none(node):
    return isinstance(node, ast.NameConstant) and node.value is None


def _parse_pre_16_tuple_autocheck_entry(entry):
    # type: (ast.Tuple) -> Union[List, Tuple]
    # drop hostname, legacy format with host in first column
    parts = entry.elts[1:] if len(entry.elts) == 4 else entry.elts

    if len(parts) != 3:
        raise Exception("Invalid autocheck: Wrong length %d instead of 3" % len(parts))
    return parts


def _parse_dict_autocheck_entry(entry):
    # type: (ast.Dict) -> Tuple
    values = {}  # type: Dict[str, Any]
    for index, key in enumerate(entry.keys):
        if isinstance(key, ast.Str):
            values[key.s] = entry.values[index]

    if set(values) != {"check_plugin_name", "item", "parameters", "service_labels"}:
        raise MKGeneralException("Invalid autocheck: Wrong keys found: %r" % list(values))

    return values["check_plugin_name"], values["item"], values["parameters"], values[
        "service_labels"]


def _parse_unresolved_parameters_from_ast(ast_parameters_unresolved):
    # type: (Any) -> str
    if isinstance(ast_parameters_unresolved, ast.Name):
        # Keep check variable names as they are: No evaluation of check parameters
        return ast_parameters_unresolved.id

    # The if64 was writing structures like this:
    # {
    #   "errors" : if_default_error_levels,
    #   "traffic" : if_default_traffic_levels,
    #   "average" : if_default_average ,
    #   "state" : "1",
    #   "speed" : 1000000000
    # }
    # where the variables are values in a dictionary. Also convert this kind of structure
    # without evaluating the variables.
    if isinstance(ast_parameters_unresolved, ast.Dict):
        values = []
        for index, key in enumerate(ast_parameters_unresolved.keys):
            if not isinstance(key, ast.Str):
                continue

            value = _parse_unresolved_parameters_from_ast(ast_parameters_unresolved.values[index])
            values.append((key.s, value))
        return "{%s}" % ", ".join(["'%s': %s" % p for p in sorted(values, key=lambda x: x[0])])

    # Other structures, like dicts, lists and so on should also be loaded as repr() str
    # instead of an interpreted structure
    return repr(
        eval(compile(ast.Expression(ast_parameters_unresolved), filename="<ast>", mode="eval")))


def _parse_discovered_service_label_from_ast(ast_service_labels):
    # type: (ast.Dict) -> DiscoveredServiceLabels
    labels = DiscoveredServiceLabels()
    if not hasattr(ast_service_labels, "keys"):
        return labels
    for key, value in zip(ast_service_labels.keys, ast_service_labels.values):
        if key is not None:
            # mypy does not get the types of the ast objects here
            labels.add_label(
                ServiceLabel(
                    ensure_str(key.s),  # type: ignore[attr-defined]
                    ensure_str(value.s),  # type: ignore[attr-defined]
                ))
    return labels


def set_autochecks_of_real_hosts(hostname, new_services, service_description):
    # type: (HostName, List[DiscoveredService], GetServiceDescription) -> None
    new_autochecks = []  # type: List[DiscoveredService]

    # write new autochecks file, but take parameters_unresolved from existing ones
    # for those checks which are kept
    for existing_service in parse_autochecks_file(hostname, service_description):
        # TODO: Need to implement a list class that realizes in / not in correctly
        if existing_service in new_services:
            new_autochecks.append(existing_service)

    for discovered_service in new_services:
        if discovered_service not in new_autochecks:
            new_autochecks.append(discovered_service)

    # write new autochecks file for that host
    save_autochecks_file(hostname, new_autochecks)


def set_autochecks_of_cluster(nodes, hostname, new_services, host_of_clustered_service,
                              service_description):
    # type: (List[HostName], HostName, List[DiscoveredService], HostOfClusteredService, GetServiceDescription) -> None
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    for node in nodes:
        new_autochecks = []  # type: List[DiscoveredService]
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


def _remove_duplicate_autochecks(autochecks):
    # type: (List[DiscoveredService]) -> List[DiscoveredService]
    """ Cleanup routine. Earlier versions (<1.6.0p8) may have introduced duplicates in the autochecks file"""
    seen = set()  # type: Set[Tuple[CheckPluginName, Item]]
    cleaned_autochecks = []
    for service in autochecks:
        service_id = (service.check_plugin_name, service.item)
        if service_id not in seen:
            seen.add(service_id)
            cleaned_autochecks.append(service)
    return cleaned_autochecks


def save_autochecks_file(hostname, items):
    # type: (HostName, List[DiscoveredService]) -> None
    path = _autochecks_path_for(hostname)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = []
    content.append("[")
    for discovered_service in sorted(items, key=lambda s: (s.check_plugin_name, s.item)):
        content.append(
            "  {'check_plugin_name': %r, 'item': %r, 'parameters': %s, 'service_labels': %r}," %
            (discovered_service.check_plugin_name, discovered_service.item,
             discovered_service.parameters_unresolved, discovered_service.service_labels.to_dict()))
    content.append("]\n")
    store.save_file(path, "\n".join(content))


def remove_autochecks_file(hostname):
    # type: (HostName) -> None
    try:
        _autochecks_path_for(hostname).unlink()
    except OSError:
        pass


def remove_autochecks_of_host(hostname, host_of_clustered_service, service_description):
    # type: (HostName, HostOfClusteredService, GetServiceDescription) -> int
    removed = 0
    new_items = []  # type: List[DiscoveredService]
    for existing_service in parse_autochecks_file(hostname, service_description):
        if hostname != host_of_clustered_service(hostname, existing_service.description):
            new_items.append(existing_service)
        else:
            removed += 1
    save_autochecks_file(hostname, new_items)
    return removed
