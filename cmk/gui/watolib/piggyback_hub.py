#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Iterable, Mapping

from livestatus import SiteConfiguration

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId

from cmk.utils.paths import omd_root

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.site_changes import ChangeSpec

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


def _validate_piggyback_hub_config(
    settings_per_site: Mapping[SiteId, GlobalSettings], central_site_id: SiteId
) -> None:
    config_var_ident = "site_piggyback_hub"
    central_enabled = dict(settings_per_site).pop(central_site_id)[config_var_ident]
    if not central_enabled and any(
        remote_config[config_var_ident] for remote_config in settings_per_site.values()
    ):
        raise MKUserError(
            config_var_ident,
            _(
                "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
            ),
        )


def validate_piggyback_hub_config(settings_per_site: Mapping[SiteId, GlobalSettings]) -> None:
    if is_wato_slave_site():
        return

    _validate_piggyback_hub_config(settings_per_site, omd_site())
