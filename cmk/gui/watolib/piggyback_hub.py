#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from livestatus import SiteConfiguration, SiteId

from cmk.ccc import store

from cmk.utils.paths import omd_root

from cmk.gui.site_config import configured_sites
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.piggyback_hub.config import config_path, distribute, PiggybackConfig, Target


class PiggybackConfigs(BaseModel):
    configs: Mapping[str, Sequence[Target]]


def load_config():
    config_file = config_path(omd_root)
    if not config_file.exists():
        return PiggybackConfig()
    config = store.load_text_from_file(config_file)

    return PiggybackConfig.model_validate_json(json.loads(config))


def save_config(config: PiggybackConfig) -> None:
    config_file = config_path(omd_root)
    store.save_text_to_file(config_file, json.dumps(config.model_dump_json()))


def piggyback_hub_enabled(site_config: SiteConfiguration, global_settings: GlobalSettings) -> bool:
    if (enabled := site_config.get("globals", {}).get("piggyback_hub_enabled")) is not None:
        return enabled
    return global_settings.get("piggyback_hub_enabled", True)


def get_piggyback_hub_sites() -> Sequence[SiteId]:
    global_settings = load_configuration_settings()
    return [
        site_id
        for site_id, site_config in configured_sites().items()
        if piggyback_hub_enabled(site_config, global_settings) is True
    ]


def get_piggyback_hub_config(piggyback_hub_sites: Sequence[SiteId]) -> PiggybackConfig:
    root_folder = folder_tree().root_folder()

    return PiggybackConfig(
        targets=[
            Target(host_name=host_name, site_id=host.site_id())
            for host_name, host in root_folder.all_hosts_recursively().items()
            if host.site_id() in piggyback_hub_sites
        ]
    )


def distribute_config() -> None:
    piggyback_hub_sites = get_piggyback_hub_sites()

    old_config = load_config()
    new_config = get_piggyback_hub_config(piggyback_hub_sites)

    if set(old_config.targets) != set(new_config.targets):
        distribute({site: new_config for site in piggyback_hub_sites}, omd_root)
        save_config(new_config)
