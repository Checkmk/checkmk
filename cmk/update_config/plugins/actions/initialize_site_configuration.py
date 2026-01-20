#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.watolib.sample_config import ConfigGeneratorLocalSiteConnection
from cmk.gui.watolib.sites import site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class InitializeSiteConfiguration(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if site_management_registry["site_management"].load_sites():
            return

        ConfigGeneratorLocalSiteConnection().generate()


update_action_registry.register(
    InitializeSiteConfiguration(
        name="initialize_site_configuration",
        title="Initialize site configuration",
        # Needs to run before "Create precompiled host and folder files". Otherwise the sites
        # attribute will be missing.
        sort_index=2,
        expiry_version=ExpiryVersion.CMK_300,
    )
)
