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
from typing import Callable

from pydantic import BaseModel

from cmk.ccc import store

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel

from .paths import create_paths


@dataclass(frozen=True)
class Target:
    host_name: HostName
    site_id: str


class PiggybackHubConfig(BaseModel):
    targets: Sequence[Target] = []


def save_config_on_message(
    logger: logging.Logger, omd_root: Path
) -> Callable[[Channel[PiggybackHubConfig], PiggybackHubConfig], None]:
    def _on_message(_channel: Channel[PiggybackHubConfig], received: PiggybackHubConfig) -> None:
        logger.debug("New configuration received")
        config_path = create_paths(omd_root).config
        config_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

        with tempfile.NamedTemporaryFile(
            "w", dir=str(config_path.parent), prefix=f".{config_path.name}.new", delete=False
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(json.dumps(received.model_dump_json()))

        os.rename(tmp_path, str(config_path))

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
    config = store.load_text_from_file(config_path)
    return PiggybackHubConfig.model_validate_json(json.loads(config))
