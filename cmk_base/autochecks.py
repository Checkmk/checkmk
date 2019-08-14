#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Caring about persistance of the discovered services (aka autochecks)"""

from typing import Iterator, Any, Dict, Union, Tuple, Text, Optional, List  # pylint: disable=unused-import
import os
import sys
import ast
from pathlib2 import Path
import six

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.console
from cmk_base.discovered_labels import (
    DiscoveredServiceLabels,
    ServiceLabel,
)
from cmk_base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName, CheckParameters, DiscoveredService, Item, Service,
)


class AutochecksManager(object):
    """Read autochecks from the configuration

    Autochecks of a host are once read and cached for the whole lifetime of the
    AutochecksManager."""
    def __init__(self):
        # type: () -> None
        super(AutochecksManager, self).__init__()

        self._autochecks = {}  # type: Dict[str, List[Service]]

        # Extract of the autochecks. This cache is populated either on the way while
        # processing get_autochecks_of() or when directly calling discovered_labels_of().
        self._discovered_labels_of = {}  # type: Dict[str, Dict[Text, DiscoveredServiceLabels]]
        self._raw_autochecks_cache = {}  # type: Dict[str, List[Service]]

    def get_autochecks_of(self, hostname):
        # type: (str) -> List[Service]
        if hostname in self._autochecks:
            return self._autochecks[hostname]

        services = self._read_autochecks_of(hostname)
        self._autochecks[hostname] = services

        return services

    def discovered_labels_of(self, hostname, service_desc):
        # type: (str, Text) -> DiscoveredServiceLabels
        # Check if the autochecks for the given hostname were already read
        # The service in question might have no entry in the autochecks file
        # In this scenario it gets an empty DiscoveredServiceLabels entry
        host_results = self._discovered_labels_of.get(hostname)
        if host_results is not None:
            service_result = host_results.get(service_desc)
            if service_result is None:
                host_results[service_desc] = DiscoveredServiceLabels()
            return host_results[service_desc]

        # Only read the raw autochecks here. Do not compute the effective check parameters,
        # because that would invole ruleset matching which in would require the labels to
        # be already computed.
        # The following function reads the autochecks and populates the the discovered labels cache
        self._read_raw_autochecks_cached(hostname)
        result = self._discovered_labels_of.get(hostname, {}).get(service_desc)
        if result is None:
            # The service was not present in the autochecks, create an empty instance
            result = DiscoveredServiceLabels()
            self._discovered_labels_of.setdefault(hostname, {})[service_desc] = result

        return result

    def _read_autochecks_of(self, hostname):
        # type: (str) -> List[Service]
        """Read automatically discovered checks of one host"""
        autochecks = []
        for service in self._read_raw_autochecks_cached(hostname):
            autochecks.append(
                Service(
                    check_plugin_name=service.check_plugin_name,
                    item=service.item,
                    description=service.description,
                    parameters=config.compute_check_parameters(hostname, service.check_plugin_name,
                                                               service.item, service.parameters),
                    service_labels=service.service_labels,
                ))
        return autochecks

    def _read_raw_autochecks_cached(self, hostname):
        if hostname in self._raw_autochecks_cache:
            return self._raw_autochecks_cache[hostname]

        raw_autochecks = self._read_raw_autochecks_of(hostname)
        self._raw_autochecks_cache[hostname] = raw_autochecks

        # create cache from autocheck labels
        self._discovered_labels_of.setdefault(hostname, {})
        for service in raw_autochecks:
            self._discovered_labels_of[hostname][service.description] = service.service_labels

        return raw_autochecks

    # TODO: use store.load_data_from_file()
    # TODO: Common code with parse_autochecks_file? Cleanup.
    def _read_raw_autochecks_of(self, hostname):
        # type: (str) -> List[Service]
        """Read automatically discovered checks of one host"""
        basedir = cmk.utils.paths.autochecks_dir
        filepath = basedir + '/' + hostname + '.mk'

        result = []  # type: List[Service]
        if not os.path.exists(filepath):
            return result

        check_config = config.get_check_variables()
        try:
            cmk_base.console.vverbose("Loading autochecks from %s\n", filepath)
            autochecks_raw = eval(
                file(filepath).read().decode("utf-8"), check_config,
                check_config)  # type: List[Dict]
        except SyntaxError as e:
            cmk_base.console.verbose("Syntax error in file %s: %s\n",
                                     filepath,
                                     e,
                                     stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return result
        except Exception as e:
            cmk_base.console.verbose("Error in file %s:\n%s\n", filepath, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return result

        for entry in autochecks_raw:
            labels = DiscoveredServiceLabels()
            for label_id, label_value in entry["service_labels"].items():
                labels.add_label(ServiceLabel(label_id, label_value))

            # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
            # items from existing autocheck files for compatibility. TODO remove this one day
            item = entry["item"]
            if isinstance(item, str):
                item = config.decode_incoming_string(item)

            if not isinstance(entry["check_plugin_name"], six.string_types):
                raise MKGeneralException("Invalid entry '%r' in check table of host '%s': "
                                         "The check type must be a string." % (entry, hostname))

            try:
                description = config.service_description(hostname, entry["check_plugin_name"], item)
            except Exception:
                continue  # ignore

            result.append(
                Service(
                    check_plugin_name=str(entry["check_plugin_name"]),
                    item=item,
                    description=description,
                    parameters=entry["parameters"],
                    service_labels=labels,
                ))

        return result


def resolve_paramstring(check_plugin_name, parameters_unresolved):
    # type: (str, str) -> CheckParameters
    """Translates a parameter string (read from autochecks) to it's final value
    (according to the current configuration)"""
    check_context = config.get_check_context(check_plugin_name)
    # TODO: Can't we simply access check_context[paramstring]?
    return eval(parameters_unresolved, check_context, check_context)


def parse_autochecks_file(hostname):
    # type: (str) -> List[DiscoveredService]
    """Read autochecks, but do not compute final check parameters"""
    path = "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, hostname)
    if not os.path.exists(path):
        return []

    services = []  # type: List[DiscoveredService]

    try:
        tree = ast.parse(open(path).read())
    except SyntaxError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Unable to parse autochecks file %s: %s" % (path, e))

    for child in ast.iter_child_nodes(tree):
        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        if not isinstance(child, ast.Expr) and isinstance(child.value, ast.List):  # type: ignore
            continue  # We only care about top level list

        # Mypy is wrong about this: [mypy:] "AST" has no attribute "value"
        for entry in child.value.elts:  # type: ignore
            if not isinstance(entry, (ast.Tuple, ast.Dict)):
                continue

            service = _parse_autocheck_entry(hostname, entry)
            if service:
                services.append(service)

    return services


def _parse_autocheck_entry(hostname, entry):
    # type: (str, Union[ast.Tuple, ast.Dict]) -> Optional[DiscoveredService]
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
    elif isinstance(ast_item, ast.Num):
        item = int(ast_item.n)
    elif isinstance(ast_item, ast.Name) and ast_item.id == "None":
        item = None
    else:
        raise Exception("Invalid autocheck: Wrong item type: %r" % ast_item)

    # With Check_MK 1.2.7i3 items are now defined to be unicode
    # strings. Convert items from existing autocheck files for
    # compatibility.
    if isinstance(item, str):
        item = config.decode_incoming_string(item)

    try:
        description = config.service_description(hostname, check_plugin_name, item)
    except Exception:
        return None  # ignore

    return DiscoveredService(
        check_plugin_name,
        item,
        description,
        _parse_unresolved_parameters_from_ast(ast_parameters_unresolved),
        service_labels=_parse_discovered_service_label_from_ast(ast_service_labels))


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

    if set(values.keys()) != {"check_plugin_name", "item", "parameters", "service_labels"}:
        raise MKGeneralException("Invalid autocheck: Wrong keys found: %r" % values.keys())

    return values["check_plugin_name"], values["item"], values["parameters"], values[
        "service_labels"]


def _parse_unresolved_parameters_from_ast(ast_parameters_unresolved):
    if isinstance(ast_parameters_unresolved, ast.Name):
        # Keep check variable names as they are: No evaluation of check parameters
        parameters_unresolved = ast_parameters_unresolved.id
    else:
        # Other structures, like dicts, lists and so on should also be loaded as repr() str
        # instead of an interpreted structure
        parameters_unresolved = repr(
            eval(compile(ast.Expression(ast_parameters_unresolved), filename="<ast>", mode="eval")))

    return parameters_unresolved


def _parse_discovered_service_label_from_ast(ast_service_labels):
    # type: (ast.Dict) -> DiscoveredServiceLabels
    labels = DiscoveredServiceLabels()

    # mypy does not get the types of the ast objects here
    if not hasattr(ast_service_labels, "keys"):  # # type: ignore
        return labels

    for key, value in zip(ast_service_labels.keys, ast_service_labels.values):
        # mypy does not get the types of the ast objects here
        labels.add_label(ServiceLabel(key.s, value.s))  # type: ignore

    return labels


def set_autochecks_of(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """Merge existing autochecks with the given autochecks for a host and save it"""
    if host_config.is_cluster:
        _set_autochecks_of_cluster(host_config, new_items)
    else:
        _set_autochecks_of_real_hosts(host_config, new_items)


def _set_autochecks_of_real_hosts(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    new_autochecks = []  # type: List[DiscoveredService]

    # write new autochecks file, but take parameters_unresolved from existing ones
    # for those checks which are kept
    for existing_service in parse_autochecks_file(host_config.hostname):
        # TODO: Need to implement a list class that realizes in / not in correctly
        if existing_service in new_items:
            new_autochecks.append(existing_service)

    for discovered_service in new_items:
        if discovered_service not in new_autochecks:
            new_autochecks.append(discovered_service)

    # write new autochecks file for that host
    save_autochecks_file(host_config.hostname, new_autochecks)


def _set_autochecks_of_cluster(host_config, new_items):
    # type: (config.HostConfig, List[DiscoveredService]) -> None
    """A Cluster does not have an autochecks file. All of its services are located
    in the nodes instead. For clusters we cycle through all nodes remove all
    clustered service and add the ones we've got as input."""
    if not host_config.nodes:
        return

    config_cache = config.get_config_cache()

    new_autochecks = []  # type: List[DiscoveredService]
    for node in host_config.nodes:
        for existing_service in parse_autochecks_file(node):
            if host_config.hostname != config_cache.host_of_clustered_service(
                    node, existing_service.description):
                new_autochecks.append(existing_service)

        for discovered_service in new_items:
            new_autochecks.append(discovered_service)

        # write new autochecks file for that host
        save_autochecks_file(node, new_autochecks)

    # Check whether or not the cluster host autocheck files are still existant.
    # Remove them. The autochecks are only stored in the nodes autochecks files
    # these days.
    remove_autochecks_file(host_config.hostname)


def has_autochecks(hostname):
    # type: (str) -> bool
    return os.path.exists(cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk")


def save_autochecks_file(hostname, items):
    # type: (str, List[DiscoveredService]) -> None
    if not os.path.exists(cmk.utils.paths.autochecks_dir):
        os.makedirs(cmk.utils.paths.autochecks_dir)

    filepath = Path(cmk.utils.paths.autochecks_dir) / ("%s.mk" % hostname)
    content = []
    content.append("[")
    for discovered_service in sorted(items, key=lambda s: (s.check_plugin_name, s.item)):
        content.append(
            "  {'check_plugin_name': %r, 'item': %r, 'parameters': %s, 'service_labels': %r}," %
            (discovered_service.check_plugin_name, discovered_service.item,
             discovered_service.parameters_unresolved, discovered_service.service_labels.to_dict()))
    content.append("]\n")
    store.save_file(str(filepath), "\n".join(content))


def remove_autochecks_file(hostname):
    # type: (str) -> None
    filepath = cmk.utils.paths.autochecks_dir + "/" + hostname + ".mk"
    try:
        os.remove(filepath)
    except OSError:
        pass


def remove_autochecks_of(host_config):
    # type: (config.HostConfig) -> int
    """Remove all autochecks of a host while being cluster-aware

    Cluster aware means that the autocheck files of the nodes are handled. Instead
    of removing the whole file the file is loaded and only the services associated
    with the given cluster are removed."""
    removed = 0
    if host_config.nodes:
        for node_name in host_config.nodes:
            removed += _remove_autochecks_of_host(node_name)
    else:
        removed += _remove_autochecks_of_host(host_config.hostname)

    return removed


def _remove_autochecks_of_host(hostname):
    # type: (str) -> int
    removed = 0
    new_items = []  # type: List[DiscoveredService]
    config_cache = config.get_config_cache()

    old_items = parse_autochecks_file(hostname)
    for existing_service in old_items:
        if hostname != config_cache.host_of_clustered_service(hostname,
                                                              existing_service.description):
            new_items.append(existing_service)
        else:
            removed += 1
    save_autochecks_file(hostname, new_items)
    return removed
