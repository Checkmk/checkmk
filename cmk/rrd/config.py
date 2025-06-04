#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc.hostaddress import HostName
from cmk.ccc.store import load_object_from_file

from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.servicename import ServiceName

RRD_CONFIG_FOLDER = "rrd_config"
RRD_CONFIG_HOSTS_FOLDER = "hosts"
CMC_LOG_RRDCREATION = "cmc_log_rrdcreation"


@lru_cache
def rrd_config_dir(config_path: Path) -> Path:
    return config_path / RRD_CONFIG_FOLDER


@lru_cache
def rrd_config_hosts_dir(config_path: Path) -> Path:
    return rrd_config_dir(config_path) / RRD_CONFIG_HOSTS_FOLDER


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
    def __init__(self, hostname: HostName) -> None:
        self._loaded_config: _RRDHostConfig = load_object_from_file(
            rrd_config_hosts_dir(VersionedConfigPath.LATEST_CONFIG) / hostname, default={}
        )
        self._cmc_log_rrdcreation = load_object_from_file(
            rrd_config_dir(VersionedConfigPath.LATEST_CONFIG) / CMC_LOG_RRDCREATION, default=None
        )

    def rrd_config(self) -> RRDObjectConfig | None:
        return self._loaded_config.get("host")

    def rrd_config_of_service(self, description: ServiceName) -> RRDObjectConfig | None:
        return self._loaded_config.get("services", {}).get(description)

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None:
        return self._cmc_log_rrdcreation


def read_hostnames() -> Sequence[HostName]:
    return [
        HostName(p.name) for p in rrd_config_hosts_dir(VersionedConfigPath.LATEST_CONFIG).glob("*")
    ]
