#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from pydantic import BaseModel

CONFIG_FILE = "agent_receiver_config.json"


class Config(BaseModel):
    task_ttl: float = 120.0
    max_tasks_per_relay: int = 10

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        if path is None:
            config_path_dir = os.getenv("OMD_ROOT")
            if config_path_dir is None:
                raise RuntimeError("OMD_ROOT environment variable is not set")
            path = Path(config_path_dir) / CONFIG_FILE

        # If config file doesn't exist, return default configuration
        if not path.exists():
            return cls()

        with path.open(encoding="utf-8") as fin:
            raw_config = fin.read()
        return cls.model_validate_json(raw_config)

    @property
    def omd_root(self) -> Path:
        return Path(os.environ["OMD_ROOT"])

    @property
    def site_name(self) -> str:
        return os.environ["OMD_SITE"]

    @property
    def config_file(self) -> Path:
        return self.omd_root / CONFIG_FILE

    @property
    def agent_output_dir(self) -> Path:
        return self.omd_root / "var/agent-receiver/received-outputs"

    @property
    def r4r_dir(self) -> Path:
        return self.omd_root / "var/check_mk/wato/requests-for-registration"

    @property
    def internal_secret_path(self) -> Path:
        return self.omd_root / "etc/site_internal.secret"

    @property
    def site_config_path(self) -> Path:
        return self.omd_root / "etc/omd/site.conf"

    @property
    def log_path(self) -> Path:
        return self.omd_root / "var/log/agent-receiver/agent-receiver.log"

    @property
    def site_ca_path(self) -> Path:
        return self.omd_root / "etc/ssl/ca.pem"

    @property
    def agent_ca_path(self) -> Path:
        return self.omd_root / "etc/ssl/agents/ca.pem"


@cache
def get_config() -> Config:
    return Config.load()
