#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from logging import Logger
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import AutochecksStore
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName
from cmk.gui.config import active_config, Config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
    save_site_global_settings,
)
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING
from cmk.gui.watolib.sites import site_globals_editable, site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import autochecks_dir

# See SUP-27073 for context: these NetApp plugins have been renamed and their service description
# changed, which causes customers to lose the service history. In order to mitigate this, we
# introduced the option to return to the old service descriptions.
# If services with the new description are already discovered, the new description will
# automatically be kept, the customer has to manually return to the old one if needed
# Otherwise if there are old services already discovered, the old description will be kept
# automatically
_RENAMED_PLUGINS: Mapping[str, str] = {
    "netapp_ontap_volumes": "netapp_api_volumes",
    "netapp_ontap_snapshots": "netapp_api_snapshots",
}


def _read_autocheck_entries() -> Sequence[AutocheckEntry]:
    return [
        autocheck
        for autocheck_file in Path(autochecks_dir).glob("*.mk")
        for autocheck in AutochecksStore(HostName(autocheck_file.stem)).read()
    ]


def _plugin_has_discovered_services(
    autocheck_entries: Sequence[AutocheckEntry], plugin_name: CheckPluginName
) -> bool:
    for autocheck in autocheck_entries:
        if autocheck.check_plugin_name == plugin_name:
            return True
    return False


def _is_renamed_plugin_enabled(
    autocheck_entries: Sequence[AutocheckEntry], old_plugin_name: str, new_plugin_name: str
) -> bool:
    has_old_services = _plugin_has_discovered_services(
        autocheck_entries, CheckPluginName(old_plugin_name)
    )
    has_new_services = _plugin_has_discovered_services(
        autocheck_entries, CheckPluginName(new_plugin_name)
    )
    return not has_old_services or has_new_services


def _migrate_from_old_format(
    logger: Logger,
    use_new_descriptions_sample_config: Mapping[str, bool],
    use_new_descriptions_selected_plugins: Sequence[str],
    autocheck_entries: Sequence[AutocheckEntry],
) -> Mapping[str, bool]:
    logger.debug(
        "Migrating 'use_new_descriptions_for' from old format (list of enabled plugins) to new format (enabled state per plugin)"
    )

    results = {}
    for plugin in use_new_descriptions_sample_config:
        if plugin in _RENAMED_PLUGINS:
            results[plugin] = _is_renamed_plugin_enabled(
                autocheck_entries, _RENAMED_PLUGINS[plugin], plugin
            )
        else:
            results[plugin] = plugin in use_new_descriptions_selected_plugins
    return results


def _update_new_format(
    logger: Logger,
    use_new_descriptions_sample_config: Mapping[str, bool],
    use_new_descriptions_for_current: Mapping[str, bool],
    autocheck_entries: Sequence[AutocheckEntry],
) -> Mapping[str, bool]:
    logger.debug(
        "Disable 'use_new_descriptions_for' for plugins where the setting has been added in the new version to keep the old descriptions active"
    )
    removed_plugins = set(use_new_descriptions_for_current) - set(
        USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
    )
    if removed_plugins:
        # If we pass the plugins along here, they would be dropped silently later on as part of
        # the transformation to UI value of the global setting's ValueSpec (Dictionary).
        # We have no procedure to deal with removed plugins and their consequences at the moment,
        # so don't remove them
        raise NotImplementedError(
            "Removing plugins from 'use_new_descriptions_for' is not possible at the moment. "
            f"The following plugins where found in the configuration under update, but are not "
            f"configurable in the new Checkmk version: {removed_plugins}."
        )

    results = {}
    for plugin in use_new_descriptions_sample_config:
        if plugin in _RENAMED_PLUGINS:
            results[plugin] = _is_renamed_plugin_enabled(
                autocheck_entries, _RENAMED_PLUGINS[plugin], plugin
            )
        else:
            results[plugin] = use_new_descriptions_for_current.get(plugin, False)
    return results


def _update_use_new_descriptions_for(
    logger: Logger,
    settings: GlobalSettings,
    autocheck_entries: Sequence[AutocheckEntry],
) -> GlobalSettings:
    match settings.get("use_new_descriptions_for"):
        case None:
            return settings
        case dict(use_new_descriptions_for_mapping):
            updated_value: Mapping[str, bool] = _update_new_format(
                logger,
                USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
                use_new_descriptions_for_mapping,
                autocheck_entries,
            )
            return {**settings, "use_new_descriptions_for": updated_value}
        case list(use_new_descriptions_selected_plugins):
            updated_value = _migrate_from_old_format(
                logger,
                USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
                use_new_descriptions_selected_plugins,
                autocheck_entries,
            )
            return {**settings, "use_new_descriptions_for": updated_value}
        case _:
            raise ValueError(
                f"Unknown 'use_new_descriptions_for' format: {settings.get('use_new_descriptions_for')}"
            )


def _update_installation_wide_global_settings(
    logger: Logger, autocheck_entries: Sequence[AutocheckEntry]
) -> None:
    """Update the globals.mk of the local site"""
    save_global_settings(
        _update_use_new_descriptions_for(
            logger,
            load_configuration_settings(full_config=True),
            autocheck_entries,
        )
    )


def _update_site_specific_global_settings(
    logger: Logger,
    autocheck_entries: Sequence[AutocheckEntry],
    ui_config: Config,
) -> None:
    """Update the sitespecific.mk of the local site (which is a remote site)"""
    if not is_distributed_setup_remote_site(ui_config.sites):
        return
    save_site_global_settings(
        _update_use_new_descriptions_for(
            logger,
            load_site_global_settings(),
            autocheck_entries,
        )
    )


def _update_remote_site_specific_global_settings(
    logger: Logger,
    autocheck_entries: Sequence[AutocheckEntry],
    ui_config: Config,
) -> None:
    """Update the site specific global settings in the central site configuration"""

    site_mgmt = site_management_registry["site_management"]
    configured_sites = site_mgmt.load_sites()
    for site_spec in configured_sites.values():
        if site_globals_editable(configured_sites, site_spec):
            site_spec["globals"] = dict(
                _update_use_new_descriptions_for(
                    logger,
                    site_spec.setdefault("globals", {}),
                    autocheck_entries,
                )
            )

    site_mgmt.save_sites(
        configured_sites,
        activate=False,
        pprint_value=ui_config.wato_pprint_config,
    )


class UpdateUseNewServiceDescription(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        autocheck_entries = _read_autocheck_entries()
        _update_installation_wide_global_settings(logger, autocheck_entries)
        _update_site_specific_global_settings(logger, autocheck_entries, active_config)
        _update_remote_site_specific_global_settings(logger, autocheck_entries, active_config)


update_action_registry.register(
    UpdateUseNewServiceDescription(
        name="use_new_service_description",
        title="Use new service description",
        sort_index=17,  # before rulesets and global settings
        expiry_version=ExpiryVersion.CMK_260,
    )
)
