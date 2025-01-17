#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
from collections.abc import Callable, Mapping
from multiprocessing.synchronize import Event
from pathlib import Path

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, Connection, DeliveryTag, QueueName, RoutingKey

from .paths import create_paths, PiggybackHubPaths
from .utils import APP_NAME

CONFIG_ROUTE = RoutingKey("config")

CONFIG_QUEUE = QueueName("config")


class PiggybackHubConfig(BaseModel):
    targets: Mapping[HostName, str] = {}


class _PersistedPiggybackHubConfig(BaseModel):
    targets: Mapping[HostName, str] = {}


def _save_config(paths: PiggybackHubPaths, config: PiggybackHubConfig) -> None:
    persisted = _PersistedPiggybackHubConfig(targets=config.targets)
    paths.config.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    tmp_path = paths.config.with_suffix(f".{os.getpid()}.tmp")
    tmp_path.write_text(f"{persisted.model_dump_json()}\n")
    tmp_path.rename(paths.config)


def save_config_on_message(
    logger: logging.Logger, omd_root: Path, reload_config: Event
) -> Callable[[Channel[PiggybackHubConfig], DeliveryTag, PiggybackHubConfig], None]:
    def _on_message(
        channel: Channel[PiggybackHubConfig],
        delivery_tag: DeliveryTag,
        received: PiggybackHubConfig,
    ) -> None:
        logger.debug("New configuration received")

        _save_config(create_paths(omd_root), received)

        reload_config.set()

        channel.acknowledge(delivery_tag)

    return _on_message


def load_config(paths: PiggybackHubPaths) -> PiggybackHubConfig:
    try:
        persisted = _PersistedPiggybackHubConfig.model_validate_json(paths.config.read_text())
    except FileNotFoundError:
        return PiggybackHubConfig()
    return PiggybackHubConfig(targets=persisted.targets)


def distribute_config(
    configs: Mapping[str, PiggybackHubConfig], omd_root: Path, omd_site: str
) -> None:
    for site_id, config in configs.items():
        with Connection(APP_NAME, omd_root, omd_site) as conn:
            channel = conn.channel(PiggybackHubConfig)
            channel.publish_for_site(site_id, config, routing=CONFIG_ROUTE)
