#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.gui.watolib.sites import SitesConfigFile

from cmk.update_config.registry import update_action_registry, UpdateAction


class InitializeSiteConfiguration(UpdateAction):
    """Create a default sites.mk if none exists.

    Single site setups might have never edited their site configurations, so
    sites.mk might not exist. This ensures the file is present before any
    update actions that depend on site configuration (like rule validation).
    """

    @override
    def __call__(self, logger: Logger) -> None:
        store = SitesConfigFile()
        if store._config_file_path.exists():
            return
        logger.info("Creating default sites.mk")
        connection_configs = store.load_for_reading()
        store.save(connection_configs)


update_action_registry.register(
    InitializeSiteConfiguration(
        name="initialize_site_configuration",
        title="Ensure default site configuration exists",
        sort_index=2,
    )
)
