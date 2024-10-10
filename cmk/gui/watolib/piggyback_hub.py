#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Iterable, Mapping

from livestatus import SiteConfiguration, SiteId

from cmk.utils.hostaddress import HostName
from cmk.utils.paths import omd_root

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.site_changes import ChangeSpec

from cmk.piggyback_hub.config import distribute_config, PiggybackHubConfig

_HOST_CHANGES = (
    "edit-host",
    "create-host",
    "delete-host",
    "rename-host",
    "move-host",
    "edit-folder",
)


def has_piggyback_hub_relevant_changes(pending_changes: Iterable[ChangeSpec]) -> bool:
    def _is_relevant_config_change(change: ChangeSpec) -> bool:
        return (
            change["action_name"] == "edit-configvar"
            and "piggyback_hub" in change["domains"]
            or change["action_name"] in _HOST_CHANGES
        )

    return any(_is_relevant_config_change(change) for change in pending_changes)


def distribute_piggyback_hub_configs(
    global_settings: GlobalSettings,
    configured_sites: Mapping[SiteId, SiteConfiguration],
    dirty_sites: Container[SiteId],  # only needed in CME case.
    hosts_sites: Mapping[HostName, SiteId],
) -> None:
    site_configs = filter_for_enabled_piggyback_hub(global_settings, configured_sites)

    new_config = PiggybackHubConfig(
        targets={
            host_name: site_id
            for host_name, site_id in hosts_sites.items()
            if site_id in site_configs
        }
    )

    distribute_config({site: new_config for site in site_configs}, omd_root)


def _piggyback_hub_enabled(site_config: SiteConfiguration, global_settings: GlobalSettings) -> bool:
    if (enabled := site_config.get("globals", {}).get("piggyback_hub_enabled")) is not None:
        return enabled
    return global_settings.get("piggyback_hub_enabled", True)


def filter_for_enabled_piggyback_hub(
    global_settings: GlobalSettings, configured_sites: Mapping[SiteId, SiteConfiguration]
) -> Mapping[SiteId, SiteConfiguration]:
    return {
        site_id: site_config
        for site_id, site_config in configured_sites.items()
        if _piggyback_hub_enabled(site_config, global_settings) is True
    }
