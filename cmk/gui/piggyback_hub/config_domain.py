#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import subprocess
import traceback
from collections.abc import Mapping

from cmk.ccc import store

from cmk.utils.config_warnings import ConfigurationWarnings

from cmk.gui.log import logger
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils.piggyback_hub import (
    distributed_piggyback_sites,
    PIGGYBACK_HUB_CONFIG,
    PIGGYBACK_HUB_CONFIG_DIR,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, ConfigDomainName, SerializedSettings
from cmk.gui.watolib.hosts_and_folders import folder_tree


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
        try:
            # TODO: the config doesn't get updated if the site specific config of
            # a remote site is changed
            if not is_wato_slave_site():
                self._write_config_file()

            completed_process = subprocess.run(
                ["omd", "restart", "piggyback-hub"],
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

    def _write_config_file(self):
        dist_piggyback_sites = distributed_piggyback_sites()

        root_folder = folder_tree().root_folder()
        hosts = [
            {"host_name": host_name, "site_id": host.site_id()}
            for host_name, host in root_folder.all_hosts_recursively().items()
            if host.site_id() in dist_piggyback_sites
        ]

        store.save_text_to_file(PIGGYBACK_HUB_CONFIG, json.dumps(hosts))
