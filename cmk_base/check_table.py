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
"""Code for computing the table of checks of hosts."""

from typing import Union, TypeVar, Iterable, Text, Optional, Dict, Tuple, Any, List  # pylint: disable=unused-import

from cmk.utils.exceptions import MKGeneralException

import cmk_base
import cmk_base.config as config
import cmk_base.item_state as item_state
import cmk_base.check_utils
import cmk_base.check_api_utils as check_api_utils
from cmk_base.check_utils import (  # pylint: disable=unused-import
    Item, CheckParameters, CheckPluginName, CheckTable, Service)

# Add WATO-configured explicit checks to (possibly empty) checks
# statically defined in checks.
#def add_wato_static_checks_to_checks():


# TODO: This is just a first cleanup step: Continue cleaning this up.
# - Check all call sites and cleanup the different
# - Make this a helper object of HostConfig?
class HostCheckTable(object):
    def __init__(self, config_cache, host_config):
        # type: (config.ConfigCache, config.HostConfig) -> None
        super(HostCheckTable, self).__init__()
        self._config_cache = config_cache
        self._host_config = host_config

        self._is_checkname_valid_cache = {}  # type: Dict[str, bool]

    def get(self, remove_duplicates, use_cache, skip_autochecks, filter_mode, skip_ignored):
        # type: (bool, bool, bool, Optional[str], bool) -> CheckTable
        """Returns check table for a specific host

        Format of check table is: {(checkname, item): (params, description)}

        filter_mode: None                -> default, returns only checks for this host
        filter_mode: "only_clustered"    -> returns only checks belonging to clusters
        filter_mode: "include_clustered" -> returns checks of own host, including clustered checks
        """
        # TODO: Clean them up
        self.remove_duplicates = remove_duplicates
        self.use_cache = use_cache
        self.skip_autochecks = skip_autochecks
        self.filter_mode = filter_mode
        self.skip_ignored = skip_ignored
        hostname = self._host_config.hostname

        if self._host_config.is_ping_host:
            skip_autochecks = True

        # speed up multiple lookup of same host
        check_table_cache = self._config_cache.check_table_cache
        table_cache_id = hostname, filter_mode

        if not skip_autochecks and use_cache and table_cache_id in check_table_cache:
            # TODO: The whole is_dual_host handling needs to be cleaned up. The duplicate checking
            #       needs to be done in all cases since a host can now have a lot of different data
            #       sources.
            if remove_duplicates and self._host_config.is_dual_host:
                return remove_duplicate_checks(check_table_cache[table_cache_id])
            return check_table_cache[table_cache_id]

        check_table = {}  # type: CheckTable

        # Now process all entries that are specific to the host
        # in search (single host) or that might match the host.
        if not skip_autochecks:
            for service in self._config_cache.get_autochecks_of(hostname):
                check_table.update(self._handle_service(service))

        for service in self._get_static_check_entries(self._host_config):
            check_table.update(self._handle_service(service))

        # Now add checks a cluster might receive from its nodes
        if self._host_config.is_cluster:
            check_table.update(self._get_clustered_services(hostname, skip_autochecks))

        # Remove dependencies to non-existing services
        all_descr = set(
            [descr for ((_checkname, _item), (_params, descr, _deps)) in check_table.iteritems()])
        for (_checkname, _item), (_params, _descr, deps) in check_table.iteritems():
            deeps = deps[:]
            del deps[:]
            for d in deeps:
                if d in all_descr:
                    deps.append(d)

        if not skip_autochecks and use_cache:
            check_table_cache[table_cache_id] = check_table

        if remove_duplicates:
            return remove_duplicate_checks(check_table)
        return check_table

    def _get_static_check_entries(self, host_config):
        # type: (config.HostConfig) -> List[Service]
        entries = []  # type: List[Service]
        for _checkgroup_name, check_plugin_name, item, params in host_config.static_checks:
            # Make sure, that for dictionary based checks at least those keys
            # defined in the factory settings are present in the parameters
            # TODO: Isn't this done during checking for all checks in more generic code?
            if isinstance(params, dict) and check_plugin_name in config.check_info:
                def_levels_varname = config.check_info[check_plugin_name].get(
                    "default_levels_variable")
                if def_levels_varname:
                    for key, value in config.factory_settings.get(def_levels_varname, {}).items():
                        if key not in params:
                            params[key] = value

            descr = config.service_description(host_config.hostname, check_plugin_name, item)
            entries.append(Service(check_plugin_name, item, descr, params))

        # Note: We need to reverse the order of the static_checks. This is
        # because users assume that earlier rules have precedence over later
        # ones. For static checks that is important if there are two rules for
        # a host with the same combination of check type and item.
        return list(reversed(entries))

    def _handle_service(self, service):
        # type: (Service) -> CheckTable
        check_table = {}  # type: CheckTable
        hostname = self._host_config.hostname

        if not self._is_checkname_valid(service.check_plugin_name):
            return {}

        if self.skip_ignored and config.service_ignored(hostname, service.check_plugin_name,
                                                        service.description):
            return {}

        if not self._host_config.part_of_clusters:
            svc_is_mine = True
        else:
            svc_is_mine = hostname == self._config_cache.host_of_clustered_service(
                hostname, service.description, part_of_clusters=self._host_config.part_of_clusters)

        if self.filter_mode is None and not svc_is_mine:
            return {}

        elif self.filter_mode == "only_clustered" and svc_is_mine:
            return {}

        deps = config.service_depends_on(hostname, service.description)
        check_table[(service.check_plugin_name, service.item)] = (service.parameters,
                                                                  service.description, deps)

        return check_table

    def _is_checkname_valid(self, checkname):
        if checkname in self._is_checkname_valid_cache:
            return self._is_checkname_valid_cache[checkname]

        passed = True
        if checkname not in config.check_info:
            passed = False

        # Skip SNMP checks for non SNMP hosts (might have been discovered before with other
        # agent setting. Remove them without rediscovery). Same for agent based checks.
        elif not self._host_config.is_snmp_host and self._config_cache.is_snmp_check(checkname) and \
           (not self._host_config.has_management_board or self._host_config.management_protocol != "snmp"):
            passed = False

        elif not self._host_config.is_agent_host and self._config_cache.is_tcp_check(checkname):
            passed = False

        self._is_checkname_valid_cache[checkname] = passed
        return passed

    def _get_clustered_services(self, hostname, skip_autochecks):
        # type: (str, bool) -> CheckTable
        check_table = {}  # type: CheckTable
        for node in self._host_config.nodes or []:
            # TODO: Cleanup this to work exactly like the logic above (for a single host)
            node_config = self._config_cache.get_host_config(node)
            node_checks = self._get_static_check_entries(node_config)
            if not skip_autochecks:
                node_checks += self._config_cache.get_autochecks_of(node)

            for service in node_checks:
                if self._config_cache.host_of_clustered_service(node,
                                                                service.description) != hostname:
                    continue

                cluster_params = config.compute_check_parameters(hostname,
                                                                 service.check_plugin_name,
                                                                 service.item, service.parameters)
                cluster_service = Service(service.check_plugin_name, service.item,
                                          service.description, cluster_params,
                                          service.service_labels)
                check_table.update(self._handle_service(cluster_service))
        return check_table


