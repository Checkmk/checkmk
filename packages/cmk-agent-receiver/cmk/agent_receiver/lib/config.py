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
    max_pending_tasks_per_relay: int = 10

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
    def site_cert_path(self) -> Path:
        return self.omd_root / "etc/ssl/sites" / f"{self.site_name}.pem"

    @property
    def agent_ca_path(self) -> Path:
        return self.omd_root / "etc/ssl/agents/ca.pem"

    @property
    def relay_ca_path(self) -> Path:
        return self.omd_root / "etc/ssl/relays/ca.pem"

    @property
    def helper_config_dir(self) -> Path:
        return self.omd_root / "var/check_mk/core/helper_config"

    # TODO: This value is defined in cmk/utils/paths.py but it's not a bazel package yet
    @property
    def raw_data_socket(self) -> Path:
        return self.omd_root / "tmp/run/raw-data"

    @property
    def base_url(self) -> str:
        address = "localhost"
        port = 80
        for site_config_line in self.site_config_path.read_text().splitlines():
            key, value = site_config_line.split("=")
            if key == "CONFIG_APACHE_TCP_PORT":
                port = int(value.strip("'"))
            if key == "CONFIG_APACHE_TCP_ADDR":
                address = value.strip("'")
        return f"http://{address}:{port}/{self.site_name}"

    @property
    def rest_api_url(self) -> str:
        return f"{self.base_url}/check_mk/api/unstable"

    @property
    def internal_rest_api_url(self) -> str:
        return f"{self.base_url}/check_mk/api/internal"

    @property
    def is_remote_site(self) -> bool:
        distributed_mk = self.omd_root / "etc/omd/distributed.mk"
        if not distributed_mk.exists():
            return False
        file_vars: dict[str, object] = {}
        exec(distributed_mk.read_text(), file_vars, file_vars)  # nosec B102
        return file_vars.get("is_wato_remote_site") is True


@cache
def get_config() -> Config:
    return Config.load()
