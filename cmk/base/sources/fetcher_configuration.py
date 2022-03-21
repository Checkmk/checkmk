#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Any, Dict, Optional

from cmk.utils.type_defs import HostAddress

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
                "fetcher_type": c.fetcher_type.name,
                "fetcher_params": c.fetcher_configuration,
            }
            for c in make_non_cluster_sources(host_config, ipaddress)
        ]
    }


def clusters(host_config: HostConfig) -> Dict[str, Any]:
    return {"clusters": {"nodes": host_config.nodes or ()}}
