#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from logging import Logger

from cmk.utils.log import VERBOSE

from cmk.gui.i18n import is_community_translation
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.userdb import load_users
from cmk.gui.watolib.config_domain_name import (
    config_variable_registry,
    filter_unknown_settings,
    UNREGISTERED_SETTINGS,
)
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
    save_site_global_settings,
)
from cmk.gui.watolib.sites import site_globals_editable, SiteManagementFactory

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

# List[(old_config_name, new_config_name, replacement_dict{old: new})]
_REMOVED_GLOBALS: Sequence[tuple[str, str, Mapping[object, object]]] = [
    ("view_action_defaults", "acknowledge_problems", {}),
]


class UpdateGlobalSettings(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        _update_installation_wide_global_settings(logger)
        _update_site_specific_global_settings(logger)
        _update_remote_site_specific_global_settings(logger)


update_action_registry.register(
    UpdateGlobalSettings(
        name="global_settings",
        title="Global settings",
        sort_index=20,
    )
)


def _update_installation_wide_global_settings(logger: Logger) -> None:
    """Update the globals.mk of the local site"""
    save_global_settings(
        _handle_community_translations(
            logger,
            update_global_config(
                logger,
                # Load full config (with undefined settings)
                load_configuration_settings(full_config=True),
            ),
        )
    )


def _update_site_specific_global_settings(logger: Logger) -> None:
    """Update the sitespecific.mk of the local site (which is a remote site)"""
    if not is_wato_slave_site():
        return
    save_site_global_settings(
        update_global_config(
            logger,
            load_site_global_settings(),
        )
    )


def _update_remote_site_specific_global_settings(logger: Logger) -> None:
    """Update the site specific global settings in the central site configuration"""
    site_mgmt = SiteManagementFactory().factory()
    configured_sites = site_mgmt.load_sites()
    for site_id, site_spec in configured_sites.items():
        if site_globals_editable(site_id, site_spec):
            site_spec["globals"] = dict(
                update_global_config(
                    logger,
                    site_spec.setdefault("globals", {}),
                )
            )
    site_mgmt.save_sites(configured_sites, activate=False)


def update_global_config(
    logger: Logger,
    global_config: GlobalSettings,
) -> GlobalSettings:
    return _transform_global_config_values(
        _update_removed_global_config_vars(
            logger,
            global_config,
        )
    )


def _update_removed_global_config_vars(
    logger: Logger,
    global_config: GlobalSettings,
) -> GlobalSettings:
    global_config_updated = dict(global_config)
    for old_config_name, new_config_name, replacement in _REMOVED_GLOBALS:
        if old_config_name in global_config_updated:
            logger.log(VERBOSE, f"Replacing {old_config_name} with {new_config_name}")
            old_value = global_config_updated[old_config_name]
            if replacement:
                global_config_updated.setdefault(new_config_name, replacement[old_value])
            else:
                global_config_updated.setdefault(new_config_name, old_value)

            del global_config_updated[old_config_name]

    return filter_unknown_settings(
        {
            **global_config_updated,
            **_convert_user_idle_timeout(
                logger,
                global_config_updated,
            ),
            **_convert_max_output_size(
                logger,
                global_config_updated,
            ),
        }
    )


def _convert_user_idle_timeout(
    logger: Logger,
    global_config: GlobalSettings,
) -> dict[str, dict[str, int | dict[str, None | int]]]:
    """
    Version 2.3 moved the former ConfigVariableUserIdleTimeout to ConfigVariableSessionManagement.
    Make sure old settings are respected in the new variable before filter_unknown_settings()
    """
    # No such explicit setting or already converted
    if "user_idle_timeout" not in global_config:
        return {}

    logger.log(VERBOSE, "Converting global setting 'user_idle_timeout' to new format")
    # None, deactivated by user
    if idle_timeout := global_config.get("user_idle_timeout") is None:
        return {"session_mgmt": {}}

    return {
        "session_mgmt": {
            "user_idle_timeout": idle_timeout,
        }
    }


def _convert_max_output_size(
    logger: Logger,
    global_config: GlobalSettings,
) -> dict[str, int]:
    """
    Version 2.1 introduced 'max_long_output_size' as Optional. This should be an Integer.
    Can be removed in 2.4.
    """
    # Factory setting if not explicitly set
    if "max_long_output_size" not in global_config:
        return {}

    logger.log(VERBOSE, "Converting global setting 'max_long_output_size' to new format")
    # None, this should not have happened
    if (max_long_output_size := global_config.get("max_long_output_size")) is None:
        return {"max_long_output_size": 2000}

    return {"max_long_output_size": max_long_output_size}


def _transform_global_config_value(config_var: str, config_val: object) -> object:
    try:
        config_variable_cls = config_variable_registry[config_var]
    except KeyError:
        return config_val
    return config_variable_cls().valuespec().transform_value(config_val)


def _transform_global_config_values(global_config: GlobalSettings) -> GlobalSettings:
    return {
        **global_config,
        **{
            config_var: _transform_global_config_value(config_var, config_val)
            for config_var, config_val in global_config.items()
            if config_var not in UNREGISTERED_SETTINGS
        },
    }


def _handle_community_translations(logger: Logger, global_config: GlobalSettings) -> GlobalSettings:
    """Set the global setting "enable_community_translations" to True if it wasn't set in the old
    version and if a community translated language was set as default language or as user specific
    UI language. Otherwise this global setting defaults to False and community translations are not
    choosable as language.
    """
    enable_ct_ident = "enable_community_translations"
    if enable_ct_ident in global_config:
        return global_config

    enable_ct: bool = False
    if is_community_translation(global_config.get("default_language", "en")):
        enable_ct = True
    else:
        for user_config in load_users().values():
            if is_community_translation(user_config.get("language", "en")):
                enable_ct = True
                break

    if enable_ct:
        logger.log(VERBOSE, "Changing global setting '%s' to true" % enable_ct_ident)
        return {**global_config, "enable_ct_ident": True}

    return global_config
