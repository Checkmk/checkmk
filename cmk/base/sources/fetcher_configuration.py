#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Any, Dict, Optional

from cmk.utils.type_defs import HostAddress

from cmk.core_helpers import FetcherType

import cmk.base.core_config as core_config
from cmk.base.config import HostConfig, max_cachefile_age

from ._abstract import Source
from ._checkers import make_non_cluster_sources

__all__ = ["fetchers", "clusters"]


def get_ip_address(host_config: HostConfig) -> Optional[HostAddress]:
    if host_config.is_ipv6_primary:
        return core_config.ip_address_of(host_config, socket.AF_INET6)

    return core_config.ip_address_of(host_config, socket.AF_INET)


def _fixup_caching_info(source: Source) -> Source:
    if source.fetcher_type is not FetcherType.SNMP:
        # By default this is MaxAge.none(). For checking this is the same as max_cachefile_age(),
        # but:
        # During discovery, the allowed cache age is (by default) 120 seconds, such that the
        # discovery service won't steal data in the TCP case.
        # But we do want to see new services, so for SNMP we leave the cache age at zero.
        # For TCP, we ensure updated caches by triggering the "Check_MK" service whenever the
        # user manually triggers "Check_MK Discovery", but then use cached data during the actual
        # discovery
        source.file_cache_max_age = max_cachefile_age()
    return source


def fetchers(host_config: HostConfig) -> Dict[str, Any]:
    ipaddress = get_ip_address(host_config)
    return {
        "fetchers": [
            {
                "fetcher_type": c.fetcher_type.name,
                "fetcher_params": _fixup_caching_info(c).fetcher_configuration,
            }
            for c in make_non_cluster_sources(host_config, ipaddress)
        ]
    }


def clusters(host_config: HostConfig) -> Dict[str, Any]:
    return {"clusters": {"nodes": host_config.nodes or ()}}