def get_check_table(hostname,
                    remove_duplicates=False,
                    use_cache=True,
                    skip_autochecks=False,
                    filter_mode=None,
                    skip_ignored=True):
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    table = HostCheckTable(config_cache, host_config)
    return table.get(remove_duplicates, use_cache, skip_autochecks, filter_mode, skip_ignored)


def get_precompiled_check_table(hostname,
                                remove_duplicates=True,
                                filter_mode=None,
                                skip_ignored=True):
    """The precompiled check table is somehow special compared to the regular check table.

    a) It is sorted by the service dependencies (which are only relevant for Nagios)
    b) More important: Some special checks pre-compue a new set of parameters
       using a plugin specific precompile_params function. It's purpose is to
       perform time consuming ruleset evaluations once without the need to perform
       it during each check execution.

       The effective check parameters are calculated in these steps:

       1. Read from config
         a) autochecks + cmk_base.config.compute_check_parameters()
         b) static checks

       2. Execute the precompile params function
         The precompile_params function can base on the "params" from a static check or
         autocheck and computes a new "params".

         This is the last step that may be cached across the single executions.

       3. Execute the check
         During check execution will update the check parameters once more with
         checking.determine_check_params() right before execution the check.
    """
    host_checks = get_sorted_check_table(hostname,
                                         remove_duplicates,
                                         filter_mode=filter_mode,
                                         skip_ignored=skip_ignored)
    precomp_table = []
    for check_plugin_name, item, params, description in host_checks:
        # make these globals available to the precompile function
        check_api_utils.set_service(check_plugin_name, description)
        item_state.set_item_state_prefix(check_plugin_name, item)

        params = get_precompiled_check_parameters(hostname, item, params, check_plugin_name)
        precomp_table.append(
            (check_plugin_name, item, params, description))  # deps not needed while checking
    return precomp_table


