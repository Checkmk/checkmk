#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import GlobalSettings
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
from cmk.gui.watolib.sites import site_globals_editable, site_management_registry
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.log import VERBOSE

# List[(old_config_name, new_config_name, replacement_dict{old: new})]
_RENAMED_GLOBALS: Sequence[tuple[str, str, Mapping[object, object]]] = []
_REMOVED_OPTIONS: Sequence[str] = [
    "hide_languages",
    "enable_community_translations",
]


class UpdateGlobalSettings(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        _update_installation_wide_global_settings(logger)
        _update_site_specific_global_settings(logger)
        _update_remote_site_specific_global_settings(logger)


update_action_registry.register(
    UpdateGlobalSettings(
        name="global_settings",
        title="Global settings",
        sort_index=20,
        expiry_version=ExpiryVersion.NEVER,
    )
)


def _update_installation_wide_global_settings(logger: Logger) -> None:
    """Update the globals.mk of the local site"""
    save_global_settings(
        update_global_config(
            logger,
            # Load full config (with undefined settings)
            load_configuration_settings(full_config=True),
        ),
    )


def _update_site_specific_global_settings(logger: Logger) -> None:
    """Update the sitespecific.mk of the local site (which is a remote site)"""
    if not is_distributed_setup_remote_site(active_config.sites):
        return
    save_site_global_settings(
        update_global_config(
            logger,
            load_site_global_settings(),
        )
    )


def _update_remote_site_specific_global_settings(logger: Logger) -> None:
    """Update the site specific global settings in the central site configuration"""
    site_mgmt = site_management_registry["site_management"]
    configured_sites = site_mgmt.load_sites()
    for site_spec in configured_sites.values():
        if site_globals_editable(configured_sites, site_spec):
            site_spec["globals"] = dict(
                update_global_config(
                    logger,
                    site_spec.setdefault("globals", {}),
                )
            )
    site_mgmt.save_sites(
        configured_sites,
        activate=False,
        pprint_value=active_config.wato_pprint_config,
    )


def update_global_config(
    logger: Logger,
    global_config: GlobalSettings,
) -> GlobalSettings:
    new_config = _remove_options(logger, global_config, _REMOVED_OPTIONS)
    new_config = _update_renamed_global_config_vars(
        logger,
        new_config,
    )
    return _transform_global_config_values(new_config)


def _update_renamed_global_config_vars(
    logger: Logger,
    global_config: GlobalSettings,
) -> GlobalSettings:
    global_config_updated = dict(global_config)
    for old_config_name, new_config_name, replacement in _RENAMED_GLOBALS:
        if old_config_name in global_config_updated:
            logger.log(VERBOSE, f"Replacing {old_config_name} with {new_config_name}")
            old_value = global_config_updated[old_config_name]
            if replacement:
                global_config_updated.setdefault(new_config_name, replacement[old_value])
            else:
                global_config_updated.setdefault(new_config_name, old_value)

            del global_config_updated[old_config_name]

    return filter_unknown_settings(global_config_updated)


def _remove_options(
    logger: Logger,
    global_config: GlobalSettings,
    options_to_remove: Sequence[str],
) -> GlobalSettings:
    """remove options_to_remove from global_config

    Meant to cleanup no longer used config options"""

    config = dict(global_config)
    for option_to_remove in options_to_remove:
        if option_to_remove in config:
            logger.log(VERBOSE, f"Removing old unused option {option_to_remove!r}")
        config.pop(option_to_remove, None)
    return config


def _transform_global_config_value(config_var: str, config_val: object) -> object:
    try:
        config_variable = config_variable_registry[config_var]
    except KeyError:
        return config_val
    return config_variable.valuespec().transform_value(config_val)


def _transform_global_config_values(global_config: GlobalSettings) -> GlobalSettings:
    return {
        **global_config,
        **{
            config_var: _transform_global_config_value(config_var, config_val)
            for config_var, config_val in global_config.items()
            if config_var not in UNREGISTERED_SETTINGS
        },
    }
