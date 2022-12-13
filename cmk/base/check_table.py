#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Code for computing the table of checks of hosts."""

import enum
from collections.abc import Iterable, Iterator, Mapping
from contextlib import suppress

from cmk.utils.type_defs import CheckPluginName, HostName, ServiceID

import cmk.base.config as config
from cmk.base.check_utils import ConfiguredService
from cmk.base.config import ConfigCache


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

    def needed_check_names(self) -> set[CheckPluginName]:
        return {s.check_plugin_name for s in self.values()}


def _aggregate_check_table_services(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    skip_autochecks: bool,
    skip_ignored: bool,
    filter_mode: FilterMode,
) -> Iterable[ConfiguredService]:
    sfilter = _ServiceFilter(
        host_name,
        config_cache=config_cache,
        mode=filter_mode,
        skip_ignored=skip_ignored,
    )

    # process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not (skip_autochecks or config_cache.is_ping_host(host_name)):
        yield from (s for s in config_cache.get_autochecks_of(host_name) if sfilter.keep(s))

    yield from (s for s in _get_enforced_services(config_cache, host_name) if sfilter.keep(s))

    # Now add checks a cluster might receive from its nodes
    if config_cache.is_cluster(host_name):
        yield from (
            s
            for s in _get_clustered_services(config_cache, host_name, skip_autochecks)
            if sfilter.keep(s)
        )
        return

    # add all services from the nodes inside the host's clusters
    # the host must try to fetch all services that are discovered in his clusters
    # in case of failover, it has to provide the service data to the cluster
    # even when the service was never discovered on it
    yield from (
        s for s in _get_services_from_cluster_nodes(config_cache, host_name) if sfilter.keep(s)
    )


class _ServiceFilter:
    def __init__(
        self,
        host_name: HostName,
        *,
        config_cache: ConfigCache,
        mode: FilterMode,
        skip_ignored: bool,
    ) -> None:
        """Filter services for a specific host

        FilterMode.NONE              -> default, returns only checks for this host
        FilterMode.ONLY_CLUSTERED    -> returns only checks belonging to clusters
        FilterMode.INCLUDE_CLUSTERED -> returns checks of own host, including clustered checks
        """
        self._host_name = host_name
        self._config_cache = config_cache
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

        if not self._config_cache.clusters_of(self._host_name):
            return self._mode is not FilterMode.ONLY_CLUSTERED

        host_of_service = self._config_cache.host_of_clustered_service(
            self._host_name,
            service.description,
            part_of_clusters=self._config_cache.clusters_of(self._host_name),
        )
        svc_is_mine = self._host_name == host_of_service

        if self._mode is FilterMode.NONE:
            return svc_is_mine

        # self._mode is FilterMode.ONLY_CLUSTERED
        return not svc_is_mine


def _get_enforced_services(
    config_cache: ConfigCache, host_name: HostName
) -> list[ConfiguredService]:
    return [
        service
        for _ruleset_name, service in config_cache.enforced_services_table(host_name).values()
    ]


def _get_services_from_cluster_nodes(
    config_cache: ConfigCache, hostname: HostName
) -> Iterable[ConfiguredService]:
    for cluster in config_cache.clusters_of(hostname):
        yield from _get_clustered_services(config_cache, cluster, False)


def _get_clustered_services(
    config_cache: ConfigCache,
    host_name: HostName,
    skip_autochecks: bool,
) -> Iterable[ConfiguredService]:
    for node in config_cache.nodes_of(host_name) or []:
        # TODO: Cleanup this to work exactly like the logic above (for a single host)
        # (mo): in particular: this means that autochecks will win over static checks.
        #       for a single host the static ones win.
        node_checks = _get_enforced_services(config_cache, node)
        if not (skip_autochecks or config_cache.is_ping_host(host_name)):
            node_checks += config_cache.get_autochecks_of(node)

        yield from (
            service
            for service in node_checks
            if config_cache.host_of_clustered_service(node, service.description) == host_name
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
    cache_key = (hostname, filter_mode, skip_autochecks, skip_ignored) if use_cache else None
    if cache_key:
        with suppress(KeyError):
            return config_cache.check_table_cache[cache_key]

    host_check_table = HostCheckTable(
        services=_aggregate_check_table_services(
            hostname,
            config_cache=config_cache,
            skip_autochecks=skip_autochecks,
            skip_ignored=skip_ignored,
            filter_mode=filter_mode,
        )
    )

    if cache_key:
        config_cache.check_table_cache[cache_key] = host_check_table

    return host_check_table
