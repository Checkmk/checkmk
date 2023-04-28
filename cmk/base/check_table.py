#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

import enum
from contextlib import suppress
from typing import Iterable, Iterator, Mapping, Set

from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.base.config as config
from cmk.base.check_utils import ConfiguredService, ServiceID


class FilterMode(enum.Enum):
    NONE = enum.auto()
    ONLY_CLUSTERED = enum.auto()
    INCLUDE_CLUSTERED = enum.auto()


class HostCheckTable(Mapping[ServiceID, ConfiguredService]):
    def __init__(
        self,
        *,
        services: Iterable[ConfiguredService],
    ) -> None:
        self._data = {s.id(): s for s in services}

    def __getitem__(self, key: ServiceID) -> ConfiguredService:
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
) -> Iterable[ConfiguredService]:

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
            s for s in config_cache.get_autochecks_of(host_config.hostname) if sfilter.keep(s)
        )

    # Now add checks a cluster might receive from its nodes
    if host_config.is_cluster:
        yield from (
            s
            for s in _get_clustered_services(config_cache, host_config, skip_autochecks)
            if sfilter.keep(s)
        )

    yield from (s for s in _get_static_check_entries(config_cache, host_config) if sfilter.keep(s))

    # NOTE: as far as I can see, we only have two cases with the filter mode.
    # Either we compute services to check, or we compute services for fetching.
    if filter_mode is not FilterMode.INCLUDE_CLUSTERED:
        return
    # Now we are in the latter case.
    # Since the clusters don't fetch data themselves, we may have to include more
    # services than are attached to the host itself, so that we get the needed data
    # even if a failover occurred since the last discovery.

    # Consider the case where we've clustered 3 nodes `node{1,2,3}`.
    # Let `service A` be
    #  * (only) in the autochecks of node1
    #  * clustered by a clustered service rule matching hosts node1 and node2.
    #
    # The following must include `service A` for node1 and node2 but *not* for node3.
    # Failing to exclude node3 might add an undesired service to it.
    # For node1 it was added from the autochecks above.
    yield from (
        s
        # ... this adds it for node2
        for s in _get_services_from_cluster_nodes(config_cache, host_config.hostname)
        if sfilter.keep(s)
        # ... and this condition prevents it from being added on node3
        # 'not is_mine' means: would it be there, it would be clustered.
        and not sfilter.is_mine(s)
    )


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

    def keep(self, service: ConfiguredService) -> bool:

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

        svc_is_mine = self.is_mine(service)

        if self._mode is FilterMode.NONE:
            return svc_is_mine

        # self._mode is FilterMode.ONLY_CLUSTERED
        return not svc_is_mine

    def is_mine(self, service: ConfiguredService) -> bool:
        """Determine whether a service should be displayed on this host's service overview.

        If the service should be displayed elsewhere, this means the service is clustered and
        should be displayed on the cluster host's service overview.
        """
        return (
            self._config_cache.host_of_clustered_service(
                self._host_name,
                service.description,
                part_of_clusters=self._host_part_of_clusters,
            )
            == self._host_name
        )


def _get_static_check_entries(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
) -> Iterator[ConfiguredService]:
    entries = []
    for _checkgroup_name, check_plugin_name, item, params in host_config.static_checks:

        descr = config.service_description(host_config.hostname, check_plugin_name, item)
        entries.append(
            ConfiguredService(
                check_plugin_name=check_plugin_name,
                item=item,
                description=descr,
                parameters=config.compute_check_parameters(
                    config_cache.host_of_clustered_service(host_config.hostname, descr),
                    check_plugin_name,
                    item,
                    {},
                    configured_parameters=TimespecificParameters((params,)),
                ),
                discovered_parameters=None,
                service_labels={},
            )
        )

    # Note: We need to reverse the order of the static_checks. This is
    # because users assume that earlier rules have precedence over later
    # ones. For static checks that is important if there are two rules for
    # a host with the same combination of check type and item.
    return reversed(entries)


def _get_services_from_cluster_nodes(
    config_cache: config.ConfigCache, hostname: HostName
) -> Iterable[ConfiguredService]:
    for cluster in config_cache.clusters_of(hostname):
        cluster_config = config_cache.get_host_config(cluster)
        for service in _get_clustered_services(config_cache, cluster_config, False):
            yield service


def _get_clustered_services(
    config_cache: config.ConfigCache,
    host_config: config.HostConfig,
    skip_autochecks: bool,
) -> Iterable[ConfiguredService]:
    for node in host_config.nodes or []:
        node_config = config_cache.get_host_config(node)
        node_checks: list[ConfiguredService] = []
        if not (skip_autochecks or host_config.is_ping_host):
            node_checks += config_cache.get_autochecks_of(node)
        node_checks.extend(_get_static_check_entries(config_cache, node_config))

        yield from (
            service
            for service in node_checks
            if config_cache.host_of_clustered_service(node, service.description)
            == host_config.hostname
        )


def get_check_table(
    hostname: HostName,
    *,
    use_cache: bool = True,
    skip_autochecks: bool = False,
    filter_mode: FilterMode = FilterMode.NONE,
    skip_ignored: bool = True,
) -> HostCheckTable:
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    cache_key = (
        (host_config.hostname, filter_mode, skip_autochecks, skip_ignored) if use_cache else None
    )

    if cache_key:
        with suppress(KeyError):
            return config_cache.check_table_cache[cache_key]

    host_check_table = HostCheckTable(
        services=_aggregate_check_table_services(
            config_cache=config_cache,
            host_config=host_config,
            skip_autochecks=skip_autochecks,
            skip_ignored=skip_ignored,
            filter_mode=filter_mode,
        )
    )

    if cache_key:
        config_cache.check_table_cache[cache_key] = host_check_table

    return host_check_table
