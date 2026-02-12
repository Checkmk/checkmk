#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from logging import Logger
from pathlib import Path

from cmk.utils.hostaddress import HostName
from cmk.utils.paths import autochecks_dir

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutochecksStore

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings

from cmk.update_config.registry import update_action_registry, UpdateAction

_NEW_NETAPP_PLUGINS = frozenset(
    {
        CheckPluginName("netapp_ontap_volumes"),
        CheckPluginName("netapp_ontap_snapshots"),
    }
)

_OLD_NETAPP_PLUGINS = frozenset(
    {
        CheckPluginName("netapp_api_volumes"),
        CheckPluginName("netapp_api_snapshots"),
    }
)


def _autocheck_hosts() -> Iterable[HostName]:
    for autocheck_file in Path(autochecks_dir).glob("*.mk"):
        yield HostName(autocheck_file.stem)


def _enable_new_service_in_global_settings(logger: Logger, global_settings: GlobalSettings) -> None:
    use_new_descriptions: list[str] = global_settings.get("use_new_descriptions_for", [])

    for plugin_name in _NEW_NETAPP_PLUGINS:
        if str(plugin_name) not in use_new_descriptions:
            use_new_descriptions.append(str(plugin_name))
            logger.info(
                f"Enabled 'Use new service names' for {str(plugin_name)} in global settings"
            )

    save_global_settings(global_settings)


def _disable_new_service_in_global_settings(
    logger: Logger, global_settings: GlobalSettings
) -> None:
    use_new_descriptions: list[str] = global_settings.get("use_new_descriptions_for", [])

    for plugin_name in _NEW_NETAPP_PLUGINS:
        if str(plugin_name) in use_new_descriptions:
            use_new_descriptions.remove(str(plugin_name))
            logger.info(
                f"Disabled 'Use new service names' for {str(plugin_name)} in global settings"
            )

    save_global_settings(global_settings)


class UpdateNetappVolumesServiceName(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        global_settings = load_configuration_settings(full_config=True)

        if isinstance(global_settings.get("use_new_descriptions_for"), dict):
            # already migrated to new format, nothing to do since we only want to set the option
            # for the old/new service names once
            return

        old_services_found = False

        for host_name in _autocheck_hosts():
            for autocheck in AutochecksStore(host_name).read():
                if autocheck.check_plugin_name in _NEW_NETAPP_PLUGINS:
                    # New service names already in use, don't change them automatically.
                    # User can still disable the new descriptions manually.
                    _enable_new_service_in_global_settings(logger, global_settings)
                    return

                if autocheck.check_plugin_name in _OLD_NETAPP_PLUGINS:
                    old_services_found = True

        if old_services_found:
            _disable_new_service_in_global_settings(logger, global_settings)


update_action_registry.register(
    UpdateNetappVolumesServiceName(
        name="netapp_volumes_service_name",
        title="NetApp Volumes Service Name",
        sort_index=19,  # before global settings
    )
)
