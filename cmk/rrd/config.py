#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Sequence
from typing import Literal

from cmk.utils.config_path import LATEST_CONFIG
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.base import config as base_config  # pylint: disable=cmk-module-layer-violation
from cmk.base.config import CEEConfigCache  # pylint: disable=cmk-module-layer-violation

from .interface import (  # pylint: disable=cmk-module-layer-violation
    RRDObjectConfig,
    RRDReloadableConfig,
)


class RRDConfigImpl(RRDReloadableConfig):
    def __init__(self):
        self._cee_config_cache = self._load_cee_config_cache()

    def reload(self):
        self._cee_config_cache = self._load_cee_config_cache()

    def rrd_config(self, hostname: HostName) -> RRDObjectConfig | None:
        return self._cee_config_cache.rrd_config(hostname)

    def rrd_config_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> RRDObjectConfig | None:
        return self._cee_config_cache.rrd_config_of_service(hostname, description)

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None:
        return self._cee_config_cache.cmc_log_rrdcreation()

    def get_hosts(self) -> Sequence[HostName]:
        hosts_config = base_config.make_hosts_config()
        return sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if self._cee_config_cache.is_active(hn) and self._cee_config_cache.is_online(hn)
            }
        )

    def _load_cee_config_cache(self) -> CEEConfigCache:
        base_config.load_packed_config(LATEST_CONFIG, discovery_rulesets=())
        config_cache = base_config.get_config_cache()
        assert isinstance(config_cache, CEEConfigCache)
        return config_cache
