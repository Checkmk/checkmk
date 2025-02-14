#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc.store import load_object_from_file

from cmk.utils.config_path import ConfigPath, LATEST_CONFIG, VersionedConfigPath
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

RRD_CONFIG_FOLDER = "rrd_config"
RRD_CONFIG_HOSTS_FOLDER = "hosts"
CMC_LOG_RRDCREATION = "cmc_log_rrdcreation"


@lru_cache
def rrd_config_dir(config_path: ConfigPath) -> Path:
    return Path(config_path) / RRD_CONFIG_FOLDER


@lru_cache
def rrd_config_hosts_dir(config_path: ConfigPath) -> Path:
    return rrd_config_dir(config_path) / RRD_CONFIG_FOLDER / RRD_CONFIG_HOSTS_FOLDER


class RRDObjectConfig(TypedDict):
    """RRDObjectConfig
    This typing might not be complete or even wrong, feel free to improve"""

    cfs: Iterable[Literal["MIN", "MAX", "AVERAGE"]]  # conceptually a Set[Literal[...]]
    rras: list[tuple[float, int, int]]
    step: int
    format: Literal["pnp_multiple", "cmc_single"]


class _RRDHostConfig(TypedDict, total=False):
    host: RRDObjectConfig
    services: Mapping[str, RRDObjectConfig]


class RRDConfig:
    def __init__(self):
        self._loaded_host_configs: dict[HostName, _RRDHostConfig] = {}
        self._config_base_path = VersionedConfigPath.current()
        self._config_path = rrd_config_dir(self._config_base_path)
        self._hosts_path = rrd_config_hosts_dir(self._config_base_path)

    def reload(self) -> None:
        new_config_base_path = VersionedConfigPath.current()
        if new_config_base_path != self._config_base_path:
            self._loaded_host_configs = {}
            self._config_base_path = new_config_base_path
            self._config_path = rrd_config_dir(self._config_base_path)
            self._hosts_path = rrd_config_hosts_dir(self._config_base_path)

    def rrd_config(self, hostname: HostName) -> RRDObjectConfig | None:
        self._conditionally_load_host_config(hostname)
        return self._loaded_host_configs[hostname].get("host")

    def rrd_config_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> RRDObjectConfig | None:
        self._conditionally_load_host_config(hostname)
        return self._loaded_host_configs[hostname].get("services", {}).get(description)

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None:
        if not self._config_path.exists():
            self.reload()
        return load_object_from_file(self._config_path / CMC_LOG_RRDCREATION, default=None)

    def _conditionally_load_host_config(self, hostname: HostName) -> None:
        if not self._hosts_path.exists():
            self.reload()
        if hostname not in self._loaded_host_configs:
            self._loaded_host_configs[hostname] = load_object_from_file(
                self._hosts_path / hostname, default={}
            )


def read_hostnames() -> Sequence[HostName]:
    return [
        HostName(p.name)
        for p in (Path(LATEST_CONFIG) / RRD_CONFIG_FOLDER / RRD_CONFIG_HOSTS_FOLDER).glob("*")
    ]
