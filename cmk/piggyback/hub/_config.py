#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, PlainValidator

from cmk.ccc.hostaddress import HostName

from cmk.messaging import Connection, QueueName, RoutingKey

from ._paths import RELATIVE_CONFIG_PATH
from ._utils import APP_NAME

CONFIG_ROUTE = RoutingKey("config")

CONFIG_QUEUE = QueueName("config")


AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


type HostLocations = Mapping[AnnotatedHostName, str]
"""A map of host names to the sites they are monitored on."""


class ConfigType(enum.Enum):
    ONESHOT = enum.auto()
    PERSISTED = enum.auto()


class PiggybackHubConfig(BaseModel):
    type: ConfigType
    locations: HostLocations


class _PersistedPiggybackHubConfig(BaseModel):
    locations: Mapping[AnnotatedHostName, str] = {}


def save_config(omd_root: Path, config: PiggybackHubConfig) -> None:
    persisted = _PersistedPiggybackHubConfig(locations=config.locations)
    path = omd_root / RELATIVE_CONFIG_PATH
    path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    tmp_path = path.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(f"{persisted.model_dump_json()}\n")
    tmp_path.rename(path)


def load_config(omd_root: Path) -> PiggybackHubConfig:
    try:
        locations = _PersistedPiggybackHubConfig.model_validate_json(
            (omd_root / RELATIVE_CONFIG_PATH).read_text()
        ).locations
    except FileNotFoundError:
        locations = {}
    return PiggybackHubConfig(type=ConfigType.PERSISTED, locations=locations)


def publish_persisted_locations(
    destination_site: str, locations: HostLocations, omd_root: Path, omd_site: str
) -> None:
    """Publish host locations for continuous distribution of piggyback data.

    Args:
        destination_site: The site to receive the instruction to send piggyback data
        locations: A mapping of host names to the sites they are monitored on.
        omd_root: The path to the OMD root directory of this site.
        omd_site: The name of this OMD site
    """
    config = PiggybackHubConfig(type=ConfigType.PERSISTED, locations=locations)
    _publish_config(destination_site, config, omd_root, omd_site)


def publish_one_shot_locations(
    destination_site: str, locations: HostLocations, omd_root: Path, omd_site: str
) -> None:
    """Publish host locations for one-shot distribution of piggyback data.

    Args:
        destination_site: The site to receive the instruction to send piggyback data
        locations: A mapping of host names to the sites they are monitored on.
        omd_root: The path to the OMD root directory of this site.
        omd_site: The name of this OMD site
    """
    config = PiggybackHubConfig(type=ConfigType.ONESHOT, locations=locations)
    _publish_config(destination_site, config, omd_root, omd_site)


def _publish_config(
    destination_site: str, config: PiggybackHubConfig, omd_root: Path, omd_site: str
) -> None:
    with Connection(APP_NAME, omd_root, omd_site) as conn:
        channel = conn.channel(PiggybackHubConfig)
        channel.publish_for_site(destination_site, config, routing=CONFIG_ROUTE)
