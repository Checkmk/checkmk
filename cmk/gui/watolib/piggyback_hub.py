#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Collection, Iterable, Mapping

from livestatus import SiteConfiguration, SiteId

from cmk.ccc.site import omd_site

from cmk.utils.hostaddress import HostName
from cmk.utils.paths import omd_root

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.site_changes import ChangeSpec

from cmk.messaging.rabbitmq import rabbitmqctl_running
from cmk.piggyback.hub import HostLocations, publish_persisted_locations

_HOST_CHANGES = (
    "edit-host",  # includes moving a host from a site to another
    "create-host",
    "delete-host",
    "rename-host",
    "move-host",
    "edit-folder",
    "piggyback-hub-turned-on",
    "cmk-update-config",
)

_REMOTE_PIGGYBACK_STATUS_RELPATH = "etc/check_mk/remote_piggyback_hub_status"


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
    dirty_sites: Collection[SiteId],  # only needed in CME case.
    hosts_sites: Mapping[HostName, SiteId],
) -> None:
    for destination_site, locations in compute_new_config(
        global_settings, configured_sites, hosts_sites
    ):
        publish_persisted_locations(destination_site, locations, omd_root, omd_site())


def compute_new_config(
    global_settings: GlobalSettings,
    configured_sites: Mapping[SiteId, SiteConfiguration],
    hosts_sites: Mapping[HostName, SiteId],
) -> Iterable[tuple[str, HostLocations]]:
    sites_to_update = _filter_for_enabled_piggyback_hub(global_settings, configured_sites)

    def _make_targets(for_site: SiteId) -> HostLocations:
        return {
            host_name: target_site
            for host_name, target_site in hosts_sites.items()
            if target_site != for_site and target_site in sites_to_update
        }

    return ((site, _make_targets(site)) for site in sites_to_update)


def _piggyback_hub_enabled(site_config: SiteConfiguration, global_settings: GlobalSettings) -> bool:
    if (enabled := site_config.get("globals", {}).get("piggyback_hub_enabled")) is not None:
        return enabled
    return global_settings.get("piggyback_hub_enabled", True)


def _filter_for_enabled_piggyback_hub(
    global_settings: GlobalSettings, configured_sites: Mapping[SiteId, SiteConfiguration]
) -> Mapping[SiteId, SiteConfiguration]:
    return {
        site_id: site_config
        for site_id, site_config in configured_sites.items()
        if _piggyback_hub_enabled(site_config, global_settings) is True
    }


def _read_stored_piggyback_hub_status() -> Mapping[SiteId, str]:
    try:
        with open(omd_root.joinpath(_REMOTE_PIGGYBACK_STATUS_RELPATH), "r") as f:
            return {SiteId(site): status for site, status in (line.split() for line in f)}
    except FileNotFoundError:
        return {}


def _store_piggyback_hub_status(sites_status: Mapping[SiteId, int]) -> None:
    with open(omd_root.joinpath(_REMOTE_PIGGYBACK_STATUS_RELPATH), "w") as f:
        for site, status in sites_status.items():
            f.write(f"{site} {"on" if status == 0 else "off"}\n")


def changed_remote_piggyback_hub_status(sites_status: Mapping[SiteId, int]) -> set[SiteId]:
    previous_status = _read_stored_piggyback_hub_status()
    _store_piggyback_hub_status(sites_status)

    sites_changed = set()
    for site, status in sites_status.items():
        status_literal = "on" if status == 0 else "off"
        if status_literal == "off" or previous_status.get(site, "off") == status_literal:
            continue

        # a site is "changed" if the current status is "on"
        # and the previous status was "off" or not present
        sites_changed.add(site)

    if sites_changed and not rabbitmqctl_running():
        subprocess.Popen(
            ["omd", "start", "rabbitmq"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    return sites_changed
