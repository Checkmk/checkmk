#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools

from cmk.utils.hostaddress import HostName

from cmk.base import config  # pylint: disable=cmk-module-layer-violation
from cmk.base.config import CEEConfigCache  # pylint: disable=cmk-module-layer-violation

from . import rrd  # pylint: disable=cmk-module-layer-violation


def convert_rrds(options: dict, hostnames: list[HostName]) -> None:
    config.load(with_conf_d=True)
    config_cache = config.get_config_cache()
    assert isinstance(config_cache, CEEConfigCache)
    hosts_config = config.make_hosts_config()

    if not hostnames:
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )

    for hostname in hostnames:
        rrd.convert_rrds_of_host(
            config_cache,
            hostname,
            split=options.get("split-rrds", False),
            delete=options.get("delete-rrds", False),
        )
