#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

from typing import Iterable, Iterator, List, Literal, Optional, Set
from contextlib import suppress

from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config

from cmk.base.check_utils import CheckTable, Service


# TODO: This is just a first cleanup step: Continue cleaning this up.
# - Caching a Dict is dangerous. This should be an immutable mapping.
# - Make this a helper object of HostConfig?
class HostCheckTable(CheckTable):
    def __init__(
        self,
        config_cache: config.ConfigCache,
        host_config: config.HostConfig,
        skip_autochecks: bool,
        filter_mode: Optional[Literal["only_clustered", "include_clustered"]],
        skip_ignored: bool,
    ) -> None:
        """Returns check table for a specific host

        Format of check table is: {(checkname, item): (params, description)}

        filter_mode: None                -> default, returns only checks for this host
        filter_mode: "only_clustered"    -> returns only checks belonging to clusters
        filter_mode: "include_clustered" -> returns checks of own host, including clustered checks
        """
        hostname = host_config.hostname

        # Now process all entries that are specific to the host
        # in search (single host) or that might match the host.
        if not skip_autochecks:
            self.update({
                service.id(): service
                for service in config_cache.get_autochecks_of(hostname)
                if self._keep_service(config_cache, host_config, service, filter_mode, skip_ignored)
            })

        self.update({
            service.id(): service
            for service in self._get_static_check_entries(host_config)
            if self._keep_service(config_cache, host_config, service, filter_mode, skip_ignored)
        })

        # Now add checks a cluster might receive from its nodes
        if host_config.is_cluster:
            self.update({
                service.id(): service
                for service in self._get_clustered_services(config_cache, host_config, hostname,
                                                            skip_autochecks)
                if self._keep_service(config_cache, host_config, service, filter_mode, skip_ignored)
            })

    @staticmethod
    def _get_static_check_entries(host_config: config.HostConfig,) -> Iterator[Service]:
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
                for_static_checks=True,
            )

            if timespec_params:
                params = config.set_timespecific_param_list(timespec_params, new_params)
            else:
                params = new_params

            # TODO (mo): centralize maincheckify: CMK-4295
            check_plugin_name = CheckPluginName(maincheckify(check_plugin_name_str))
            descr = config.service_description(host_config.hostname, check_plugin_name, item)
            entries.append(Service(check_plugin_name, item, descr, params))

        # Note: We need to reverse the order of the static_checks. This is
        # because users assume that earlier rules have precedence over later
        # ones. For static checks that is important if there are two rules for
        # a host with the same combination of check type and item.
        return reversed(entries)

    @staticmethod
    def _keep_service(
        config_cache: config.ConfigCache,
        host_config: config.HostConfig,
        service: Service,
        filter_mode: Optional[Literal["only_clustered", "include_clustered"]],
        skip_ignored: bool,
    ) -> bool:
        hostname = host_config.hostname

        # drop unknown plugins:
        if agent_based_register.get_check_plugin(service.check_plugin_name) is None:
            return False

        if skip_ignored and config.service_ignored(hostname, service.check_plugin_name,
                                                   service.description):
            return False

        if filter_mode == "include_clustered":
            return True

        if not host_config.part_of_clusters:
            return filter_mode != "only_clustered"

        host_of_service = config_cache.host_of_clustered_service(
            hostname,
            service.description,
            part_of_clusters=host_config.part_of_clusters,
        )
        svc_is_mine = (hostname == host_of_service)

        if filter_mode is None:
            return svc_is_mine

        # filter_mode == "only_clustered"
        return not svc_is_mine

    def _get_clustered_services(
        self,
        config_cache: config.ConfigCache,
        host_config: config.HostConfig,
        hostname: str,
        skip_autochecks: bool,
    ) -> Iterable[Service]:
        for node in host_config.nodes or []:
            # TODO: Cleanup this to work exactly like the logic above (for a single host)
            node_config = config_cache.get_host_config(node)
            node_checks = list(self._get_static_check_entries(node_config))
            if not skip_autochecks:
                node_checks += config_cache.get_autochecks_of(node)

            for service in node_checks:
                if config_cache.host_of_clustered_service(node, service.description) != hostname:
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


def get_check_table(
    hostname: str,
    *,
    use_cache: bool = True,
    skip_autochecks: bool = False,
    filter_mode: Optional[Literal["only_clustered", "include_clustered"]] = None,
    skip_ignored: bool = True,
) -> HostCheckTable:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    if host_config.is_ping_host:
        skip_autochecks = True

    use_cache_for_real = not skip_autochecks and use_cache
    # speed up multiple lookup of same host
    table_cache_id = host_config.hostname, filter_mode
    if use_cache_for_real:
        with suppress(KeyError):
            return config_cache.check_table_cache[table_cache_id]

    host_check_table = HostCheckTable(
        config_cache,
        host_config,
        skip_autochecks,
        filter_mode,
        skip_ignored,
    )

    if use_cache_for_real:
        config_cache.check_table_cache[table_cache_id] = host_check_table

    return host_check_table


def get_needed_check_names(
    hostname: HostName,
    filter_mode: Optional[Literal["only_clustered", "include_clustered"]] = None,
    skip_ignored: bool = True,
) -> Set[CheckPluginName]:
    return {
        s.check_plugin_name for s in get_check_table(
            hostname,
            filter_mode=filter_mode,
            skip_ignored=skip_ignored,
        ).values()
    }


def get_sorted_service_list(
    hostname: HostName,
    *,
    filter_mode: Optional[Literal["only_clustered", "include_clustered"]] = None,
    skip_ignored: bool = True,
) -> List[Service]:

    sorted_services_unresolved = sorted(
        get_check_table(hostname, filter_mode=filter_mode, skip_ignored=skip_ignored).values(),
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