def get_precompiled_check_parameters(hostname, item, params, check_plugin_name):
    precomp_func = config.precompile_params.get(check_plugin_name)
    if precomp_func:
        return precomp_func(hostname, item, params)
    return params


def remove_duplicate_checks(check_table):
    # type: (CheckTable) -> CheckTable
    have_with_tcp = {}  # type: Dict[Text, Tuple[CheckPluginName, Item]]
    have_with_snmp = {}  # type: Dict[Text, Tuple[CheckPluginName, Item]]
    without_duplicates = {}  # type: CheckTable
    for key, value in check_table.iteritems():
        checkname = key[0]
        descr = value[1]
        if cmk_base.check_utils.is_snmp_check(checkname):
            if descr in have_with_tcp:
                continue
            have_with_snmp[descr] = key
        else:
            if descr in have_with_snmp:
                snmp_key = have_with_snmp[descr]
                del without_duplicates[snmp_key]
                del have_with_snmp[descr]
            have_with_tcp[descr] = key
        without_duplicates[key] = value
    return without_duplicates


def get_needed_check_names(hostname, remove_duplicates=False, filter_mode=None, skip_ignored=True):
    # type: (str, bool, Optional[str], bool) -> List[str]
    return [
        e[0] for e in get_check_table(hostname,
                                      remove_duplicates=remove_duplicates,
                                      filter_mode=filter_mode,
                                      skip_ignored=skip_ignored)
    ]


# remove_duplicates: Automatically remove SNMP based checks
# if there already is a TCP based one with the same
# description. E.g: df vs hr_fs.
# TODO: Clean this up!
def get_sorted_check_table(hostname, remove_duplicates=False, filter_mode=None, skip_ignored=True):
    # Convert from dictionary into simple tuple list. Then sort
    # it according to the service dependencies.
    unsorted = [(checkname, item, params, descr, deps)
                for ((checkname, item),
                     (params, descr, deps)) in get_check_table(hostname,
                                                               remove_duplicates=remove_duplicates,
                                                               filter_mode=filter_mode,
                                                               skip_ignored=skip_ignored).items()]

    unsorted.sort(key=lambda x: x[3])

    ordered = []
    while len(unsorted) > 0:
        unsorted_descrs = set([entry[3] for entry in unsorted])
        left = []
        at_least_one_hit = False
        for check in unsorted:
            deps_fulfilled = True
            for dep in check[4]:  # deps
                if dep in unsorted_descrs:
                    deps_fulfilled = False
                    break
            if deps_fulfilled:
                ordered.append(check[:-1])
                at_least_one_hit = True
            else:
                left.append(check)
        if len(left) == 0:
            break
        if not at_least_one_hit:
            raise MKGeneralException("Cyclic service dependency of host %s. Problematic are: %s" %
                                     (hostname, ",".join(unsorted_descrs)))
        unsorted = left
    return ordered
