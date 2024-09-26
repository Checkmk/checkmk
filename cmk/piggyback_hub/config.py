#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from pydantic import BaseModel

from cmk.ccc import store

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel, DeliveryTag

from .paths import create_paths


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
        config_path = create_paths(omd_root).config
        config_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

        with tempfile.NamedTemporaryFile(
            "w", dir=str(config_path.parent), prefix=f".{config_path.name}.new", delete=False
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(json.dumps(received.model_dump_json()))

        os.rename(tmp_path, str(config_path))
        reload_config.set()

        channel.acknowledge(delivery_tag)

    return _on_message


def save_config(root_path: Path, config: PiggybackHubConfig) -> None:
    store.save_text_to_file(
        create_paths(root_path).config,
        json.dumps(config.model_dump_json()),
    )


def load_config(root_path: Path) -> PiggybackHubConfig:
    config_path = create_paths(root_path).config
    if not config_path.exists():
        return PiggybackHubConfig()
    raw = store.load_text_from_file(config_path)
    return PiggybackHubConfig.model_validate_json(json.loads(raw))
