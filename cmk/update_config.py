#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.
"""
import argparse
import ast
import copy
import errno
import gzip
import hashlib
import logging
import multiprocessing
import re
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime
from datetime import time as dt_time
from pathlib import Path
from typing import Any, Callable, Container, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import cmk.utils
import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.site
import cmk.utils.tty as tty
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import CheckPluginName, HostName, RulesetName, UserId

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
import cmk.base.autochecks
import cmk.base.check_api
import cmk.base.config
from cmk.base.api.agent_based import register

import cmk.gui.config
import cmk.gui.groups
import cmk.gui.utils
import cmk.gui.visuals as visuals
import cmk.gui.watolib.groups
import cmk.gui.watolib.hosts_and_folders
import cmk.gui.watolib.rulesets
import cmk.gui.watolib.tags
import cmk.gui.watolib.timeperiods as timeperiods
from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import SuperUserContext
from cmk.gui.plugins.dashboard.utils import get_all_dashboards
from cmk.gui.plugins.userdb.utils import (
    load_connection_config,
    save_connection_config,
    USER_SCHEME_SERIAL,
)
from cmk.gui.plugins.watolib.utils import config_variable_registry, filter_unknown_settings
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.userdb import load_users, save_users, Users
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.view_store import get_all_views
from cmk.gui.wato.mkeventd import MACROS_AND_VARS
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.changes import ActivateChangesWriter, add_change
from cmk.gui.watolib.global_settings import (
    GlobalSettings,
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
    save_site_global_settings,
)
from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.watolib.sites import site_globals_editable, SiteManagementFactory
from cmk.gui.watolib.timeperiods import TimeperiodSpec

TimeRange = Tuple[Tuple[int, int], Tuple[int, int]]

# mapping removed check plugins to their replacement:
REMOVED_CHECK_PLUGIN_MAP = {
    CheckPluginName("aix_diskiod"): CheckPluginName("diskstat_io"),
    CheckPluginName("cisco_mem_asa"): CheckPluginName("cisco_mem"),
    CheckPluginName("cisco_mem_asa64"): CheckPluginName("cisco_mem"),
    CheckPluginName("df_netapp32"): CheckPluginName("df_netapp"),
    CheckPluginName("emc_vplex_volumes"): CheckPluginName("diskstat_io_volumes"),
    CheckPluginName("emc_vplex_director_stats"): CheckPluginName("diskstat_io_director"),
    CheckPluginName("fjdarye100_cadaps"): CheckPluginName("fjdarye_channel_adapters"),
    CheckPluginName("fjdarye100_cmods"): CheckPluginName("fjdarye_channel_modules"),
    CheckPluginName("fjdarye100_cmods_mem"): CheckPluginName("fjdarye_controller_modules_memory"),
    CheckPluginName("fjdarye100_conencs"): CheckPluginName("fjdarye_controller_enclosures"),
    CheckPluginName("fjdarye100_cpsus"): CheckPluginName("fjdarye_ce_power_supply_units"),
    CheckPluginName("fjdarye100_devencs"): CheckPluginName("fjdarye_device_enclosures"),
    CheckPluginName("fjdarye100_disks"): CheckPluginName("fjdarye_disks"),
    CheckPluginName("fjdarye100_disks_summary"): CheckPluginName("fjdarye_disks_summary"),
    CheckPluginName("fjdarye100_rluns"): CheckPluginName("fjdarye_rluns"),
    CheckPluginName("fjdarye100_sum"): CheckPluginName("fjdarye_summary_status"),
    CheckPluginName("fjdarye100_syscaps"): CheckPluginName("fjdarye_system_capacitors"),
    CheckPluginName("fjdarye101_cadaps"): CheckPluginName("fjdarye_channel_adapters"),
    CheckPluginName("fjdarye101_cmods"): CheckPluginName("fjdarye_channel_modules"),
    CheckPluginName("fjdarye101_cmods_mem"): CheckPluginName("fjdarye_controller_modules_memory"),
    CheckPluginName("fjdarye101_conencs"): CheckPluginName("fjdarye_controller_enclosures"),
    CheckPluginName("fjdarye101_devencs"): CheckPluginName("fjdarye_device_enclosures"),
    CheckPluginName("fjdarye101_disks"): CheckPluginName("fjdarye_disks"),
    CheckPluginName("fjdarye101_disks_summary"): CheckPluginName("fjdarye_disks_summary"),
    CheckPluginName("fjdarye101_rluns"): CheckPluginName("fjdarye_rluns"),
    CheckPluginName("fjdarye101_sum"): CheckPluginName("fjdarye_summary_status"),
    CheckPluginName("fjdarye101_syscaps"): CheckPluginName("fjdarye_system_capacitors"),
    CheckPluginName("fjdarye200_pools"): CheckPluginName("fjdarye_pools"),
    CheckPluginName("fjdarye500_cadaps"): CheckPluginName("fjdarye_channel_adapters"),
    CheckPluginName("fjdarye500_ca_ports"): CheckPluginName("fjdarye_ca_ports"),
    CheckPluginName("fjdarye500_cmods"): CheckPluginName("fjdarye_channel_modules"),
    CheckPluginName("fjdarye500_cmods_flash"): CheckPluginName("fjdarye_controller_modules_flash"),
    CheckPluginName("fjdarye500_cmods_mem"): CheckPluginName("fjdarye_controller_modules_memory"),
    CheckPluginName("fjdarye500_conencs"): CheckPluginName("fjdarye_controller_enclosures"),
    CheckPluginName("fjdarye500_cpsus"): CheckPluginName("fjdarye_ce_power_supply_units"),
    CheckPluginName("fjdarye500_devencs"): CheckPluginName("fjdarye_device_enclosures"),
    CheckPluginName("fjdarye500_disks"): CheckPluginName("fjdarye_disks"),
    CheckPluginName("fjdarye500_disks_summary"): CheckPluginName("fjdarye_disks_summary"),
    CheckPluginName("fjdarye500_expanders"): CheckPluginName("fjdarye_expanders"),
    CheckPluginName("fjdarye500_inletthmls"): CheckPluginName("fjdarye_inlet_thermal_sensors"),
    CheckPluginName("fjdarye500_pfm"): CheckPluginName("fjdarye_pcie_flash_modules"),
    CheckPluginName("fjdarye500_sum"): CheckPluginName("fjdarye_summary_status"),
    CheckPluginName("fjdarye500_syscaps"): CheckPluginName("fjdarye_system_capacitors"),
    CheckPluginName("fjdarye500_thmls"): CheckPluginName("fjdarye_thermal_sensors"),
    CheckPluginName("fjdarye60_cadaps"): CheckPluginName("fjdarye_channel_adapters"),
    CheckPluginName("fjdarye60_cmods"): CheckPluginName("fjdarye_channel_modules"),
    CheckPluginName("fjdarye60_cmods_flash"): CheckPluginName("fjdarye_controller_modules_flash"),
    CheckPluginName("fjdarye60_cmods_mem"): CheckPluginName("fjdarye_controller_modules_memory"),
    CheckPluginName("fjdarye60_conencs"): CheckPluginName("fjdarye_controller_enclosures"),
    CheckPluginName("fjdarye60_devencs"): CheckPluginName("fjdarye_device_enclosures"),
    CheckPluginName("fjdarye60_disks"): CheckPluginName("fjdarye_disks"),
    CheckPluginName("fjdarye60_disks_summary"): CheckPluginName("fjdarye_disks_summary"),
    CheckPluginName("fjdarye60_expanders"): CheckPluginName("fjdarye_expanders"),
    CheckPluginName("fjdarye60_inletthmls"): CheckPluginName("fjdarye_inlet_thermal_sensors"),
    CheckPluginName("fjdarye60_psus"): CheckPluginName("fjdarye_power_supply_units"),
    CheckPluginName("fjdarye60_rluns"): CheckPluginName("fjdarye_rluns"),
    CheckPluginName("fjdarye60_sum"): CheckPluginName("fjdarye_summary_status"),
    CheckPluginName("fjdarye60_syscaps"): CheckPluginName("fjdarye_system_capacitors"),
    CheckPluginName("fjdarye60_thmls"): CheckPluginName("fjdarye_thermal_sensors"),
    CheckPluginName("hpux_lunstats"): CheckPluginName("diskstat_io"),
}


# List[(old_config_name, new_config_name, replacement_dict{old: new})]
REMOVED_GLOBALS_MAP: List[Tuple[str, str, Dict]] = []

REMOVED_WATO_RULESETS_MAP: Mapping[RulesetName, RulesetName] = {}


@contextmanager
def _save_user_instances(  # type:ignore[no-untyped-def]
    visual_type: visuals.VisualType, all_visuals: Dict
):
    modified_user_instances: Set[UserId] = set()

    yield modified_user_instances

    # Now persist all modified instances
    for user_id in modified_user_instances:
        visuals.save(visual_type, all_visuals, user_id)


class UpdateConfig:
    def __init__(self, logger: logging.Logger, arguments: argparse.Namespace) -> None:
        super().__init__()
        self._arguments = arguments
        self._logger = logger
        # TODO: Fix this cruel hack caused by our funny mix of GUI + console
        # stuff. Currently, we just move the console handler to the top, so
        # both worlds are happy. We really, really need to split business logic
        # from presentation code... :-/
        if log.logger.handlers:
            console_handler = log.logger.handlers[0]
            del log.logger.handlers[:]
            logging.getLogger().addHandler(console_handler)
        self._has_errors = False
        gui_logger.setLevel(
            _our_logging_level_to_gui_logging_level(self._logger.getEffectiveLevel())
        )

    def run(self) -> bool:
        self._has_errors = False
        self._logger.log(VERBOSE, "Initializing application...")

        main_modules.load_plugins()

        # Note: Redis has to be disabled first, the other contexts depend on it
        with cmk.gui.watolib.hosts_and_folders.disable_redis(), gui_context(), SuperUserContext():
            self._check_failed_gui_plugins()
            self._initialize_base_environment()

            self._logger.log(VERBOSE, "Updating Checkmk configuration...")
            self._logger.log(
                VERBOSE,
                f"{tty.red}ATTENTION: Some steps may take a long time depending "
                f"on your installation, e.g. during major upgrades.{tty.normal}",
            )
            total = len(self._steps())
            for count, (step_func, title) in enumerate(self._steps(), start=1):
                self._logger.log(VERBOSE, " %i/%i %s..." % (count, total, title))
                try:
                    with ActivateChangesWriter.disable():
                        step_func()
                except Exception:
                    self._has_errors = True
                    self._logger.error(' + "%s" failed' % title, exc_info=True)
                    if self._arguments.debug:
                        raise

            if not self._has_errors and not is_wato_slave_site():
                # Force synchronization of the config after a successful configuration update
                add_change(
                    "cmk-update-config",
                    "Successfully updated Checkmk configuration",
                    need_sync=True,
                )

        self._logger.log(VERBOSE, "Done")
        return self._has_errors

    def _steps(self) -> List[Tuple[Callable[[], None], str]]:
        return [
            (self._rewrite_visuals, "Migrate Visuals context"),
            (self._update_global_settings, "Update global settings"),
            (self._rewrite_wato_rulesets, "Rewriting rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
            (self._migrate_ldap_connections, "Migrate LDAP connections"),
            (self._adjust_user_attributes, "Set version specific user attributes"),
            (self._rewrite_py2_inventory_data, "Rewriting inventory data"),
            (self._sanitize_audit_log, "Sanitize audit log (Werk #13330)"),
            (self._rename_discovered_host_label_files, "Rename discovered host label files"),
            (
                self._rewrite_servicenow_notification_config,
                "Rewriting notification configuration for ServiceNow",
            ),
            (self._add_site_ca_to_trusted_cas, "Adding site CA to trusted CAs"),
            (self._check_ec_rules, "Disabling unsafe EC rules"),
        ]

    def _initialize_base_environment(self) -> None:
        # Failing to load the config here will result in the loss of *all* services due to (...)
        # EDIT: This is no longer the case; but we probably need the config for other reasons?
        cmk.base.config.load()
        cmk.base.config.load_all_agent_based_plugins(
            cmk.base.check_api.get_check_api_context,
        )

    def _update_global_settings(self) -> None:
        self._update_installation_wide_global_settings()
        self._update_site_specific_global_settings()
        self._update_remote_site_specific_global_settings()

    def _update_installation_wide_global_settings(self) -> None:
        """Update the globals.mk of the local site"""
        # Load full config (with undefined settings)
        global_config = load_configuration_settings(full_config=True)
        self._update_global_config(global_config)
        save_global_settings(global_config)

    def _update_site_specific_global_settings(self) -> None:
        """Update the sitespecific.mk of the local site (which is a remote site)"""
        if not is_wato_slave_site():
            return

        global_config = load_site_global_settings()
        self._update_global_config(global_config)

        save_site_global_settings(global_config)

    def _update_remote_site_specific_global_settings(self) -> None:
        """Update the site specific global settings in the central site configuration"""
        site_mgmt = SiteManagementFactory().factory()
        configured_sites = site_mgmt.load_sites()
        for site_id, site_spec in configured_sites.items():
            if site_globals_editable(site_id, site_spec):
                self._update_global_config(site_spec.setdefault("globals", {}))
        site_mgmt.save_sites(configured_sites, activate=False)

    def _update_global_config(
        self,
        global_config: GlobalSettings,
    ) -> GlobalSettings:
        return self._transform_global_config_values(
            self._update_removed_global_config_vars(global_config)
        )

    def _update_removed_global_config_vars(
        self,
        global_config: GlobalSettings,
    ) -> GlobalSettings:
        # Replace old settings with new ones
        for old_config_name, new_config_name, replacement in REMOVED_GLOBALS_MAP:
            if old_config_name in global_config:
                self._logger.log(
                    VERBOSE, "Replacing %s with %s" % (old_config_name, new_config_name)
                )
                old_value = global_config[old_config_name]
                if replacement:
                    global_config.setdefault(new_config_name, replacement[old_value])
                else:
                    global_config.setdefault(new_config_name, old_value)

                del global_config[old_config_name]

        # Delete unused settings
        global_config = filter_unknown_settings(global_config)
        return global_config

    def _transform_global_config_value(
        self,
        config_var: str,
        config_val: Any,
    ) -> Any:
        return config_variable_registry[config_var]().valuespec().transform_value(config_val)

    def _transform_global_config_values(
        self,
        global_config: GlobalSettings,
    ) -> GlobalSettings:
        global_config.update(
            {
                config_var: self._transform_global_config_value(config_var, config_val)
                for config_var, config_val in global_config.items()
            }
        )
        return global_config

    def _rewrite_autochecks(self) -> None:
        failed_hosts = []

        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()

        for autocheck_file in Path(cmk.utils.paths.autochecks_dir).glob("*.mk"):
            hostname = HostName(autocheck_file.stem)
            store = cmk.base.autochecks.AutochecksStore(hostname)

            try:
                autochecks = store.read()
            except MKGeneralException as exc:
                if self._arguments.debug:
                    raise
                self._logger.error(str(exc))
                failed_hosts.append(hostname)
                continue

            store.write([self._fix_entry(s, all_rulesets, hostname) for s in autochecks])

        if failed_hosts:
            msg = f"Failed to rewrite autochecks file for hosts: {', '.join(failed_hosts)}"
            self._logger.error(msg)
            raise MKGeneralException(msg)

    def _transformed_params(
        self,
        plugin_name: CheckPluginName,
        params: Any,
        all_rulesets: RulesetCollection,
        hostname: str,
    ) -> Any:
        check_plugin = register.get_check_plugin(plugin_name)
        if check_plugin is None:
            return None

        ruleset_name = "checkgroup_parameters:%s" % check_plugin.check_ruleset_name
        if ruleset_name not in all_rulesets.get_rulesets():
            return None

        debug_info = "host=%r, plugin=%r, ruleset=%r, params=%r" % (
            hostname,
            str(plugin_name),
            str(check_plugin.check_ruleset_name),
            params,
        )

        try:
            ruleset = all_rulesets.get_rulesets()[ruleset_name]

            # TODO: in order to keep the original input parameters and to identify misbehaving
            #       transform_values() implementations we check the passed values for modifications
            #       In that case we have to fix that transform_values() before using it
            #       This hack chould vanish as soon as we know transform_values() works as expected
            param_copy = copy.deepcopy(params)
            new_params = ruleset.valuespec().transform_value(param_copy) if params else {}
            if not param_copy == params:
                self._logger.warning(
                    "transform_value() for ruleset '%s' altered input"
                    % check_plugin.check_ruleset_name
                )

            assert new_params or not params, "non-empty params vanished"
            assert not isinstance(params, dict) or isinstance(new_params, dict), (
                "transformed params down-graded from dict: %r" % new_params
            )

            # TODO: in case of known exceptions we don't want the transformed values be combined
            #       with old keys. As soon as we can remove the workaround below we should not
            #       handle any ruleset differently
            if str(check_plugin.check_ruleset_name) in {"if", "filesystem"}:
                return new_params

            # TODO: some transform_value() implementations (e.g. 'ps') return parameter with
            #       missing keys - so for safety-reasons we keep keys that don't exist in the
            #       transformed values
            #       On the flipside this can lead to problems with the check itself and should
            #       be vanished as soon as we can be sure no keys are deleted accidentally
            return {**params, **new_params} if isinstance(params, dict) else new_params

        except Exception as exc:
            msg = "Transform failed: %s, error=%r" % (debug_info, exc)
            if self._arguments.debug:
                raise RuntimeError(msg) from exc
            self._logger.error(msg)

        return None

    def _fix_entry(
        self,
        entry: cmk.base.autochecks.AutocheckEntry,
        all_rulesets: RulesetCollection,
        hostname: str,
    ) -> cmk.base.autochecks.AutocheckEntry:
        """Change names of removed plugins to the new ones and transform parameters"""
        new_plugin_name = REMOVED_CHECK_PLUGIN_MAP.get(entry.check_plugin_name)
        new_params = self._transformed_params(
            new_plugin_name or entry.check_plugin_name,
            entry.parameters,
            all_rulesets,
            hostname,
        )

        if new_plugin_name is None and new_params is None:
            # don't create a new entry if nothing has changed
            return entry

        return cmk.base.autochecks.AutocheckEntry(
            check_plugin_name=new_plugin_name or entry.check_plugin_name,
            item=entry.item,
            parameters=new_params or entry.parameters,
            service_labels=entry.service_labels,
        )

    def _rewrite_wato_rulesets(self) -> None:
        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()
        self._transform_fileinfo_timeofday_to_timeperiods(all_rulesets)
        self._transform_replaced_wato_rulesets(
            all_rulesets,
            REMOVED_WATO_RULESETS_MAP,
        )
        self._transform_wato_rulesets_params(all_rulesets)
        self._remove_removed_check_plugins_from_ignored_checks(
            all_rulesets,
            REMOVED_CHECK_PLUGIN_MAP,
        )
        self._validate_rule_values(all_rulesets)
        all_rulesets.save()

    def _transform_replaced_wato_rulesets(
        self,
        all_rulesets: RulesetCollection,
        replaced_rulesets: Mapping[RulesetName, RulesetName],
    ) -> None:
        deprecated_ruleset_names: Set[RulesetName] = set()
        for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
            if ruleset_name not in replaced_rulesets:
                continue

            new_ruleset = all_rulesets.get(replaced_rulesets[ruleset_name])

            if not new_ruleset.is_empty():
                self._logger.log(VERBOSE, "Found deprecated ruleset: %s" % ruleset_name)

            self._logger.log(
                VERBOSE, "Replacing ruleset %s with %s" % (ruleset_name, new_ruleset.name)
            )
            for folder, _folder_index, rule in ruleset.get_rules():
                new_ruleset.append_rule(folder, rule)

            deprecated_ruleset_names.add(ruleset_name)

        for deprecated_ruleset_name in deprecated_ruleset_names:
            all_rulesets.delete(deprecated_ruleset_name)

    def _transform_wato_rulesets_params(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        num_errors = 0
        for ruleset in all_rulesets.get_rulesets().values():
            valuespec = ruleset.valuespec()
            for folder, folder_index, rule in ruleset.get_rules():
                try:
                    rule.value = valuespec.transform_value(rule.value)
                except Exception as e:
                    if self._arguments.debug:
                        raise
                    self._logger.error(
                        "ERROR: Failed to transform rule: (Ruleset: %s, Folder: %s, "
                        "Rule: %d, Value: %s: %s",
                        ruleset.name,
                        folder.path(),
                        folder_index,
                        rule.value,
                        e,
                    )
                    num_errors += 1

        if num_errors and self._arguments.debug:
            raise MKGeneralException("Failed to transform %d rule values" % num_errors)

    def _validate_rule_values(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        rulesets_skip = {
            # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
            # see all of them
            "extra_service_conf:_sla_config",
        }

        n_invalid = 0
        for ruleset in all_rulesets.get_rulesets().values():
            if ruleset.name in rulesets_skip:
                continue

            for folder, index, rule in ruleset.get_rules():
                try:
                    ruleset.rulespec.valuespec.validate_value(
                        rule.value,
                        "",
                    )
                except MKUserError as excpt:
                    n_invalid += 1
                    self._logger.warning(
                        _format_warning(
                            "WARNING: Invalid rule configuration detected (Ruleset: %s, Title: %s, "
                            "Folder: %s,\nRule nr: %s, Exception: %s)"
                        ),
                        ruleset.name,
                        ruleset.title(),
                        folder.path(),
                        index + 1,
                        excpt,
                    )

        if n_invalid:
            self._logger.warning(
                _format_warning(
                    "Detected %s issue(s) in configured rules.\n"
                    "To correct these issues, we recommend to open the affected rules in the GUI.\n"
                    "Upon attempting to save them, any problematic fields will be highlighted."
                ),
                n_invalid,
            )

    def _remove_removed_check_plugins_from_ignored_checks(
        self,
        all_rulesets: RulesetCollection,
        removed_check_plugins: Container[CheckPluginName],
    ) -> None:
        ignored_checks_ruleset = all_rulesets.get("ignored_checks")
        for _folder, _index, rule in ignored_checks_ruleset.get_rules():
            if plugins_to_keep := [
                plugin_str
                for plugin_str in rule.value
                if CheckPluginName(plugin_str).create_basic_name() not in removed_check_plugins
            ]:
                rule.value = plugins_to_keep
            else:
                ignored_checks_ruleset.delete_rule(
                    rule,
                    create_change=False,
                )

    def _transform_time_range(self, time_range: TimeRange) -> Tuple[str, str]:
        begin_time = dt_time(hour=time_range[0][0], minute=time_range[0][1])
        end_time = dt_time(hour=time_range[1][0], minute=time_range[1][1])
        return (begin_time.strftime("%H:%M"), end_time.strftime("%H:%M"))

    def _get_timeperiod_name(self, timeofday: Sequence[TimeRange]) -> str:
        periods = [self._transform_time_range(t) for t in timeofday]
        period_string = "_".join((f"{b}-{e}" for b, e in periods)).replace(":", "")
        return f"timeofday_{period_string}"

    def _create_timeperiod(self, name: str, timeofday: Sequence[TimeRange]) -> None:
        periods = [self._transform_time_range(t) for t in timeofday]
        periods_alias = ", ".join((f"{b}-{e}" for b, e in periods))

        timeperiod: TimeperiodSpec = {
            "alias": f"Created by migration of timeofday parameter ({periods_alias})",
            **{
                d: periods
                for d in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            },
        }
        timeperiods.save_timeperiod(name, timeperiod)

    def _transform_fileinfo_timeofday_to_timeperiods(self, all_rulesets: RulesetCollection) -> None:
        """Transforms the deprecated timeofday parameter to timeperiods

        In the general case, timeperiods shouldn't be specified if timeofday is used.
        It wasn't restriced, but it doesn't make sense to have both.
        In case of timeofday in the default timeperiod, timeofday time range is
        used and other timeperiods are removed.
        In case of timeofday in the non-default timeperiod, timeofday param is removed.

        This transformation is introduced in v2.2 and can be removed in v2.3.
        """
        ruleset = all_rulesets.get_rulesets()["checkgroup_parameters:fileinfo"]
        for _folder, _folder_index, rule in ruleset.get_rules():
            # in case there are timeperiods, look at default timepriod params
            rule_params = rule.value.get("tp_default_value", rule.value)

            timeofday = rule_params.get("timeofday")
            if not timeofday:
                # delete timeofday from non-default timeperiods
                # this configuration doesn't make sense at all, there is nothing to transform it to
                for _, tp_params in rule.value.get("tp_values", {}):
                    tp_params.pop("timeofday", None)
                continue

            timeperiod_name = self._get_timeperiod_name(timeofday)
            if timeperiod_name not in timeperiods.load_timeperiods():
                self._create_timeperiod(timeperiod_name, timeofday)

            thresholds = {
                k: p
                for k, p in rule_params.items()
                if k not in ("timeofday", "tp_default_value", "tp_values")
            }
            tp_values = [(timeperiod_name, thresholds)]

            rule.value = {"tp_default_value": {}, "tp_values": tp_values}

    def _check_failed_gui_plugins(self) -> None:
        failed_plugins = cmk.gui.utils.get_failed_plugins()
        if failed_plugins:
            self._logger.error("")
            self._logger.error(
                "ERROR: Failed to load some GUI plugins. You will either have \n"
                "       to remove or update them to be compatible with this \n"
                "       Checkmk version."
            )
            self._logger.error("")

    def _cleanup_version_specific_caches(self) -> None:
        paths = [
            Path(cmk.utils.paths.include_cache_dir, "builtin"),
            Path(cmk.utils.paths.include_cache_dir, "local"),
            Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
            Path(cmk.utils.paths.precompiled_checks_dir, "local"),
        ]

        walk_cache_dir = Path(cmk.utils.paths.var_dir, "snmp_cache")
        if walk_cache_dir.exists():
            paths.extend(walk_cache_dir.iterdir())

        for base_dir in paths:
            try:
                for f in base_dir.iterdir():
                    f.unlink()
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise  # Do not fail on missing directories / files

        # The caches might contain visuals in a deprecated format. For example, in 2.2, painters in
        # visuals are represented by a dedicated type, which was not the case the before. The caches
        # from 2.1 will still contain the old data structures.
        visuals._CombinedVisualsCache.invalidate_all_caches()

    def _rewrite_visuals(self):
        """This function uses the updates in visuals.transform_old_visual which
        takes place upon visuals load. However, load forces no save, thus save
        the transformed visual in this update step. All user configs are rewriten.
        The load and transform functions are specific to each visual, saving is generic."""

        def updates(  # type:ignore[no-untyped-def]
            visual_type: visuals.VisualType, all_visuals: Dict
        ):
            with _save_user_instances(visual_type, all_visuals) as affected_user:
                # skip builtins, only users
                affected_user.update(owner for owner, _name in all_visuals if owner)

        updates(visuals.VisualType.views, get_all_views())
        updates(visuals.VisualType.dashboards, get_all_dashboards())

        # Reports
        try:
            import cmk.gui.cee.reporting as reporting
        except ImportError:
            reporting = None  # type: ignore[assignment]

        if reporting:
            reporting.load_reports()  # Loading does the transformation
            updates(visuals.VisualType.reports, reporting.reports)

    def _migrate_ldap_connections(self) -> None:
        """Each user connections needs to declare it's connection type.

        This is done using the "type" attribute. Previous versions did not always set this
        attribute, which is corrected with this update method.

        Furthermore, convert to password store compatible format"""
        connections = load_connection_config()
        if not connections:
            return

        for connection in connections:
            connection.setdefault("type", "ldap")

            if "bind" in connection:
                dn, password = connection["bind"]
                if isinstance(password, tuple):
                    continue
                connection["bind"] = (dn, ("password", password))

        save_connection_config(connections)

    def _adjust_user_attributes(self) -> None:
        """All users are loaded and attributes can be transformed or set."""
        users: Users = load_users(lock=True)
        has_deprecated_ldap_connection: bool = any(
            connection for connection in load_connection_config() if connection.get("id") == "ldap"
        )
        for user_id in users:
            # pre 2.0 user
            if users[user_id].get("user_scheme_serial") is None:
                _add_show_mode(users, user_id)

            _add_user_scheme_serial(users, user_id)
            _cleanup_ldap_connector(users, user_id, has_deprecated_ldap_connection)

        save_users(users, datetime.now())

    def _rewrite_py2_inventory_data(self) -> None:
        done_path = Path(cmk.utils.paths.var_dir, "update_config")
        done_file = done_path / "py2conversion.done"
        if done_file.exists():
            self._logger.log(VERBOSE, "Skipping py2 inventory data update (already done)")
            return

        dirpaths = [
            Path(cmk.utils.paths.var_dir + "/inventory/"),
            Path(cmk.utils.paths.var_dir + "/inventory_archive/"),
            Path(cmk.utils.paths.tmp_dir + "/status_data/"),
        ]
        filepaths: List[Path] = []
        for dirpath in dirpaths:
            if not dirpath.exists():
                self._logger.log(VERBOSE, "Skipping path %r (empty)" % str(dirpath))
                continue

            # Create a list of all files that need to be converted with 2to3
            if "inventory_archive" in str(dirpath):
                self._find_files_recursively(filepaths, dirpath)
            else:
                filepaths += [
                    f
                    for f in dirpath.iterdir()
                    if not f.name.endswith(".gz") and not f.name.startswith(".")
                ]

        with multiprocessing.Pool(min(15, multiprocessing.cpu_count())) as pool:
            py2_files = [str(x) for x in pool.map(self._needs_to_be_converted, filepaths) if x]

        self._logger.log(VERBOSE, "Finished checking for corrupt files")

        if not py2_files:
            self._create_donefile(done_file)
            return

        self._logger.log(VERBOSE, "Found %i files: %s" % (len(py2_files), py2_files))

        returncode = self._fix_with_2to3(py2_files)

        # Rewriting .gz files
        for filepath in py2_files:
            if "inventory_archive" not in str(filepath):
                with open(filepath, "rb") as f_in, gzip.open(str(filepath) + ".gz", "wb") as f_out:
                    f_out.writelines(f_in)

        if returncode == 0:
            self._create_donefile(done_file)

    def _create_donefile(self, done_file: Path) -> None:
        self._logger.log(VERBOSE, "Creating file %r" % str(done_file))
        done_file.parent.mkdir(parents=True, exist_ok=True)
        done_file.touch(exist_ok=True)

    def _fix_with_2to3(self, files: List[str]) -> int:
        self._logger.log(VERBOSE, "Try to fix corrupt files with 2to3")
        cmd = [
            "2to3",
            "--write",
            "--nobackups",
        ] + files

        self._logger.log(VERBOSE, "Executing: %s", subprocess.list2cmdline(cmd))
        completed_process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            check=False,
        )
        if completed_process.returncode != 0:
            self._logger.error(
                "Failed to run 2to3 (Exit code: %d): %s",
                completed_process.returncode,
                completed_process.stdout,
            )
        self._logger.log(VERBOSE, "Finished.")
        return completed_process.returncode

    def _needs_to_be_converted(self, filepath: Path) -> Optional[Path]:
        with filepath.open(encoding="utf-8") as f:
            # Try to evaluate data with ast.literal_eval
            try:
                data = f.read()
                self._logger.debug("Evaluating %r" % str(filepath))
                ast.literal_eval(data)
            except SyntaxError:
                self._logger.log(VERBOSE, "Found corrupt file %r" % str(filepath))
                return filepath
        return None

    def _find_files_recursively(self, files: List[Path], path: Path) -> None:
        for f in path.iterdir():
            if f.is_file():
                if not f.name.endswith(".gz") and not f.name.startswith("."):
                    files.append(f)
            elif f.is_dir():
                self._find_files_recursively(files, f)

    def _sanitize_audit_log(self) -> None:
        # Use a file to determine if the sanitization was successfull. Otherwise it would be
        # run on every update and we want to tamper with the audit log as little as possible.
        log_dir = AuditLogStore.make_path().parent

        update_flag = log_dir / ".werk-13330"
        if update_flag.is_file():
            self._logger.log(VERBOSE, "Skipping (already done)")
            return

        logs = list(log_dir.glob("wato_audit.*"))
        if not logs:
            self._logger.log(VERBOSE, "Skipping (nothing to do)")
            update_flag.touch(mode=0o660)
            return

        backup_dir = Path.home() / "audit_log_backup"
        backup_dir.mkdir(mode=0o750, exist_ok=True)
        for l in logs:
            shutil.copy(src=l, dst=backup_dir / l.name)
        self._logger.info(
            f"{tty.yellow}Wrote audit log backup to {backup_dir}. Please check if the audit log "
            f"in the GUI works as expected. In case of problems you can copy the backup files back to "
            f"{log_dir}. Please check the corresponding files in {log_dir} for any leftover passwords "
            f"and remove them if necessary. If everything works as expected you can remove the "
            f"backup. For further details please have a look at Werk #13330.{tty.normal}"
        )

        self._logger.log(VERBOSE, "Sanitizing log files: %s", ", ".join(map(str, logs)))
        sanitizer = PasswordSanitizer()

        for l in logs:
            store = AuditLogStore(l)
            entries = [sanitizer.replace_password(e) for e in store.read()]
            store.write(entries)
        self._logger.log(VERBOSE, "Finished sanitizing log files")

        update_flag.touch(mode=0o660)
        self._logger.log(VERBOSE, "Wrote sanitization flag file %s", update_flag)

    def _rename_discovered_host_label_files(self) -> None:
        config_cache = cmk.base.config.get_config_cache()
        for host_name in config_cache.all_configured_realhosts():
            old_path = (cmk.utils.paths.discovered_host_labels_dir / host_name).with_suffix(".mk")
            new_path = cmk.utils.paths.discovered_host_labels_dir / (host_name + ".mk")
            if old_path == new_path:
                continue

            if old_path.exists() and not new_path.exists():
                self._logger.debug(
                    "Rename discovered host labels file from '%s' to '%s'", old_path, new_path
                )
                old_path.rename(new_path)

    def _rewrite_servicenow_notification_config(self) -> None:
        # Management type "case" introduced with werk #13096 in 2.1.0i1
        notification_rules = load_notification_rules()
        for index, rule in enumerate(notification_rules):
            plugin_name = rule["notify_plugin"][0]
            if plugin_name != "servicenow":
                continue

            params = rule["notify_plugin"][1]
            if "mgmt_types" in params:
                continue

            assert isinstance(params, dict)

            incident_params = {
                key: params.pop(key)
                for key in [
                    "caller",
                    "host_short_desc",
                    "svc_short_desc",
                    "host_desc",
                    "svc_desc",
                    "urgency",
                    "impact",
                    "ack_state",
                    "recovery_state",
                    "dt_state",
                ]
                if key in params
            }
            params["mgmt_type"] = ("incident", incident_params)

            notification_rules[index]["notify_plugin"] = (plugin_name, params)

        save_notification_rules(notification_rules)

    def _add_site_ca_to_trusted_cas(self) -> None:
        site_ca = (
            site_cas[-1]
            if (site_cas := raw_certificates_from_file(cmk.utils.paths.site_cert_file))
            else None
        )

        if not site_ca:
            return

        global_config = load_configuration_settings(full_config=True)
        cert_settings = global_config.setdefault(
            "trusted_certificate_authorities", {"use_system_wide_cas": True, "trusted_cas": []}
        )
        # For remotes with config sync the settings would be overwritten by activate changes. To keep the config
        # consistent exclude remotes during the update.
        if is_wato_slave_site() or site_ca in cert_settings["trusted_cas"]:
            return

        cert_settings["trusted_cas"].append(site_ca)
        save_global_settings(global_config)

    def _check_ec_rules(self) -> None:
        """check for macros in EC scripts and disable them if found

        The macros in shell scripts cannot be gated by quotes or something, so
        an attacker could craft malicious logs and insert code.

        This routine goes through all rules, checks for macros in the scripts
        and then disables them"""
        global_config = load_configuration_settings(full_config=True)
        for action in global_config.get("actions", []):
            if action["action"][0] == "script":
                if not self._has_script_macros(action["action"][1]["script"]):
                    self._logger.debug("Script %r doesn't use macros, that's good", action["id"])
                    continue
                if action["disabled"]:
                    self._logger.info(
                        "Script %r uses macros but was already disabled. Be careful if you enable this!",
                        action["id"],
                    )
                else:
                    self._logger.warning(
                        "Script %r uses macros. We disable it. Please replace the macros with proper variables before enabling it again!",
                        action["id"],
                    )
                    action["disabled"] = True
        save_global_settings(global_config)

    @staticmethod
    def _has_script_macros(script_text: str) -> bool:
        """check if a script uses macros"""
        for macro_name, _description in MACROS_AND_VARS:
            if f"${macro_name}$" in script_text:
                return True
        return False


class PasswordSanitizer:
    """
    Due to a bug the audit log could contain clear text passwords. This class replaces clear text
    passwords in audit log entries on a best-effort basis. This is no 100% solution! After Werk
    #13330 no clear text passwords are written to the audit log anymore.
    """

    CHANGED_PATTERN = re.compile(
        r'Value of "value/('
        r"\[1\]auth/\[1|"
        r"auth/\[1|"
        r"auth_basic/password/\[1|"
        r"\[2\]authentication/\[1|"
        r"basicauth/\[1|"
        r"basicauth/\[1]\[1|"
        r"api_token\"|"
        r"client_secret\"|"
        r"\[0\]credentials/\[1\]\[1|"
        r"credentials/\[1|"
        r"credentials/\[1\]\[1|"
        r"credentials/\[1\]\[1\]\[1|"
        r"credentials/\[\d+\]\[3\]\[1\]\[1|"
        r"credentials_sap_connect/\[1\]\[1|"
        r"fetch/\[1\]auth/\[1\]\[1|"
        r"imap_parameters/auth/\[1\]\[1|"
        r"instance/api_key/\[1|"
        r"instance/app_key/\[1|"
        r"instances/\[0\]passwd\"|"
        r"login/\[1|"
        r"login/auth/\[1\]\[1|"
        r"login_asm/auth/\[1\]\[1|"
        r"login_exceptions/\[0\]\[1\]auth/\[1\]\[1|"
        r"mode/\[1\]auth/\[1\]\[1|"
        r"password\"|"
        r"\[1\]password\"|"
        r"password/\[1|"
        r"proxy/auth/\[1\]\[1|"
        r"proxy/proxy_protocol/\[1\]credentials/\[1|"
        r"proxy_details/proxy_password/\[1|"
        r"smtp_auth/\[1\]\[1|"
        r"token/\[1|"
        r"secret\"|"
        r"secret/\[1|"
        r"secret_access_key/\[1|"
        r"passphrase\""
        # Even if values contain double quotes the outer quotes remain double quotes.
        # That .* is greedy is not a problem here since each change is on its own line.
        r') changed from "(.*)" to "(.*)"\.'
    )

    _QUOTED_STRING = r"(\"(?:(?!(?<!\\)\").)*\"|'(?:(?!(?<!\\)').)*')"

    NEW_NESTED_PATTERN = re.compile(
        rf"'login': \({_QUOTED_STRING}, {_QUOTED_STRING}, {_QUOTED_STRING}\)|"
        rf"\('password', {_QUOTED_STRING}\)|"
        rf"'(auth|authentication|basicauth|credentials)': \({_QUOTED_STRING}, {_QUOTED_STRING}\)|"
        rf"'(auth|credentials)': \('(explicit|configured)', \({_QUOTED_STRING}, {_QUOTED_STRING}\)\)"
    )

    NEW_DICT_ENTRY_PATTERN = (
        r"'("
        r"api_token|"
        r"auth|"
        r"authentication|"
        r"client_secret|"
        r"passphrase|"
        r"passwd|"
        r"password|"
        r"secret"
        rf")': {_QUOTED_STRING}"
    )

    def replace_password(self, entry: AuditLogStore.Entry) -> AuditLogStore.Entry:
        if entry.diff_text and entry.action in ("edit-rule", "new-rule"):
            diff_edit = re.sub(self.CHANGED_PATTERN, self._changed_match_function, entry.diff_text)
            diff_nested = re.sub(
                self.NEW_NESTED_PATTERN, self._new_nested_match_function, diff_edit
            )
            diff_text = re.sub(
                self.NEW_DICT_ENTRY_PATTERN, self._new_single_key_match_function, diff_nested
            )
            return entry._replace(diff_text=diff_text)
        return entry

    def _changed_match_function(self, match: re.Match) -> str:
        return 'Value of "value/%s changed from "hash:%s" to "hash:%s".' % (
            match.group(1),
            self._hash(match.group(2)),
            self._hash(match.group(3)),
        )

    def _new_nested_match_function(self, match: re.Match) -> str:
        if match.group(1):
            return "'login': (%s, 'hash:%s', %s)" % (
                match.group(1),
                self._hash(match.group(2)[1:-1]),
                match.group(3),
            )
        if match.group(4):
            return "('password', 'hash:%s')" % self._hash(match.group(4)[1:-1])
        if match.group(5):
            return "'%s': (%s, 'hash:%s')" % (
                match.group(5),
                match.group(6),
                self._hash(match.group(7)[1:-1]),
            )
        return "'%s': ('%s', (%s, 'hash:%s'))" % (
            match.group(8),
            match.group(9),
            match.group(10),
            self._hash(match.group(11)[1:-1]),
        )

    def _new_single_key_match_function(self, match: re.Match) -> str:
        return "'%s': 'hash:%s'" % (match.group(1), self._hash(match.group(2)[1:-1]))

    def _hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()[:10]


def _format_warning(msg: str) -> str:
    return "\033[93m {}\033[00m".format(msg)


def _add_show_mode(users: Users, user_id: UserId) -> Users:
    """Set show_mode for existing user to 'default to show more' on upgrade to
    2.0"""
    users[user_id]["show_mode"] = "default_show_more"
    return users


def _add_user_scheme_serial(users: Users, user_id: UserId) -> Users:
    """Set attribute to detect with what cmk version the user was
    created. We start that with 2.0"""
    users[user_id]["user_scheme_serial"] = USER_SCHEME_SERIAL
    return users


def _cleanup_ldap_connector(
    users: Users,
    user_id: UserId,
    has_deprecated_ldap_connection: bool,
) -> Users:
    """Transform LDAP connector attribute of older versions to new format"""
    connection_id: Optional[str] = users[user_id].get("connector")
    if connection_id is None:
        connection_id = "htpasswd"

    # Old Checkmk used a static "ldap" connector id for all LDAP users.
    # Since Checkmk now supports multiple LDAP connections, the ID has
    # been changed to "default". But only transform this when there is
    # no connection existing with the id LDAP.
    if connection_id == "ldap" and not has_deprecated_ldap_connection:
        connection_id = "default"

    users[user_id]["connector"] = connection_id

    return users


def _id_from_title(title: str) -> str:
    return re.sub("[^-a-zA-Z0-9_]+", "", title.lower().replace(" ", "_"))


def _our_logging_level_to_gui_logging_level(lvl: int) -> int:
    """The default in cmk.gui is WARNING, whereas our default is INFO. Hence, our default
    corresponds to INFO in cmk.gui, which results in too much logging.
    """
    return lvl + 10


def main(args: List[str]) -> int:
    arguments = parse_arguments(args)
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))
    logger = logging.getLogger("cmk.update_config")
    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    try:
        has_errors = UpdateConfig(logger, arguments).run()
    except Exception:
        if arguments.debug:
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-update-config -v" '
            "BEFORE starting the site again."
        )
        return 1
    return 1 if has_errors else 0


def parse_arguments(args: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (use multiple times for more output)",
    )

    return p.parse_args(args)


# RRD migration cleaups


def check_df_includes_use_new_metric() -> None:
    "Check that df.include files can return fs_used metric name"
    df_file = cmk.utils.paths.local_checks_dir / "df.include"
    if df_file.exists():
        with df_file.open("r") as fid:
            r = fid.read()
            mat = re.search("fs_used", r, re.M)
            if not mat:
                msg = (
                    "source: %s\n Returns the wrong perfdata\n" % df_file
                    + "Checkmk 2.0 requires Filesystem check plugins to deliver "
                    '"Used filesystem space" perfdata under the metric name fs_used. '
                    "Your local extension pluging seems to be using the old convention "
                    "of mountpoints as the metric name. Please update your include file "
                    "to match our reference implementation."
                )
                raise RuntimeError(msg)
