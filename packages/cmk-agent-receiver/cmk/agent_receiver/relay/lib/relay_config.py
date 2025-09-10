#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

RELAY_CONFIG_FILE = "relay_config.json"


class RelayConfig(BaseModel):
    task_ttl: float = 120.0
    max_tasks_per_relay: int = 10

    @classmethod
    def load(cls, path: Path | None = None) -> RelayConfig:
        if path is None:
            config_path_dir = os.getenv("OMD_ROOT")
            if config_path_dir is None:
                raise RuntimeError("OMD_ROOT environment variable is not set")
            path = Path(config_path_dir) / RELAY_CONFIG_FILE

        # If config file doesn't exist, return default configuration
        if not path.exists():
            return cls()

        with path.open(encoding="utf-8") as fin:
            raw_config = fin.read()
        return cls.model_validate_json(raw_config)
