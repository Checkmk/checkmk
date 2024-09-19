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

from cmk.utils.hostaddress import HostName

from cmk.messaging import Channel

from .paths import create_paths


@dataclass(frozen=True)
class Target:
    host_name: HostName
    site_id: str


class PiggybackConfig(BaseModel):
    targets: Sequence[Target] = []


def save_config(
    logger: logging.Logger, omd_root: Path
) -> Callable[[Channel[PiggybackConfig], PiggybackConfig], None]:
    def _on_message(_channel: Channel[PiggybackConfig], received: PiggybackConfig) -> None:
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
