#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

from typing import Callable, cast, Dict, Iterator, List, Optional, Set, Tuple, TypeVar

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import PluginName

from cmk.base.api.agent_based.register.check_plugins_legacy import maincheckify

import cmk.base.config as config
import cmk.base.item_state as item_state
import cmk.base.check_utils
import cmk.base.check_api_utils as check_api_utils
from cmk.utils.type_defs import HostName
from cmk.base.check_utils import (
    CheckParameters,
    CheckPluginName,
    CheckTable,
    DiscoveredCheckTable,
    Item,
    Service,
)

AbstractCheckTable = TypeVar("AbstractCheckTable", CheckTable, DiscoveredCheckTable)

# Add WATO-configured explicit checks to (possibly empty) checks
# statically defined in checks.
#def add_wato_static_checks_to_checks():


# TODO: This is just a first cleanup step: Continue cleaning this up.
# - Check all call sites and cleanup the different
# - Make this a helper object of HostConfig?
class HostCheckTable:
    def __init__(self, config_cache, host_config):
        # type: (config.ConfigCache, config.HostConfig) -> None
        super(HostCheckTable, self).__init__()
        self._config_cache = config_cache
        self._host_config = host_config

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

        if not skip_autochecks and use_cache:
            check_table_cache[table_cache_id] = check_table

        if remove_duplicates:
            return remove_duplicate_checks(check_table)
        return check_table

    def _get_static_check_entries(self, host_config):
        # type: (config.HostConfig) -> Iterator[Service]
        entries = []  # type: List[Service]
        for _checkgroup_name, check_plugin_name, item, params in host_config.static_checks:
            if config.has_timespecific_params(params):
                timespec_params = [params]
                params = {}
            else:
                timespec_params = []

            new_params = config.compute_check_parameters(host_config.hostname, check_plugin_name,
                                                         item, params)

            if timespec_params:
                params = config.set_timespecific_param_list(timespec_params, new_params)
            else:
                params = new_params

            descr = config.service_description(host_config.hostname, check_plugin_name, item)
            entries.append(Service(check_plugin_name, item, descr, params))

        # Note: We need to reverse the order of the static_checks. This is
        # because users assume that earlier rules have precedence over later
        # ones. For static checks that is important if there are two rules for
        # a host with the same combination of check type and item.
        return reversed(entries)

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

        if self.filter_mode == "only_clustered" and svc_is_mine:
            return {}

        check_table[(service.check_plugin_name, service.item)] = service

        return check_table

    def _is_checkname_valid(self, checkname):
        # type: (CheckPluginName) -> bool
        # TODO (mo): centralize maincheckify: CMK-4295
        plugin_name = PluginName(maincheckify(checkname))
        return config.get_registered_check_plugin(plugin_name) is not None

    def _get_clustered_services(self, hostname, skip_autochecks):
        # type: (str, bool) -> CheckTable
        check_table = {}  # type: CheckTable
        for node in self._host_config.nodes or []:
            # TODO: Cleanup this to work exactly like the logic above (for a single host)
            node_config = self._config_cache.get_host_config(node)
            node_checks = list(self._get_static_check_entries(node_config))
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
    # type: (str, bool, bool, bool, Optional[str], bool) -> CheckTable
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    table = HostCheckTable(config_cache, host_config)
    return table.get(remove_duplicates, use_cache, skip_autochecks, filter_mode, skip_ignored)


