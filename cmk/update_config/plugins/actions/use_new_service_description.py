#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from logging import Logger

from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING

from cmk.update_config.registry import update_action_registry, UpdateAction


def _migrate_from_old_format(
    logger: Logger,
    use_new_descriptions_sample_config: Mapping[str, bool],
    use_new_descriptions_selected_plugins: Sequence[str],
) -> Mapping[str, bool]:
    logger.debug(
        "Migrating 'use_new_descriptions_for' from old format (list of enabled plugins) to new format (enabled state per plugin)"
    )
    return {
        plugin: plugin in use_new_descriptions_selected_plugins
        for plugin in use_new_descriptions_sample_config
    }


def _update_new_format(
    logger: Logger,
    use_new_descriptions_sample_config: Mapping[str, bool],
    use_new_descriptions_for_current: Mapping[str, bool],
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

    return {
        k: use_new_descriptions_for_current.get(k, False)
        for k in use_new_descriptions_sample_config
    }


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
                )
            case list(use_new_descriptions_selected_plugins):
                updated_global_settings["use_new_descriptions_for"] = _migrate_from_old_format(
                    logger,
                    USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
                    use_new_descriptions_selected_plugins,
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
    )
)
