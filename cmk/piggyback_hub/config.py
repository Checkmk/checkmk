#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Final

from pydantic import BaseModel

from cmk.utils.hostaddress import HostName

from cmk.messaging import Connection

PIGGYBACK_HUB_CONFIG_PATH: Final = Path("etc/check_mk/piggyback_hub.conf")
MULTISITE_CONFIG: Final = Path("etc/check_mk/piggyback_hub.d/multisite.conf")


@dataclass
class Target:
    host_name: HostName
    site_id: str


class PiggybackConfig(BaseModel):
    hosts: Sequence[Target]


def config_path(omd_root: Path) -> Path:
    """Get the path of the local piggyback hub configuration"""
    return omd_root / PIGGYBACK_HUB_CONFIG_PATH


def multisite_config_path(omd_root: Path) -> Path:
    """Get the path of the multisite configuration"""
    return omd_root / MULTISITE_CONFIG


def distribute(configs: Mapping[str, Sequence[Target]], omd_root: Path) -> None:
    for site_id, config in configs.items():
        with Connection("piggyback-hub", omd_root) as conn:
            channel = conn.channel(PiggybackConfig)
            channel.publish_for_site(site_id, PiggybackConfig(hosts=config), routing="config")


def save_config(
    logger: logging.Logger, omd_root: Path
) -> Callable[[object, object, object, PiggybackConfig], None]:
    def _on_message(
        _channel: object, _delivery: object, _properties: object, received: PiggybackConfig
    ) -> None:
        logger.debug("New configuration received")
        file_path = config_path(omd_root)
        file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

        with tempfile.NamedTemporaryFile(
            "w", dir=str(file_path.parent), prefix=f".{file_path.name}.new", delete=False
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(json.dumps(received.model_dump()["hosts"]))

        os.rename(tmp_path, str(file_path))

    return _on_message