def get_precompiled_check_table(hostname,
                                remove_duplicates=True,
                                filter_mode=None,
                                skip_ignored=True):
    # type: (str, bool, Optional[str], bool) -> List[Service]
    """The precompiled check table is somehow special compared to the regular check table.

    a) It is sorted by the service dependencies (which are only relevant for Nagios). The
       sorting is important here to send the state updates to Nagios in the correct order.
       Sending the updates in this order gives Nagios a consistent state in a shorter time.
    b) More important: Some special checks pre-compue a new set of parameters
       using a plugin specific precompile_params function. It's purpose is to
       perform time consuming ruleset evaluations once without the need to perform
       it during each check execution.

       The effective check parameters are calculated in these steps:

       1. Read from config
         a) autochecks + cmk.base.config.compute_check_parameters()
         b) static checks

       2. Execute the precompile params function
         The precompile_params function can base on the "params" from a static check or
         autocheck and computes a new "params".

         This is the last step that may be cached across the single executions.

       3. Execute the check
         During check execution will update the check parameters once more with
         checking.legacy_determine_check_params() right before execution the check.
    """
    host_checks = _get_sorted_check_table(hostname,
                                          remove_duplicates,
                                          filter_mode=filter_mode,
                                          skip_ignored=skip_ignored)
    services = []  # type: List[Service]
    for service in host_checks:
        # make these globals available to the precompile function
        check_api_utils.set_service(service.check_plugin_name, service.description)
        item_state.set_item_state_prefix(service.check_plugin_name, service.item)

        precompiled_parameters = get_precompiled_check_parameters(hostname, service.item,
                                                                  service.parameters,
                                                                  service.check_plugin_name)
        services.append(
            Service(service.check_plugin_name, service.item, service.description,
                    precompiled_parameters, service.service_labels))
    return services


def get_precompiled_check_parameters(hostname, item, params, check_plugin_name):
    # type: (HostName, Item, CheckParameters, CheckPluginName) -> CheckParameters
    precomp_func = config.precompile_params.get(check_plugin_name)
    if precomp_func:
        if not callable(precomp_func):
            raise TypeError("Invalid precompile_params function: %r" % precomp_func)
        precomp_func = cast(Callable[[HostName, Item, CheckParameters], CheckParameters],
                            precomp_func)
        return precomp_func(hostname, item, params)
    return params


def remove_duplicate_checks(check_table):
    # type: (AbstractCheckTable) -> AbstractCheckTable
    have_with_tcp = {}  # type: Dict[str, Tuple[CheckPluginName, Item]]
    have_with_snmp = {}  # type: Dict[str, Tuple[CheckPluginName, Item]]
    without_duplicates = {}  # type: AbstractCheckTable
    for key, service in check_table.items():
        if cmk.base.check_utils.is_snmp_check(service.check_plugin_name):
            if service.description in have_with_tcp:
                continue
            have_with_snmp[service.description] = key
        else:
            if service.description in have_with_snmp:
                snmp_key = have_with_snmp[service.description]
                del without_duplicates[snmp_key]
                del have_with_snmp[service.description]
            have_with_tcp[service.description] = key
        without_duplicates[key] = service
    return without_duplicates


def get_needed_check_names(hostname, remove_duplicates=False, filter_mode=None, skip_ignored=True):
    # type: (HostName, bool, Optional[str], bool) -> Set[CheckPluginName]
    return {
        s.check_plugin_name for s in get_check_table(hostname,
                                                     remove_duplicates=remove_duplicates,
                                                     filter_mode=filter_mode,
                                                     skip_ignored=skip_ignored).values()
    }


# TODO: Clean this up!
def _get_sorted_check_table(hostname, remove_duplicates=False, filter_mode=None, skip_ignored=True):
    # type: (HostName, bool, Optional[str], bool) -> List[Service]
    # Convert from dictionary into simple tuple list. Then sort it according to
    # the service dependencies.
    # TODO: Use the Service objects from get_check_table once it returns these objects
    is_cmc = config.is_cmc()
    unsorted = [(service,
                 [] if is_cmc else config.service_depends_on(hostname, service.description))
                for service in get_check_table(hostname,
                                               remove_duplicates=remove_duplicates,
                                               filter_mode=filter_mode,
                                               skip_ignored=skip_ignored).values()]

    unsorted.sort(key=lambda x: x[0].description)

    ordered = []  # type: List[Service]
    while len(unsorted) > 0:
        unsorted_descrs = {entry[0].description for entry in unsorted}
        left = []
        at_least_one_hit = False
        for check in unsorted:
            deps_fulfilled = True
            for dep in check[1]:  # dependencies
                if dep in unsorted_descrs:
                    deps_fulfilled = False
                    break
            if deps_fulfilled:
                ordered.append(check[0])
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
