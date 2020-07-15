#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

from typing import Callable, cast, Iterable, Iterator, List, Optional, Set

from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, CheckPluginNameStr

import cmk.base.config as config
import cmk.base.item_state as item_state
import cmk.base.check_api_utils as check_api_utils
from cmk.utils.type_defs import HostName
from cmk.base.check_utils import (
    CheckTable,
    Item,
    LegacyCheckParameters,
    Service,
)

# Add WATO-configured explicit checks to (possibly empty) checks
# statically defined in checks.
#def add_wato_static_checks_to_checks():


# TODO: This is just a first cleanup step: Continue cleaning this up.
# - Check all call sites and cleanup the different
# - Make this a helper object of HostConfig?
class HostCheckTable:
    def __init__(self, config_cache: config.ConfigCache, host_config: config.HostConfig) -> None:
        super(HostCheckTable, self).__init__()
        self._config_cache = config_cache
        self._host_config = host_config

    def get(self, remove_duplicates: bool, use_cache: bool, skip_autochecks: bool,
            filter_mode: Optional[str], skip_ignored: bool) -> CheckTable:
        """Returns check table for a specific host

        Format of check table is: {(checkname, item): (params, description)}

        filter_mode: None                -> default, returns only checks for this host
        filter_mode: "only_clustered"    -> returns only checks belonging to clusters
        filter_mode: "include_clustered" -> returns checks of own host, including clustered checks
        """
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

        check_table: CheckTable = {}

        # Now process all entries that are specific to the host
        # in search (single host) or that might match the host.
        if not skip_autochecks:
            check_table.update({
                service.id(): service
                for service in self._config_cache.get_autochecks_of(hostname)
                if self._keep_service(service, filter_mode, skip_ignored)
            })

        check_table.update({
            service.id(): service
            for service in self._get_static_check_entries(self._host_config)
            if self._keep_service(service, filter_mode, skip_ignored)
        })

        # Now add checks a cluster might receive from its nodes
        if self._host_config.is_cluster:
            check_table.update({
                service.id(): service
                for service in self._get_clustered_services(hostname, skip_autochecks)
                if self._keep_service(service, filter_mode, skip_ignored)
            })

        if not skip_autochecks and use_cache:
            check_table_cache[table_cache_id] = check_table

        if remove_duplicates:
            return remove_duplicate_checks(check_table)

        return check_table

    def _get_static_check_entries(self, host_config: config.HostConfig) -> Iterator[Service]:
        entries: List[Service] = []
        for _checkgroup_name, check_plugin_name_str, item, params in host_config.static_checks:
            if config.has_timespecific_params(params):
                timespec_params = [params]
                params = {}
            else:
                timespec_params = []

            new_params = config.compute_check_parameters(
                host_config.hostname,
                check_plugin_name_str,
                item,
                params,
            )

            if timespec_params:
                params = config.set_timespecific_param_list(timespec_params, new_params)
            else:
                params = new_params

            # TODO (mo): centralize maincheckify: CMK-4295
            check_plugin_name = CheckPluginName(maincheckify(check_plugin_name_str))
            descr = config.service_description(host_config.hostname, check_plugin_name, item)
            entries.append(Service(check_plugin_name_str, item, descr, params))

        # Note: We need to reverse the order of the static_checks. This is
        # because users assume that earlier rules have precedence over later
        # ones. For static checks that is important if there are two rules for
        # a host with the same combination of check type and item.
        return reversed(entries)

    def _keep_service(self, service: Service, filter_mode: Optional[str],
                      skip_ignored: bool) -> bool:
        hostname = self._host_config.hostname
        # TODO (mo): centralize maincheckify: CMK-4295
        service_check_plugin_name = CheckPluginName(maincheckify(service.check_plugin_name))

        # drop unknown plugins:
        if config.get_registered_check_plugin(service_check_plugin_name) is None:
            return False

        if skip_ignored and config.service_ignored(hostname, service_check_plugin_name,
                                                   service.description):
            return False

        if self._host_config.part_of_clusters:
            host_of_service = self._config_cache.host_of_clustered_service(
                hostname, service.description, part_of_clusters=self._host_config.part_of_clusters)
            svc_is_mine = (hostname == host_of_service)
        else:
            svc_is_mine = True

        if filter_mode is None and not svc_is_mine:
            return False

        if filter_mode == "only_clustered" and svc_is_mine:
            return False

        return True

    def _get_clustered_services(
        self,
        hostname: str,
        skip_autochecks: bool,
    ) -> Iterable[Service]:
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

                cluster_params = config.compute_check_parameters(
                    hostname,
                    service.check_plugin_name,
                    service.item,
                    service.parameters,
                )
                yield Service(
                    service.check_plugin_name,
                    service.item,
                    service.description,
                    cluster_params,
                    service.service_labels,
                )


