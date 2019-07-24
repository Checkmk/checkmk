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

from typing import Any, Dict, Union, Tuple, Text, Optional, List  # pylint: disable=unused-import
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
        self._autochecks = {}  # type: Dict[str, List[Service]]

    def get_autochecks_of(self, hostname):
        # type: (str) -> List[Service]
        if hostname in self._autochecks:
            return self._autochecks[hostname]

        result = self._read_autochecks_of(hostname)
        self._autochecks[hostname] = result
        return result

    def discovered_labels_of(self, hostname, service_desc):
        # type: (str, Text) -> DiscoveredServiceLabels
        for service in self.get_autochecks_of(hostname):
            # TODO: Performance! Would be better lookup this from a dict
            if service.description == service_desc:
                return service.service_labels
        return DiscoveredServiceLabels()

    # TODO: use store.load_data_from_file()
    # TODO: Common code with parse_autochecks_file? Cleanup.
    def _read_autochecks_of(self, hostname):
        # type: (str) -> List[Service]
        """Read automatically discovered checks of one host"""
        basedir = cmk.utils.paths.autochecks_dir
        filepath = basedir + '/' + hostname + '.mk'

        if not os.path.exists(filepath):
            return []

        check_config = config.get_check_variables()
        try:
            cmk_base.console.vverbose("Loading autochecks from %s\n", filepath)
            autochecks_raw = eval(
                file(filepath).read().decode("utf-8"), check_config,
                check_config)  # type: List[Tuple[CheckPluginName, Item, CheckParameters]]
        except SyntaxError as e:
            cmk_base.console.verbose("Syntax error in file %s: %s\n",
                                     filepath,
                                     e,
                                     stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return []
        except Exception as e:
            cmk_base.console.verbose("Error in file %s:\n%s\n", filepath, e, stream=sys.stderr)
            if cmk.utils.debug.enabled():
                raise
            return []

        autochecks = []
        for entry in autochecks_raw:
            if isinstance(entry, tuple):
                check_plugin_name, item, parameters = self._load_pre_16_tuple_autocheck(entry)
                service_labels = DiscoveredServiceLabels()
            else:
                check_plugin_name, item, parameters, service_labels = self._load_dict_autocheck(
                    entry)

            # With Check_MK 1.2.7i3 items are now defined to be unicode strings. Convert
            # items from existing autocheck files for compatibility. TODO remove this one day
            if isinstance(item, str):
                item = config.decode_incoming_string(item)

            if not isinstance(check_plugin_name, six.string_types):
                raise MKGeneralException("Invalid entry '%r' in check table of host '%s': "
                                         "The check type must be a string." % (entry, hostname))

            try:
                description = config.service_description(hostname, check_plugin_name, item)
            except Exception:
                continue  # ignore

            autochecks.append(
                Service(
                    check_plugin_name=check_plugin_name,
                    item=item,
                    description=description,
                    parameters=config.compute_check_parameters(hostname, check_plugin_name, item,
                                                               parameters),
                    service_labels=service_labels,
                ))
        return autochecks

    def _load_pre_16_tuple_autocheck(self, entry):
        # type: (Tuple[CheckPluginName, Item, CheckParameters]) -> Tuple[CheckPluginName, Item, CheckParameters]
        if len(entry) == 4:  # old format where hostname is at the first place
            entry = entry[1:]  # type: ignore
        check_plugin_name, item, parameters = entry
        return check_plugin_name, item, parameters

    def _load_dict_autocheck(self, entry):
        # type: (Dict) -> Tuple[CheckPluginName, Item, CheckParameters, DiscoveredServiceLabels]
        labels = DiscoveredServiceLabels()
        for label_id, label_value in entry["service_labels"].items():
            labels.add_label(ServiceLabel(label_id, label_value))
        return entry["check_plugin_name"], entry["item"], entry["parameters"], labels


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
    except SyntaxError:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Unable to parse autochecks file %s" % (path))

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

    if isinstance(ast_parameters_unresolved, ast.Name):
        # Keep check variable names as they are: No evaluation of check parameters
        parameters_unresolved = ast_parameters_unresolved.id
    else:
        # Other structures, like dicts, lists and so on should also be loaded as repr() str
        # instead of an interpreted structure
        parameters_unresolved = repr(
            eval(compile(ast.Expression(ast_parameters_unresolved), filename="<ast>", mode="eval")))

    try:
        description = config.service_description(hostname, check_plugin_name, item)
    except Exception:
        return None  # ignore

    return DiscoveredService(
        check_plugin_name,
        item,
        description,
        parameters_unresolved,
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
