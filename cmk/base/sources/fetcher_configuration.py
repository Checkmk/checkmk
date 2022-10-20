#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Any, Dict, Optional

from cmk.utils.type_defs import HostAddress

from cmk.core_helpers import FetcherType
from cmk.core_helpers.cache import MaxAge

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.config import HostConfig

from ._checkers import make_non_cluster_sources

__all__ = ["fetchers", "clusters"]


def get_ip_address(host_config: HostConfig) -> Optional[HostAddress]:
    if host_config.is_ipv6_primary:
        return core_config.ip_address_of(host_config, socket.AF_INET6)

    return core_config.ip_address_of(host_config, socket.AF_INET)


def fetchers(host_config: HostConfig) -> Dict[str, Any]:
    ipaddress = get_ip_address(host_config)
    return {
        "fetchers": [
            {
                "ident": source.ident,
                "fetcher_type": source.fetcher_type.name,
                "source_type": source.source_type.name,
                "fetcher_params": fetcher.to_json(),
                "file_cache_params": type(file_cache)(
                    file_cache.hostname,
                    path_template=file_cache.path_template,
                    # During discovery, the allowed cache age defaults to 120 seconds,
                    # such that the discovery service won't steal data for TCP.
                    # For SNMP, we do want to see new services so we invalidate the cache
                    # immediately.
                    # For TCP, we ensure the cache gets updated by triggering the "Check_MK"
                    # service when the "Check_MK Discovery" is triggered and use the newly
                    # cached data during the discovery.
                    max_age=(
                        MaxAge.none()
                        if source.fetcher_type is FetcherType.SNMP
                        else file_cache.max_age
                    ),
                    use_outdated=file_cache.use_outdated,
                    simulation=file_cache.simulation,
                    use_only_cache=file_cache.use_only_cache,
                    file_cache_mode=file_cache.file_cache_mode,
                ).to_json(),
            }
            for source, file_cache, fetcher in make_non_cluster_sources(
                host_config,
                ipaddress,
                simulation_mode=config.simulation_mode,
                missing_sys_description=config.get_config_cache().in_binary_hostlist(
                    host_config.hostname,
                    config.snmp_without_sys_descr,
                ),
                file_cache_max_age=config.max_cachefile_age(),
            )
        ]
    }


def clusters(host_config: HostConfig) -> Dict[str, Any]:
    return {"clusters": {"nodes": host_config.nodes or ()}}