def get_check_table(hostname: str,
                    remove_duplicates: bool = False,
                    use_cache: bool = True,
                    skip_autochecks: bool = False,
                    filter_mode: Optional[str] = None,
                    skip_ignored: bool = True) -> CheckTable:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    table = HostCheckTable(config_cache, host_config)
    return table.get(remove_duplicates, use_cache, skip_autochecks, filter_mode, skip_ignored)


def get_precompiled_check_table(hostname: str,
                                remove_duplicates: bool = True,
                                filter_mode: Optional[str] = None,
                                skip_ignored: bool = True) -> List[Service]:
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
    host_checks = _get_sorted_service_list(
        hostname,
        remove_duplicates,
        filter_mode=filter_mode,
        skip_ignored=skip_ignored,
    )
    services: List[Service] = []
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


def get_precompiled_check_parameters(
        hostname: HostName, item: Item, params: LegacyCheckParameters,
        check_plugin_name: CheckPluginNameStr) -> LegacyCheckParameters:
    precomp_func = config.precompile_params.get(check_plugin_name)
    if precomp_func:
        if not callable(precomp_func):
            raise TypeError("Invalid precompile_params function: %r" % precomp_func)
        precomp_func = cast(
            Callable[[HostName, Item, LegacyCheckParameters], LegacyCheckParameters], precomp_func)
        return precomp_func(hostname, item, params)
    return params


def remove_duplicate_checks(check_table: CheckTable) -> CheckTable:
    service_keys_by_description = {
        # This will sort by check plugin name and item, which is as good as anything else,
        # as long as it is konsistent.
        # If we want to change the precedence, we must falicitate that using the 'supersedes'
        # feature of the corresponding raw sections.
        service.description: key for key, service in sorted(check_table.items(), reverse=True)
    }
    return {key: check_table[key] for key in service_keys_by_description.values()}


def get_needed_check_names(hostname: HostName,
                           remove_duplicates: bool = False,
                           filter_mode: Optional[str] = None,
                           skip_ignored: bool = True) -> Set[CheckPluginNameStr]:
    return {
        s.check_plugin_name for s in get_check_table(hostname,
                                                     remove_duplicates=remove_duplicates,
                                                     filter_mode=filter_mode,
                                                     skip_ignored=skip_ignored).values()
    }


def _get_sorted_service_list(
    hostname: HostName,
    remove_duplicates: bool = False,
    filter_mode: Optional[str] = None,
    skip_ignored: bool = True,
) -> List[Service]:

    sorted_services_unresolved = sorted(
        get_check_table(hostname,
                        remove_duplicates=remove_duplicates,
                        filter_mode=filter_mode,
                        skip_ignored=skip_ignored).values(),
        key=lambda service: service.description,
    )

    if config.is_cmc():
        return sorted_services_unresolved

    unresolved = [(service, set(config.service_depends_on(hostname, service.description)))
                  for service in sorted_services_unresolved]

    resolved: List[Service] = []
    while unresolved:
        resolved_descriptions = {service.description for service in resolved}
        newly_resolved = [
            service for service, dependencies in unresolved if dependencies <= resolved_descriptions
        ]
        if not newly_resolved:
            problems = [
                "%r (%s / %s)" % (s.description, s.check_plugin_name, s.item) for s, _ in unresolved
            ]
            raise MKGeneralException("Cyclic service dependency of host %s. Problematic are: %s" %
                                     (hostname, ", ".join(problems)))

        unresolved = [(s, d) for s, d in unresolved if s not in newly_resolved]
        resolved.extend(newly_resolved)

    return resolved
