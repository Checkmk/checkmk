#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

from typing import Iterable, Iterator, List, Mapping, Set
from contextlib import suppress
import enum

from cmk.utils.check_utils import maincheckify
from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config

from cmk.base.check_utils import Service, ServiceID


class FilterMode(enum.Enum):
    NONE = enum.auto()
    ONLY_CLUSTERED = enum.auto()
    INCLUDE_CLUSTERED = enum.auto()


class HostCheckTable(Mapping[ServiceID, Service]):
    def __init__(
        self,
        *,
        services: Iterable[Service],
    ) -> None:
        self._data = {s.id(): s for s in services}

    def __getitem__(self, key: ServiceID) -> Service:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[ServiceID]:
        return iter(self._data)

    def needed_check_names(self) -> Set[CheckPluginName]:
        return {s.check_plugin_name for s in self.values()}


def _aggregate_check_table_services(
    *,
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    skip_autochecks: bool,
    skip_ignored: bool,
    filter_mode: FilterMode,
) -> Iterable[Service]:

    sfilter = _ServiceFilter(
        config_cache=config_cache,
        host_config=host_config,
        mode=filter_mode,
        skip_ignored=skip_ignored,
    )

    # process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not (skip_autochecks or host_config.is_ping_host):
        yield from (
            s for s in config_cache.get_autochecks_of(host_config.hostname) if sfilter.keep(s))

    yield from (s for s in _get_static_check_entries(host_config) if sfilter.keep(s))

    # Now add checks a cluster might receive from its nodes
    if host_config.is_cluster:
        yield from (s for s in _get_clustered_services(config_cache, host_config, skip_autochecks)
                    if sfilter.keep(s))


class _ServiceFilter:
    def __init__(
        self,
        *,
        config_cache: config.ConfigCache,
        host_config: config.HostConfig,
        mode: FilterMode,
        skip_ignored: bool,
    ) -> None:
        """Filter services for a specific host

        FilterMode.NONE              -> default, returns only checks for this host
        FilterMode.ONLY_CLUSTERED    -> returns only checks belonging to clusters
        FilterMode.INCLUDE_CLUSTERED -> returns checks of own host, including clustered checks
        """
        self._config_cache = config_cache
        self._host_name = host_config.hostname
        self._host_part_of_clusters = host_config.part_of_clusters
        self._mode = mode
        self._skip_ignored = skip_ignored

    def keep(self, service: Service) -> bool:
        # drop unknown plugins:
        if agent_based_register.get_check_plugin(service.check_plugin_name) is None:
            return False

        if self._skip_ignored and config.service_ignored(
                self._host_name,
                service.check_plugin_name,
                service.description,
        ):
            return False

        if self._mode is FilterMode.INCLUDE_CLUSTERED:
            return True

        if not self._host_part_of_clusters:
            return self._mode is not FilterMode.ONLY_CLUSTERED

        host_of_service = self._config_cache.host_of_clustered_service(
            self._host_name,
            service.description,
            part_of_clusters=self._host_part_of_clusters,
        )
        svc_is_mine = (self._host_name == host_of_service)

        if self._mode is FilterMode.NONE:
            return svc_is_mine

        # self._mode is FilterMode.ONLY_CLUSTERED
        return not svc_is_mine


def _get_static_check_entries(host_config: config.HostConfig,) -> Iterator[Service]:
    entries: List[Service] = []
    for _checkgroup_name, check_plugin_name_str, item, params in host_config.static_checks:
        # TODO (mo): centralize maincheckify: CMK-4295
        check_plugin_name = CheckPluginName(maincheckify(check_plugin_name_str))

        if config.has_timespecific_params(params):
            timespec_params = [params]
            params = {}
        else:
            timespec_params = []

        new_params = config.compute_check_parameters(
            host_config.hostname,
            check_plugin_name,
            item,
            params,
            for_static_checks=True,
        )

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


def _get_clustered_services(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    skip_autochecks: bool,
) -> Iterable[Service]:
    for node in host_config.nodes or []:
        # TODO: Cleanup this to work exactly like the logic above (for a single host)
        # (mo): in particular: this means that autochecks will win over static checks.
        #       for a single host the static ones win.
        node_config = config_cache.get_host_config(node)
        node_checks = list(_get_static_check_entries(node_config))
        if not (skip_autochecks or host_config.is_ping_host):
            node_checks += config_cache.get_autochecks_of(node)

        for service in node_checks:
            services_host = config_cache.host_of_clustered_service(node, service.description)
            if services_host != host_config.hostname:
                continue

            cluster_params = config.compute_check_parameters(
                host_config.hostname,
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
    filter_mode: FilterMode = FilterMode.NONE,
    skip_ignored: bool = True,
) -> HostCheckTable:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    # TODO (mo): find out why skip_ignored is ignored here. That seems wrong to me.
    cache_key = (host_config.hostname, filter_mode, skip_autochecks) if use_cache else None

    if cache_key:
        with suppress(KeyError):
            return config_cache.check_table_cache[cache_key]

    host_check_table = HostCheckTable(services=_aggregate_check_table_services(
        config_cache=config_cache,
        host_config=host_config,
        skip_autochecks=skip_autochecks,
        skip_ignored=skip_ignored,
        filter_mode=filter_mode,
    ))

    if cache_key:
        config_cache.check_table_cache[cache_key] = host_check_table

    return host_check_table
