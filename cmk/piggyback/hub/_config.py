#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Connection, QueueName, RoutingKey

from ._paths import create_paths, PiggybackHubPaths
from ._utils import APP_NAME

CONFIG_ROUTE = RoutingKey("config")

CONFIG_QUEUE = QueueName("config")


type HostLocations = Mapping[HostName, str]
"""A map of host names to the sites they are monitored on."""


class PiggybackHubConfig(BaseModel):
    locations: HostLocations


class _PersistedPiggybackHubConfig(BaseModel):
    locations: Mapping[HostName, str] = {}


def save_config(omd_root: Path, config: PiggybackHubConfig) -> None:
    persisted = _PersistedPiggybackHubConfig(locations=config.locations)
    paths = create_paths(omd_root)
    paths.config.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    tmp_path = paths.config.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(f"{persisted.model_dump_json()}\n")
    tmp_path.rename(paths.config)


def load_config(paths: PiggybackHubPaths) -> PiggybackHubConfig:
    try:
        locations = _PersistedPiggybackHubConfig.model_validate_json(
            paths.config.read_text()
        ).locations
    except FileNotFoundError:
        locations = {}
    return PiggybackHubConfig(locations=locations)


def publish_persisted_locations(
    destination_site: str, locations: HostLocations, omd_root: Path, omd_site: str
) -> None:
    config = PiggybackHubConfig(locations=locations)
    with Connection(APP_NAME, omd_root, omd_site) as conn:
        channel = conn.channel(PiggybackHubConfig)
        channel.publish_for_site(destination_site, config, routing=CONFIG_ROUTE)
