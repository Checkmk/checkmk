#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools

from cmk.base.config import ConfigCache
from cmk.ccc.hostaddress import HostName, Hosts


def monitored_hosts(hosts_config: Hosts, config_cache: ConfigCache) -> set[HostName]:
    """The active and online hosts and clusters of this site"""
    return {
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }
