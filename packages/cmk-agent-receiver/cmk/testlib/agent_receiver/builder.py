#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import final

from cmk.agent_receiver.lib.auth import B64SiteInternalSecret
from cmk.agent_receiver.lib.config import Config, CONFIG_FILE
from cmk.testlib.agent_receiver.certs import set_up_site_certs


@dataclass(frozen=True)
class AgentReceiverSite:
    config: Config

    @property
    def env(self) -> dict[str, str]:
        return {"OMD_ROOT": str(self.config.omd_root), "OMD_SITE": self.config.site_name}

    @property
    def internal_credentials(self) -> B64SiteInternalSecret:
        return B64SiteInternalSecret(
            base64.b64encode(self.config.internal_secret_path.read_bytes()).decode("ascii")
        )


@final
class AgentReceiverConfigBuilder:
    def __init__(
        self,
        *,
        omd_root: Path,
        site_name: str,
        apache_address: str,
        apache_port: int,
        task_ttl: float = 120.0,
        max_pending_tasks_per_relay: int = 10,
    ) -> None:
        self._config = Config(
            omd_root=omd_root,
            site_name=site_name,
            task_ttl=task_ttl,
            max_pending_tasks_per_relay=max_pending_tasks_per_relay,
        )
        self._apache_address = apache_address
        self._apache_port = apache_port

    def build(self) -> AgentReceiverSite:
        config = self._config

        config.omd_root.mkdir(parents=True, exist_ok=True)

        site_conf = config.site_config_path
        site_conf.parent.mkdir(parents=True, exist_ok=True)
        site_conf.write_text(
            f"CONFIG_APACHE_TCP_ADDR='{self._apache_address}'\n"
            f"CONFIG_APACHE_TCP_PORT='{self._apache_port}'\n"
        )

        config.internal_secret_path.parent.mkdir(parents=True, exist_ok=True)
        config.internal_secret_path.write_text("lol")

        config.log_path.parent.mkdir(parents=True, exist_ok=True)
        config.log_path.touch()

        (config.omd_root / CONFIG_FILE).write_text(config.model_dump_json())

        set_up_site_certs(config=config)

        version_name = "some.detailed.version.ultimate"
        version_path = config.omd_root / version_name
        version_path.mkdir(exist_ok=True)
        (config.omd_root / "version").symlink_to(version_path)

        return AgentReceiverSite(config=config)
