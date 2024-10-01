#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, DeliveryTag

from .paths import create_paths, PiggybackHubPaths


@dataclass(frozen=True)
class Target:
    host_name: HostName
    site_id: str


class PiggybackHubConfig(BaseModel):
    targets: Sequence[Target] = []


def save_config_on_message(
    logger: logging.Logger, omd_root: Path, reload_config: Event
) -> Callable[[Channel[PiggybackHubConfig], DeliveryTag, PiggybackHubConfig], None]:
    def _on_message(
        channel: Channel[PiggybackHubConfig],
        delivery_tag: DeliveryTag,
        received: PiggybackHubConfig,
    ) -> None:
        logger.debug("New configuration received")

        save_config(create_paths(omd_root), received)

        reload_config.set()

        channel.acknowledge(delivery_tag)

    return _on_message


def save_config(paths: PiggybackHubPaths, config: PiggybackHubConfig) -> None:
    paths.config.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
    tmp_path = paths.config.with_suffix(".new")
    tmp_path.write_text(config.model_dump_json())
    tmp_path.rename(paths.config)


def load_config(paths: PiggybackHubPaths) -> PiggybackHubConfig:
    try:
        return PiggybackHubConfig.model_validate_json(paths.config.read_text())
    except FileNotFoundError:
        return PiggybackHubConfig()
