#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Normalize the SNMP backend values that we have been carrying since 2.0.

The GUI accepted more values than it ever wrote: `False` and `"inline_legacy"`
for the inline backend, `True` and `"pysnmp"` for the classic one. They could
end up in the configuration during the 2.0.0 beta, or by editing the
configuration files by hand. Everything reading them had to know about them,
so we rewrite them once and are done with it.
"""

from logging import Logger
from typing import Final, override

from cmk.gui.config import active_config, Config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
)
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.gui.watolib.sites import site_globals_editable, site_management_registry
from cmk.livestatus_client import SiteConfigurations
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

_GLOBAL_SETTING: Final = "snmp_backend_default"
_RULESET_NAME: Final = "snmp_backend_hosts"


def migrated_backend_value(value: object) -> str | None:
    """Return the value to write instead, or `None` if there is nothing to do.

    We leave values we do not know alone. Guessing a backend for them would be
    worse than the `MKConfigError` the GUI reports for a value it cannot map.
    """
    match value:
        # `False` and `True` are matched by identity, so `0` and `1` are not.
        case False | "inline_legacy":
            return "inline"
        case True | "pysnmp":
            return "classic"
        case _:
            return None


def migrate_global_setting(settings: GlobalSettings, origin: str, logger: Logger) -> GlobalSettings:
    """Return the settings to save, or the passed ones if there is nothing to do.

    `origin` names the settings we are rewriting, for the log message.
    """
    if _GLOBAL_SETTING not in settings:
        return settings
    if (migrated := migrated_backend_value(settings[_GLOBAL_SETTING])) is None:
        return settings

    logger.info(
        "Rewriting %(varname)s in %(origin)s: %(old)r -> %(new)r",
        {
            "varname": _GLOBAL_SETTING,
            "origin": origin,
            "old": settings[_GLOBAL_SETTING],
            "new": migrated,
        },
    )
    return {**settings, _GLOBAL_SETTING: migrated}


def migrate_site_globals(configured_sites: SiteConfigurations, logger: Logger) -> bool:
    """Rewrite the site specific global settings in place, returning whether anything changed."""
    changed = False
    for site_id, site_spec in configured_sites.items():
        if not site_globals_editable(configured_sites, site_spec):
            continue
        site_globals = site_spec.get("globals", {})
        migrated = migrate_global_setting(
            site_globals, f"the global settings of site '{site_id}'", logger
        )
        if migrated is site_globals:
            continue
        site_spec["globals"] = dict(migrated)
        changed = True
    return changed


def migrate_rules(all_rulesets: RulesetCollection, logger: Logger) -> int:
    """Rewrite the rule values in place, returning the number of rewritten rules."""
    if not all_rulesets.exists(_RULESET_NAME):
        return 0

    n_migrated = 0
    for folder, _index, rule in all_rulesets.get(_RULESET_NAME).get_rules():
        if (migrated := migrated_backend_value(rule.value)) is None:
            continue
        logger.info(
            "Rewriting rule %(rule_id)s of ruleset '%(ruleset_name)s' in folder "
            "'%(folder_path)s': %(old)r -> %(new)r",
            {
                "rule_id": rule.id,
                "ruleset_name": _RULESET_NAME,
                "folder_path": folder.path() or "main",
                "old": rule.value,
                "new": migrated,
            },
        )
        rule.value = migrated
        n_migrated += 1
    return n_migrated


def _migrate_installation_wide_global_setting(logger: Logger) -> None:
    """Rewrite the value in the globals.mk of the local site"""
    settings = load_configuration_settings()
    if (migrated := migrate_global_setting(settings, "the global settings", logger)) is settings:
        return
    # `snmp_backend_default` is not among the global settings the cloud edition
    # activates, so without `skip_cse_edition_check` the setting would be dropped.
    save_global_settings(migrated, skip_cse_edition_check=True)


def _migrate_site_specific_global_setting(logger: Logger, ui_config: Config) -> None:
    """Rewrite the value in the sitespecific.mk of the local site (which is a remote site)"""
    if not is_distributed_setup_remote_site(ui_config.sites):
        return
    settings = load_site_global_settings()
    if (
        migrated := migrate_global_setting(settings, "the site specific global settings", logger)
    ) is settings:
        return
    save_global_settings(migrated, site_specific=True, skip_cse_edition_check=True)


def _migrate_remote_site_global_settings(logger: Logger, ui_config: Config) -> None:
    """Rewrite the site specific global settings in the central site configuration"""
    site_mgmt = site_management_registry["site_management"]
    configured_sites = site_mgmt.load_sites()
    if not migrate_site_globals(configured_sites, logger):
        return
    site_mgmt.save_sites(
        make_folder_tree(ui_config),
        configured_sites,
        activate=False,
        pprint_value=ui_config.wato_pprint_config,
        liveproxyd_enabled=ui_config.liveproxyd_enabled,
        use_git=ui_config.wato_use_git,
        acting_user_id=None,
    )


def _migrate_rules(logger: Logger, ui_config: Config) -> None:
    all_rulesets = AllRulesets.load_all_rulesets(make_folder_tree(ui_config))
    if not migrate_rules(all_rulesets, logger):
        return
    all_rulesets.save(pprint_value=ui_config.wato_pprint_config, debug=ui_config.debug)


class MigrateSNMPBackendValues(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        _migrate_installation_wide_global_setting(logger)
        _migrate_site_specific_global_setting(logger, active_config)
        _migrate_remote_site_global_settings(logger, active_config)
        _migrate_rules(logger, active_config)


update_action_registry.register(
    MigrateSNMPBackendValues(
        name="migrate_snmp_backend_values",
        title="Migrating legacy SNMP backend values",
        sort_index=16,  # before global settings (20) and rulesets (30)
        expiry_version=ExpiryVersion.CMK_310,
    )
)
