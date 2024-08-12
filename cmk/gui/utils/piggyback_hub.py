#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from livestatus import SiteConfiguration, SiteId

import cmk.utils.paths

from cmk.gui.site_config import configured_sites
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings

PIGGYBACK_HUB_CONFIG: Final = cmk.utils.paths.default_config_dir + "/piggyback_hub.conf"
PIGGYBACK_HUB_CONFIG_DIR: Final = cmk.utils.paths.default_config_dir + "/piggyback_hub.d/wato/"


def is_piggyback_hub_enabled(
    site_config: SiteConfiguration, global_settings: GlobalSettings
) -> bool:
    if (enabled := site_config.get("globals", {}).get("piggyback_hub_enabled")) is not None:
        return enabled
    return global_settings.get("piggyback_hub_enabled", True)


def distributed_piggyback_sites() -> list[SiteId]:
    global_settings = load_configuration_settings()
    return [
        site_id
        for site_id, site_config in configured_sites().items()
        if is_piggyback_hub_enabled(site_config, global_settings) is True
    ]
