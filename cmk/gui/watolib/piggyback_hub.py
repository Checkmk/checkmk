#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from livestatus import SiteConfiguration, SiteId

from cmk.utils.paths import omd_root

from cmk.gui.site_config import configured_sites
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.piggyback_hub.config import load_config, PiggybackHubConfig, save_config
from cmk.piggyback_hub.paths import create_paths
from cmk.piggyback_hub.utils import distribute


def _piggyback_hub_enabled(site_config: SiteConfiguration, global_settings: GlobalSettings) -> bool:
    if (enabled := site_config.get("globals", {}).get("piggyback_hub_enabled")) is not None:
        return enabled
    return global_settings.get("piggyback_hub_enabled", True)


def get_enabled_piggyback_hub_site_configs() -> Mapping[SiteId, SiteConfiguration]:
    global_settings = load_configuration_settings()
    return {
        site_id: site_config
        for site_id, site_config in configured_sites().items()
        if _piggyback_hub_enabled(site_config, global_settings) is True
    }


def _get_piggyback_hub_config(
    site_configs: Mapping[SiteId, SiteConfiguration],
) -> PiggybackHubConfig:
    root_folder = folder_tree().root_folder()
    return PiggybackHubConfig(
        targets={
            host_name: host.site_id()
            for host_name, host in root_folder.all_hosts_recursively().items()
            if host.site_id() in site_configs.keys()
        }
    )


def distribute_config() -> None:
    site_configs = get_enabled_piggyback_hub_site_configs()

    paths = create_paths(omd_root)

    old_config = load_config(paths)
    new_config = _get_piggyback_hub_config(site_configs)

    if set(old_config.targets) != set(new_config.targets):
        distribute({site: new_config for site in site_configs.keys()}, omd_root)
        save_config(paths, new_config)
