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
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING
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


class UpdateUseNewServiceDescription(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        global_settings = load_configuration_settings(full_config=True)

        updated_global_settings = dict(global_settings).copy()
        match updated_global_settings.get("use_new_descriptions_for"):
            case None:
                return
            case dict(use_new_descriptions_for_mapping):
                updated_global_settings["use_new_descriptions_for"] = _update_new_format(
                    logger,
                    USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
                    use_new_descriptions_for_mapping,
                    _read_autocheck_entries(),
                )
            case list(use_new_descriptions_selected_plugins):
                updated_global_settings["use_new_descriptions_for"] = _migrate_from_old_format(
                    logger,
                    USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
                    use_new_descriptions_selected_plugins,
                    _read_autocheck_entries(),
                )
            case _:
                raise ValueError(
                    f"Unknown 'use_new_descriptions_for' format: {updated_global_settings.get('use_new_descriptions_for')}"
                )

        save_global_settings(updated_global_settings)


update_action_registry.register(
    UpdateUseNewServiceDescription(
        name="use_new_service_description",
        title="Use new service description",
        sort_index=17,  # before rulesets and global settings
        expiry_version=ExpiryVersion.CMK_260,
    )
)
