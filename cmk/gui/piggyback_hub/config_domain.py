#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess
import traceback
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import cmk.utils.paths
from cmk.utils.config_warnings import ConfigurationWarnings

from cmk.gui.log import logger
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, ConfigDomainName, SerializedSettings

PIGGYBACK_HUB_CONFIG_DIR: Final = cmk.utils.paths.default_config_dir + "/piggyback_hub.d/wato/"


class ConfigDomainDistributedPiggyback(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    always_activate = True
    in_global_settings = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "piggyback_hub"

    def config_dir(self):
        return PIGGYBACK_HUB_CONFIG_DIR

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        config = self.load_full_config(
            site_specific=Path(self.config_file(site_specific=True)).exists()
        )
        operation = "start" if config.get("piggyback_hub_enabled", True) else "stop"

        try:
            completed_process = subprocess.run(
                ["omd", operation, "piggyback-hub"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode not in (0, 5):
                raise Exception(completed_process.stdout)

            return []
        except Exception:
            logger.exception("error restarting piggyback hub")
            return ["Failed to restart the piggyback hub: %s" % (traceback.format_exc())]

    def default_globals(self) -> Mapping[str, object]:
        return {"piggyback_hub_enabled": True}
