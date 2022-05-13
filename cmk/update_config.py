#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import time
from contextlib import contextmanager, suppress
from pathlib import Path, PureWindowsPath
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    Iterable,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Tuple,
)

from cryptography import x509

import cmk.utils
import cmk.utils.certs as certs
import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.site
import cmk.utils.tty as tty
from cmk.utils import password_store, version
from cmk.utils.bi.bi_legacy_config_converter import BILegacyPacksConverter
from cmk.utils.check_utils import maincheckify
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import VERBOSE
from cmk.utils.regex import unescape
from cmk.utils.store import load_from_mk_file, save_mk_file
from cmk.utils.type_defs import (
    CheckPluginName,
    ContactgroupName,
    HostName,
    HostOrServiceConditionRegex,
    UserId,
)

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
import cmk.base.autochecks
import cmk.base.check_api
import cmk.base.config
from cmk.base.api.agent_based import register
from cmk.base.autochecks.migration import load_unmigrated_autocheck_entries

import cmk.gui.config
import cmk.gui.groups
import cmk.gui.pagetypes as pagetypes
import cmk.gui.utils
import cmk.gui.visuals as visuals
import cmk.gui.watolib.groups
import cmk.gui.watolib.hosts_and_folders
import cmk.gui.watolib.rulesets
import cmk.gui.watolib.tags
from cmk.gui import main_modules
from cmk.gui.bi import BIManager
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger as gui_logger
from cmk.gui.plugins.dashboard.utils import (
    builtin_dashboards,
    get_all_dashboards,
    transform_stats_dashlet,
    transform_timerange_dashlet,
    transform_topology_dashlet,
)
from cmk.gui.plugins.userdb.utils import (
    load_connection_config,
    save_connection_config,
    USER_SCHEME_SERIAL,
)
from cmk.gui.plugins.views.utils import get_all_views
from cmk.gui.plugins.wato.utils import config_variable_registry
from cmk.gui.plugins.watolib.utils import filter_unknown_settings
from cmk.gui.sites import has_wato_slave_sites, is_wato_slave_site
from cmk.gui.userdb import load_users, save_users, Users
from cmk.gui.utils.logged_in import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.changes import (
    ActivateChangesWriter,
    add_change,
    AuditLogStore,
    ObjectRef,
    ObjectRefType,
)
from cmk.gui.watolib.global_settings import GlobalSettings
from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.watolib.sites import site_globals_editable, SiteManagementFactory

import cmk.update_rrd_fs_names  # pylint: disable=cmk-module-layer-violation  # TODO: this should be fine

# mapping removed check plugins to their replacement:
REMOVED_CHECK_PLUGIN_MAP = {
    CheckPluginName("aix_if"): CheckPluginName("interfaces"),
    CheckPluginName("aix_memory"): CheckPluginName("mem_used"),
    CheckPluginName("cisco_mem_asa64"): CheckPluginName("cisco_mem_asa"),
    CheckPluginName("datapower_tcp"): CheckPluginName("tcp_conn_stats"),
    CheckPluginName("docker_container_mem"): CheckPluginName("mem_used"),
    CheckPluginName("emc_vplex_if"): CheckPluginName("interfaces"),
    CheckPluginName("entity_sensors"): CheckPluginName("entity_sensors_temp"),
    CheckPluginName("hp_msa_if"): CheckPluginName("interfaces"),
    CheckPluginName("hr_mem"): CheckPluginName("mem_used"),
    CheckPluginName("if64adm"): CheckPluginName("if64"),
    CheckPluginName("if64_tplink"): CheckPluginName("interfaces"),
    CheckPluginName("if_brocade"): CheckPluginName("interfaces"),
    CheckPluginName("if"): CheckPluginName("interfaces"),
    CheckPluginName("if_fortigate"): CheckPluginName("interfaces"),
    CheckPluginName("if_lancom"): CheckPluginName("interfaces"),
    CheckPluginName("ps_perf"): CheckPluginName("ps"),
    CheckPluginName("snmp_uptime"): CheckPluginName("uptime"),
    CheckPluginName("solaris_mem"): CheckPluginName("mem_used"),
    CheckPluginName("statgrab_disk"): CheckPluginName("diskstat"),
    CheckPluginName("statgrab_mem"): CheckPluginName("mem_used"),
    CheckPluginName("statgrab_net"): CheckPluginName("interfaces"),
    CheckPluginName("ucs_bladecenter_if"): CheckPluginName("interfaces"),
    CheckPluginName("vms_if"): CheckPluginName("interfaces"),
    CheckPluginName("winperf_tcp_conn"): CheckPluginName("tcp_conn_stats"),
    CheckPluginName("cisco_wlc_clients"): CheckPluginName("wlc_clients"),
    CheckPluginName("aruba_wlc_clients"): CheckPluginName("wlc_clients"),
    CheckPluginName("pdu_gude_8301"): CheckPluginName("pdu_gude"),
    CheckPluginName("pdu_gude_8310"): CheckPluginName("pdu_gude"),
    CheckPluginName("ucd_cpu_load"): CheckPluginName("cpu_loads"),
    CheckPluginName("hpux_cpu"): CheckPluginName("cpu_loads"),
    CheckPluginName("mcafee_emailgateway_cpuload"): CheckPluginName("cpu_loads"),
    CheckPluginName("statgrab_load"): CheckPluginName("cpu_loads"),
    CheckPluginName("arbor_peakflow_sp_cpu_load"): CheckPluginName("cpu_loads"),
    CheckPluginName("arbor_peakflow_tms_cpu_load"): CheckPluginName("cpu_loads"),
    CheckPluginName("arbor_pravail_cpu_load"): CheckPluginName("cpu_loads"),
    CheckPluginName("lxc_container_cpu"): CheckPluginName("cpu_utilization_os"),
    CheckPluginName("docker_container_cpu"): CheckPluginName("cpu_utilization_os"),
    CheckPluginName("docker_container_diskstat"): CheckPluginName("diskstat"),
    CheckPluginName("check_mk_agent_update"): CheckPluginName("checkmk_agent"),
    CheckPluginName("ovs_bonding"): CheckPluginName("bonding"),
    CheckPluginName("lnx_bonding"): CheckPluginName("bonding"),
    CheckPluginName("windows_os_bonding"): CheckPluginName("bonding"),
}

# List[(old_config_name, new_config_name, replacement_dict{old: new})]
REMOVED_GLOBALS_MAP: List[Tuple[str, str, Dict]] = [
    # 2.0: The value has been changed from a bool to the ident of the backend
    ("use_inline_snmp", "snmp_backend_default", {True: "inline", False: "classic"}),
    # 2.0: Variable was renamed
    ("config", "notification_spooler_config", {}),
    # 2.0: Helper model was changed. We use the previous number of helpers to
    # initialize the number of fetchers.
    ("cmc_cmk_helpers", "cmc_fetcher_helpers", {}),
]

REMOVED_WATO_RULESETS_MAP = {
    "non_inline_snmp_hosts": "snmp_backend_hosts",
}

_MATCH_SINGLE_BACKSLASH = re.compile(r"[^\\]\\[^\\]")


@contextmanager
def _save_user_instances(visual_type: str, all_visuals: Dict):
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
            (self._rewrite_password_store, "Rewriting password store"),
            (self._rewrite_visuals, "Migrate Visuals context"),
            (self._migrate_dashlets, "Migrate dashlets"),
            (self._update_global_settings, "Update global settings"),
            (self._rewrite_wato_tag_config, "Rewriting tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
            # CAUTION: update_fs_used_name must be called *after* rewrite_autochecks!
            (self._update_fs_used_name, "Migrating fs_used name"),
            (self._migrate_pagetype_topics_to_ids, "Migrate pagetype topics"),
            (self._migrate_ldap_connections, "Migrate LDAP connections"),
            (self._rewrite_bi_configuration, "Rewrite BI Configuration"),
            (self._adjust_user_attributes, "Set version specific user attributes"),
            (self._rewrite_py2_inventory_data, "Rewriting inventory data"),
            (self._migrate_pre_2_0_audit_log, "Migrate audit log"),
            (self._sanitize_audit_log, "Sanitize audit log (Werk #13330)"),
            (self._rename_discovered_host_label_files, "Rename discovered host label files"),
            (self._transform_groups, "Rewriting host, service or contact groups"),
            (
                self._rewrite_servicenow_notification_config,
                "Rewriting notification configuration for ServiceNow",
            ),
            (self._renew_site_cert, "Renewing certificates without server name extension"),
            (self._add_site_ca_to_trusted_cas, "Adding site CA to trusted CAs"),
            (self._update_mknotifyd, "Rewrite mknotifyd config for central site"),
            (self._transform_influxdb_connnections, "Rewriting InfluxDB connections"),
        ]

    def _initialize_base_environment(self) -> None:
        # Failing to load the config here will result in the loss of *all*
        # services due to an exception thrown by cmk.base.config.service_description
        # in _parse_autocheck_entry of cmk.base.autochecks.
        cmk.base.config.load()
        cmk.base.config.load_all_agent_based_plugins(cmk.base.check_api.get_check_api_context)

    # FS_USED UPDATE DELETE THIS FOR CMK 1.8, THIS ONLY migrates 1.6->2.0
    def _update_fs_used_name(self) -> None:
        check_df_includes_use_new_metric()
        cmk.update_rrd_fs_names.update()

    def _rewrite_wato_tag_config(self) -> None:
        tag_config_file = cmk.gui.watolib.tags.TagConfigFile()
        tag_config = cmk.utils.tags.TagConfig.from_config(tag_config_file.load_for_reading())
        tag_config_file.save(tag_config.get_dict_format())

    def _rewrite_wato_host_and_folder_config(self) -> None:
        root_folder = cmk.gui.watolib.hosts_and_folders.Folder.root_folder()
        if root_folder.title() == "Main directory":
            root_folder.edit(new_title="Main", new_attributes=root_folder.attributes())
        root_folder.rewrite_folders()
        root_folder.rewrite_hosts_files()

    def _update_global_settings(self) -> None:
        self._update_installation_wide_global_settings()
        self._update_site_specific_global_settings()
        self._update_remote_site_specific_global_settings()

    def _update_installation_wide_global_settings(self) -> None:
        """Update the globals.mk of the local site"""
        # Load full config (with undefined settings)
        global_config = cmk.gui.watolib.global_settings.load_configuration_settings(
            full_config=True
        )
        self._update_global_config(global_config)
        cmk.gui.watolib.global_settings.save_global_settings(global_config)

    def _update_site_specific_global_settings(self) -> None:
        """Update the sitespecific.mk of the local site (which is a remote site)"""
        if not is_wato_slave_site():
            return

        global_config = cmk.gui.watolib.global_settings.load_site_global_settings()
        self._update_global_config(global_config)

        cmk.gui.watolib.global_settings.save_site_global_settings(global_config)

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
        check_variables = cmk.base.config.get_check_variables()
        failed_hosts = []

        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()

        for autocheck_file in Path(cmk.utils.paths.autochecks_dir).glob("*.mk"):
            hostname = HostName(autocheck_file.stem)
            try:
                autochecks = load_unmigrated_autocheck_entries(
                    autocheck_file,
                    check_variables,
                )
            except MKGeneralException as exc:
                msg = (
                    "%s\nIf you encounter this error during the update process "
                    "you need to replace the the variable by its actual value, e.g. "
                    "replace `my_custom_levels` by `{'levels': (23, 42)}`." % exc
                )
                if self._arguments.debug:
                    raise MKGeneralException(msg)
                self._logger.error(msg)
                failed_hosts.append(hostname)
                continue

            autochecks = [self._fix_entry(s, all_rulesets, hostname) for s in autochecks]
            cmk.base.autochecks.AutochecksStore(hostname).write(autochecks)

        if failed_hosts:
            msg = "Failed to rewrite autochecks file for hosts: %s" % ", ".join(failed_hosts)
            self._logger.error(msg)
            raise MKGeneralException(msg)

    def _rewrite_password_store(self) -> None:
        """With 2.1 the password store format changed. Ensure all sites get the new format"""
        if (
            not password_store.password_store_path().exists()
            or password_store.password_store_path().stat().st_size == 0
        ):
            return

        # First of all update the stored_passwords file
        if self._is_pre_2_1_password_store():
            passwords = self._load_pre_2_1_password_store()
            password_store.save(passwords)

        # Then load and save the setup config to update the passwords.mk
        store = PasswordStore()
        store.save(store.load_for_modification())

    def _is_pre_2_1_password_store(self) -> bool:
        return (
            int.from_bytes(
                password_store.password_store_path().read_bytes()[
                    : password_store._PasswordStoreObfuscator.VERSION_BYTE_LENGTH
                ],
                byteorder="big",
            )
            != 0
        )

    def _load_pre_2_1_password_store(self) -> dict[str, str]:
        passwords = {}
        for line in password_store.password_store_path().read_text().splitlines():
            ident, password = line.strip().split(":", 1)
            passwords[ident] = password
        return passwords

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
        self._transform_ignored_checks_to_maincheckified_list(all_rulesets)
        self._extract_disabled_snmp_sections_from_ignored_checks(all_rulesets)
        self._extract_checkmk_agent_rule_from_check_mk_config(all_rulesets)
        self._extract_checkmk_agent_rule_from_exit_spec(all_rulesets)
        self._transform_replaced_wato_rulesets(all_rulesets)
        self._transform_wato_rulesets_params(all_rulesets)
        self._transform_discovery_disabled_services(all_rulesets)
        self._validate_regexes_in_item_specs(all_rulesets)
        self._remove_removed_check_plugins_from_ignored_checks(
            all_rulesets,
            REMOVED_CHECK_PLUGIN_MAP,
        )
        self._validate_rule_values(all_rulesets)
        all_rulesets.save()

    def _transform_ignored_checks_to_maincheckified_list(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        ignored_checks_ruleset = all_rulesets.get("ignored_checks")
        if ignored_checks_ruleset.is_empty():
            return

        for _folder, _index, rule in ignored_checks_ruleset.get_rules():
            if isinstance(rule.value, str):
                rule.value = [maincheckify(rule.value)]
            else:
                rule.value = [maincheckify(s) for s in rule.value]

    def _extract_disabled_snmp_sections_from_ignored_checks(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        ignored_checks_ruleset = all_rulesets.get("ignored_checks")
        if ignored_checks_ruleset.is_empty():
            # nothing to do
            return
        if not all_rulesets.get("snmp_exclude_sections").is_empty():
            # this must be an upgrade from 2.0.0 or newer - don't mess with
            # the existing rules!
            return

        self._logger.log(VERBOSE, "Extracting excluded SNMP sections")

        all_snmp_section_names = set(s.name for s in register.iter_all_snmp_sections())
        all_check_plugin_names = set(p.name for p in register.iter_all_check_plugins())
        all_inventory_plugin_names = set(i.name for i in register.iter_all_inventory_plugins())

        snmp_exclude_sections_ruleset = cmk.gui.watolib.rulesets.Ruleset(
            "snmp_exclude_sections", ignored_checks_ruleset.tag_to_group_map
        )

        for folder, _index, rule in ignored_checks_ruleset.get_rules():
            disabled = {CheckPluginName(n) for n in rule.value}
            still_needed_sections_names = set(
                register.get_relevant_raw_sections(
                    check_plugin_names=all_check_plugin_names - disabled,
                    inventory_plugin_names=all_inventory_plugin_names,
                )
            )
            sections_to_disable = all_snmp_section_names - still_needed_sections_names
            if not sections_to_disable:
                continue

            new_rule = cmk.gui.watolib.rulesets.Rule.from_config(
                rule.folder,
                snmp_exclude_sections_ruleset,
                rule.to_config(),
            )
            new_rule.id = cmk.gui.watolib.rulesets.utils.gen_id()
            new_rule.value = {  # type: ignore[assignment]
                "sections_disabled": sorted(str(s) for s in sections_to_disable),
                "sections_enabled": [],
            }
            new_rule.rule_options.comment = (
                "%s - Checkmk: automatically converted during upgrade from rule "
                '"Disabled checks". Please review if these rules can be deleted.'
            ) % time.strftime("%Y-%m-%d %H:%M", time.localtime())
            snmp_exclude_sections_ruleset.append_rule(folder, new_rule)

        all_rulesets.set(snmp_exclude_sections_ruleset.name, snmp_exclude_sections_ruleset)

    def _extract_checkmk_agent_rule_from_check_mk_config(
        self, all_rulesets: RulesetCollection
    ) -> None:
        target_version_ruleset = all_rulesets.get("check_mk_agent_target_versions")
        if target_version_ruleset.is_empty():
            # nothing to do
            return

        agent_update_ruleset = all_rulesets.get("checkgroup_parameters:agent_update")

        for folder, _index, rule in target_version_ruleset.get_rules():

            new_rule = cmk.gui.watolib.rulesets.Rule.from_config(
                rule.folder,
                agent_update_ruleset,
                rule.to_config(),
            )
            new_rule.id = cmk.gui.watolib.rulesets.utils.gen_id()
            new_rule.value = {"agent_version": rule.value}
            new_rule.rule_options.comment = (
                "%s - Checkmk: automatically converted during upgrade from rule "
                '"Check for correct version of Checkmk agent".'
            ) % time.strftime("%Y-%m-%d %H:%M", time.localtime())

            agent_update_ruleset.append_rule(folder, new_rule)

        all_rulesets.set(agent_update_ruleset.name, agent_update_ruleset)
        all_rulesets.delete("check_mk_agent_target_versions")

    def _extract_checkmk_agent_rule_from_exit_spec(self, all_rulesets: RulesetCollection) -> None:
        exit_spec_ruleset = all_rulesets.get("check_mk_exit_status")
        if exit_spec_ruleset.is_empty():
            # nothing to do
            return

        agent_update_ruleset = all_rulesets.get("checkgroup_parameters:agent_update")

        for folder, _index, rule in exit_spec_ruleset.get_rules():

            moved_values = {
                key: rule.value.pop(key)
                for key in ("restricted_address_mismatch", "legacy_pull_mode")
                if key in rule.value
            }
            if "wrong_version" in rule.value:
                moved_values["agent_version_missmatch"] = rule.value.pop("wrong_version")
            if "wrong_version" in (overall := rule.value.get("overall", {})):
                moved_values["agent_version_missmatch"] = overall.pop("wrong_version")
            if "wrong_version" in (individual := rule.value.get("individual", {}).get("agent", {})):
                moved_values["agent_version_missmatch"] = individual.pop("wrong_version")

            if not moved_values:
                continue

            new_rule = cmk.gui.watolib.rulesets.Rule.from_config(
                rule.folder,
                agent_update_ruleset,
                rule.to_config(),
            )
            new_rule.id = cmk.gui.watolib.rulesets.utils.gen_id()
            new_rule.value = moved_values
            new_rule.rule_options.comment = (
                "%s - Checkmk: automatically converted during upgrade from rule "
                '"Status of the Checkmk services".'
            ) % time.strftime("%Y-%m-%d %H:%M", time.localtime())

            agent_update_ruleset.append_rule(folder, new_rule)

        all_rulesets.set(agent_update_ruleset.name, agent_update_ruleset)
        # TODO: do we have to do this:?
        all_rulesets.set(exit_spec_ruleset.name, exit_spec_ruleset)

    def _transform_replaced_wato_rulesets(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        deprecated_ruleset_names: Set[str] = set()
        for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
            if ruleset_name not in REMOVED_WATO_RULESETS_MAP:
                continue

            new_ruleset = all_rulesets.get(REMOVED_WATO_RULESETS_MAP[ruleset_name])

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

    def _transform_discovery_disabled_services(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        """Transform regex escaping of service descriptions

        In 1.4.0 disabled services were not quoted in the rules configuration file. Later versions
        quoted these services. Due to this the unquoted services were not found when re-enabling
        them via the GUI in version 1.6.

        Previous to Checkmk 2.0 we used re.escape() for storing service descriptions as exact match
        regexes. With 2.0 we switched to cmk.utils.regex.escape_regex_chars(), because this escapes
        less characters (like the " "), which makes the definitions more readable.

        This transformation only applies to disabled services rules created by the service
        discovery page (when enabling or disabling a single service using the "move to disabled" or
        "move to enabled" icon)
        """
        ruleset = all_rulesets.get("ignored_services")
        if not ruleset:
            return

        def _fix_up_escaped_service_pattern(pattern: str) -> HostOrServiceConditionRegex:
            if pattern == (unescaped_pattern := unescape(pattern)):
                # If there was nothing to unescape, escaping would break the pattern (e.g. '.foo').
                # This still breaks half escaped patterns (e.g. '\.foo.')
                return {"$regex": pattern}
            return cmk.gui.watolib.rulesets.service_description_to_condition(
                unescaped_pattern.rstrip("$")
            )

        for _folder, _index, rule in ruleset.get_rules():
            # We can't truly distinguish between user- and discovery generated rules.
            # We try our best to detect them, but there will be false positives.
            if not rule.is_discovery_rule():
                continue

            if isinstance(
                service_description := rule.conditions.service_description, dict
            ) and service_description.get("$nor"):
                rule.conditions.service_description = {
                    "$nor": [
                        _fix_up_escaped_service_pattern(s["$regex"])
                        for s in service_description["$nor"]
                        if isinstance(s, dict) and "$regex" in s
                    ]
                }

            elif service_description:
                rule.conditions.service_description = [
                    _fix_up_escaped_service_pattern(s["$regex"])
                    for s in service_description
                    if isinstance(s, dict) and "$regex" in s
                ]

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

    def _validate_regexes_in_item_specs(
        self,
        all_rulesets: RulesetCollection,
    ) -> None:
        def format_error(msg: str):
            return "\033[91m {}\033[00m".format(msg)

        num_errors = 0
        for ruleset in all_rulesets.get_rulesets().values():
            for folder, index, rule in ruleset.get_rules():
                if not isinstance(
                    service_description := rule.get_rule_conditions().service_description, list
                ):
                    continue
                for item in service_description:
                    if not isinstance(item, dict):
                        continue
                    regex = item.get("$regex")
                    if regex is None:
                        continue
                    try:
                        re.compile(regex)
                    except re.error as e:
                        self._logger.error(
                            format_error(
                                "ERROR: Invalid regular expression in service condition detected "
                                "(Ruleset: %s, Title: %s, Folder: %s,\nRule nr: %s, Condition: %s, "
                                "Exception: %s)"
                            ),
                            ruleset.name,
                            ruleset.title(),
                            folder.path(),
                            index + 1,
                            regex,
                            e,
                        )
                        num_errors += 1
                        continue
                    if PureWindowsPath(regex).is_absolute() and _MATCH_SINGLE_BACKSLASH.search(
                        regex
                    ):
                        self._logger.warning(
                            _format_warning(
                                "WARN: Service condition in rule looks like an absolute windows path that is not correctly escaped.\n"
                                " Use double backslash as directory separator in regex expressions, e.g.\n"
                                " 'C:\\\\Program Files\\\\'\n"
                                " (Ruleset: %s, Folder: %s, Rule nr: %s, Condition:%s)"
                            ),
                            ruleset.name,
                            folder.path(),
                            index,
                            regex,
                        )

        if num_errors:
            self._has_errors = True
            self._logger.error(
                format_error(
                    "Detected %s errors in service conditions.\n"
                    "You must correct these errors *before* starting Checkmk.\n"
                    "To do so, we recommend to open the affected rules in the GUI. Upon attempting "
                    "to save them, any problematic field will be highlighted.\n"
                    "For more information regarding errors in regular expressions see:\n"
                    "https://docs.checkmk.com/latest/en/regexes.html"
                ),
                num_errors,
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

    def _migrate_pagetype_topics_to_ids(self) -> None:
        """Change all visuals / page types to use IDs as topics

        2.0 changed the topic from a free form user localizable string to an ID
        that references the builtin and user managable "pagetype_topics".

        Try to detect builtin or existing topics topics, reference them and
        also create missing topics and refernce them.

        Persist all the user visuals and page types after modification.
        """
        topic_created_for: Set[UserId] = set()
        pagetypes.PagetypeTopics.load()
        topics = pagetypes.PagetypeTopics.instances_dict()

        # Create the topics for all page types
        topic_created_for.update(self._migrate_pagetype_topics(topics))

        # And now do the same for all visuals (views, dashboards, reports)
        topic_created_for.update(self._migrate_all_visuals_topics(topics))

        # Now persist all added topics
        for user_id in topic_created_for:
            pagetypes.PagetypeTopics.save_user_instances(user_id)

    def _migrate_pagetype_topics(self, topics: Dict) -> Set[UserId]:
        topic_created_for: Set[UserId] = set()

        for page_type_cls in pagetypes.all_page_types().values():
            if not issubclass(page_type_cls, pagetypes.PageRenderer):
                continue

            page_type_cls.load()
            modified_user_instances = set()

            # First modify all instances in memory and remember which things have changed
            for instance in page_type_cls.instances():
                owner = instance.owner()
                instance_modified, topic_created = self._transform_pre_17_topic_to_id(
                    topics, instance.internal_representation()
                )

                if instance_modified and owner:
                    modified_user_instances.add(owner)

                if topic_created and owner:
                    topic_created_for.add(owner)

            # Now persist all modified instances
            for user_id in modified_user_instances:
                page_type_cls.save_user_instances(user_id)

        return topic_created_for

    def _rewrite_visuals(self):
        """This function uses the updates in visuals.transform_old_visual which
        takes place upon visuals load. However, load forces no save, thus save
        the transformed visual in this update step. All user configs are rewriten.
        The load and transform functions are specific to each visual, saving is generic."""

        def updates(visual_type: str, all_visuals: Dict):
            with _save_user_instances(visual_type, all_visuals) as affected_user:
                # skip builtins, only users
                affected_user.update(owner for owner, _name in all_visuals if owner)

        updates("views", get_all_views())
        updates("dashboards", get_all_dashboards())

        # Reports
        try:
            import cmk.gui.cee.reporting as reporting  # pylint: disable=cmk-module-layer-violation
        except ImportError:
            reporting = None  # type: ignore[assignment]

        if reporting:
            reporting.load_reports()  # Loading does the transformation
            updates("reports", reporting.reports)

    def _migrate_all_visuals_topics(self, topics: Dict) -> Set[UserId]:
        topic_created_for: Set[UserId] = set()

        # Views
        topic_created_for.update(
            self._migrate_visuals_topics(topics, visual_type="views", all_visuals=get_all_views())
        )

        # Dashboards
        topic_created_for.update(
            self._migrate_visuals_topics(
                topics, visual_type="dashboards", all_visuals=get_all_dashboards()
            )
        )

        # Reports
        try:
            import cmk.gui.cee.reporting as reporting
        except ImportError:
            reporting = None  # type: ignore[assignment]

        if reporting:
            reporting.load_reports()
            topic_created_for.update(
                self._migrate_visuals_topics(
                    topics, visual_type="reports", all_visuals=reporting.reports
                )
            )

        return topic_created_for

    def _migrate_visuals_topics(
        self,
        topics: Dict,
        visual_type: str,
        all_visuals: Dict,
    ) -> Set[UserId]:
        topic_created_for: Set[UserId] = set()
        with _save_user_instances(visual_type, all_visuals) as affected_user:

            # First modify all instances in memory and remember which things have changed
            for (owner, _name), visual_spec in all_visuals.items():
                instance_modified, topic_created = self._transform_pre_17_topic_to_id(
                    topics, visual_spec
                )

                if instance_modified and owner:
                    affected_user.add(owner)

                if topic_created and owner:
                    topic_created_for.add(owner)

        return topic_created_for

    def _transform_pre_17_topic_to_id(
        self, topics: Dict, spec: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        topic = spec["topic"] or ""
        topic_key = (spec["owner"], topic)
        name = _id_from_title(topic)
        name_key = (spec["owner"], topic)

        topics_by_title = {v.title(): k for k, v in topics.items()}

        if ("", topic) in topics:
            # No need to transform. Found a builtin topic which has the current topic
            # as ID
            return False, False

        if ("", name) in topics:
            # Found a builtin topic matching the generated name, assume we have a match
            spec["topic"] = name
            return True, False

        if name_key in topics:
            # Found a custom topic matching the generated name, assume we have a match
            spec["topic"] = name
            return True, False

        if topic_key in topics:
            # No need to transform. Found a topic which has the current topic as ID
            return False, False

        if topic in topics_by_title and topics_by_title[topic][0] in ["", spec["owner"]]:
            # Found an existing topic which title exactly matches the current topic attribute and which
            # is either owned by the same user as the spec or builtin and accessible
            spec["topic"] = topics_by_title[topic][1]
            return True, False

        # Found no match: Create a topic for this spec and use it
        # Use same owner and visibility settings as the original
        pagetypes.PagetypeTopics.add_instance(
            (spec["owner"], name),
            pagetypes.PagetypeTopics(
                {
                    "name": name,
                    "title": topic,
                    "description": "",
                    "public": spec["public"],
                    "icon_name": "missing",
                    "sort_index": 99,
                    "owner": spec["owner"],
                }
            ),
        )

        spec["topic"] = name
        return True, True

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

    def _rewrite_bi_configuration(self) -> None:
        """Convert the bi configuration to the new (REST API compatible) format"""
        BILegacyPacksConverter(self._logger, BIManager.bi_configuration_file()).convert_config()

    def _migrate_dashlets(self) -> None:
        global_config = cmk.gui.watolib.global_settings.load_configuration_settings(
            full_config=True
        )
        filter_group = global_config.get("topology_default_filter_group", "")

        dashboards = visuals.load("dashboards", builtin_dashboards)
        with _save_user_instances("dashboards", dashboards) as affected_user:
            for (owner, _name), dashboard in dashboards.items():
                for dashlet in dashboard["dashlets"]:
                    if dashlet["type"] == "network_topology":
                        transform_topology_dashlet(dashlet, filter_group)
                        affected_user.add(owner)
                    elif dashlet["type"] in ("hoststats", "servicestats"):
                        transform_stats_dashlet(dashlet)
                        affected_user.add(owner)
                    elif dashlet["type"] in (
                        "single_timeseries",
                        "custom_graph",
                        "combined_graph",
                        "problem_graph",
                        "pnpgraph",
                    ):
                        transform_timerange_dashlet(dashlet)
                        affected_user.add(owner)

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

        save_users(users)

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

    def _migrate_pre_2_0_audit_log(self) -> None:
        old_path = Path(cmk.utils.paths.var_dir, "wato", "log", "audit.log")
        new_path = Path(cmk.utils.paths.var_dir, "wato", "log", "wato_audit.log")

        if not old_path.exists():
            self._logger.log(VERBOSE, "No audit log present. Skipping.")
            return

        if new_path.exists():
            self._logger.log(VERBOSE, "New audit log already existing. Skipping.")
            return

        store = AuditLogStore(AuditLogStore.make_path())
        store.write(list(self._read_pre_2_0_audit_log(old_path)))

        old_path.unlink()

    def _read_pre_2_0_audit_log(self, old_path: Path) -> Iterable[AuditLogStore.Entry]:
        with old_path.open(encoding="utf-8") as fp:
            for line in fp:
                splitted = line.rstrip().split(None, 4)
                if len(splitted) == 5 and splitted[0].isdigit():
                    t, linkinfo, user, action, text = splitted

                    yield AuditLogStore.Entry(
                        time=int(t),
                        object_ref=self._object_ref_from_linkinfo(linkinfo),
                        user_id=user,
                        action=action,
                        text=text,
                        diff_text=None,
                    )

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

    def _object_ref_from_linkinfo(self, linkinfo: str) -> Optional[ObjectRef]:
        if ":" not in linkinfo:
            return None

        folder_path, host_name = linkinfo.split(":", 1)
        if not host_name:
            return ObjectRef(ObjectRefType.Folder, folder_path)
        return ObjectRef(ObjectRefType.Host, host_name)

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

    def _transform_groups(self) -> None:
        group_information = cmk.gui.groups.load_group_information()

        # Add host or service group transformations here if needed
        self._transform_contact_groups(group_information.get("contact", {}))

        cmk.gui.watolib.groups.save_group_information(group_information)

    def _transform_contact_groups(
        self,
        contact_groups: Mapping[ContactgroupName, MutableMapping[str, Any]],
    ) -> None:
        # Changed since Checkmk 2.1: see Werk 12390
        # Old entries of inventory paths of multisite contact groups had the following form:
        # {
        #     "group_name_0": {
        #         "inventory_paths": "allow_all"
        #     },
        #     "group_name_1": {
        #         "inventory_paths": "forbid_all"
        #     },
        #     "group_name_2": {
        #         "inventory_paths": ("paths", [
        #             {
        #                 "path": "path.to.node_0",
        #             },
        #             {
        #                 "path": "path.to.node_1",
        #                 "attributes": [],
        #             },
        #             {
        #                 "path": "path.to.node_2",
        #                 "attributes": ["some", "keys"],
        #             },
        #         ])
        #     }
        # }
        for settings in contact_groups.values():
            inventory_paths = settings.get("inventory_paths")
            if inventory_paths and isinstance(inventory_paths, tuple):
                settings["inventory_paths"] = (
                    inventory_paths[0],
                    [
                        self._transform_inventory_path_and_keys(entry)
                        for entry in inventory_paths[1]
                    ],
                )

    def _transform_inventory_path_and_keys(self, params: Dict) -> Dict:
        if "path" not in params:
            return params

        params["visible_raw_path"] = params.pop("path")

        attributes_keys = params.pop("attributes", None)
        if attributes_keys is None:
            return params

        if attributes_keys == []:
            params["nodes"] = "nothing"
            return params

        params["attributes"] = ("choices", attributes_keys)
        params["columns"] = ("choices", attributes_keys)
        params["nodes"] = "nothing"

        return params

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

    def _renew_site_cert(self) -> None:
        try:
            cert, _priv = certs.load_cert_and_private_key(cmk.utils.paths.site_cert_file)
            if any(isinstance(e.value, x509.SubjectAlternativeName) for e in cert.extensions):
                self._logger.log(VERBOSE, "Skipping (nothing to do)")
                return
        except FileNotFoundError:
            self._logger.warning(f"No site certificate found at {cmk.utils.paths.site_cert_file}")
        except OSError as exc:
            self._logger.warning(f"Unable to load site certificate: {exc}")
            return

        root_ca_path = certs.root_cert_path(certs.cert_dir(Path(cmk.utils.paths.omd_root)))
        try:
            root_ca = certs.RootCA.load(root_ca_path)
        except OSError as exc:
            self._logger.warning(f"Unable to load root CA: {exc}")
            return

        bak = Path(f"{cmk.utils.paths.site_cert_file}.bak")
        with suppress(FileNotFoundError):
            bak.write_bytes(cmk.utils.paths.site_cert_file.read_bytes())
            self._logger.log(VERBOSE, f"Copied certificate to {bak}")

        self._logger.log(VERBOSE, "Creating new certificate...")
        root_ca.save_new_signed_cert(
            cmk.utils.paths.site_cert_file,
            cmk.utils.site.omd_site(),
            days_valid=999 * 365,
        )

    def _add_site_ca_to_trusted_cas(self) -> None:
        site_ca = (
            site_cas[-1]
            if (site_cas := raw_certificates_from_file(cmk.utils.paths.site_cert_file))
            else None
        )

        if not site_ca:
            return

        global_config = cmk.gui.watolib.global_settings.load_configuration_settings(
            full_config=True
        )
        cert_settings = global_config.setdefault(
            "trusted_certificate_authorities", {"use_system_wide_cas": True, "trusted_cas": []}
        )
        # For remotes with config sync the settings would be overwritten by activate changes. To keep the config
        # consistent exclude remotes during the update.
        if is_wato_slave_site() or site_ca in cert_settings["trusted_cas"]:
            return

        cert_settings["trusted_cas"].append(site_ca)
        cmk.gui.watolib.global_settings.save_global_settings(global_config)

    def _update_mknotifyd(self) -> None:
        """
        Update the sitespecific mknotifyd config file on central site because
        this is not handled by the global or sitespecific updates.
        The encryption key is missing on update from 2.0 to 2.1.
        """
        if is_wato_slave_site() or not has_wato_slave_sites():
            return

        sitespecific_file_path: Path = Path(
            cmk.utils.paths.default_config_dir, "mknotifyd.d", "wato", "sitespecific.mk"
        )
        if not sitespecific_file_path.exists():
            return

        mknotifyd_config: Dict[str, Any] = load_from_mk_file(
            sitespecific_file_path, "notification_spooler_config", {}
        )
        if not mknotifyd_config:
            return

        for key, value in mknotifyd_config.items():
            if key not in ["incoming", "outgoing"]:
                continue
            if key == "incoming":
                value.setdefault("encryption", "unencrypted")
            if key == "outgoing":
                for outgoing in value:
                    outgoing.setdefault("encryption", "upgradable")

        save_mk_file(sitespecific_file_path, "notification_spooler_config = %s" % mknotifyd_config)

    def _transform_influxdb_connnections(self) -> None:
        """
        Apply valuespec transforms to InfluxDB connections
        """
        if version.is_raw_edition():
            return

        # fmt: off
        from cmk.gui.cee.plugins.wato import influxdb  # type: ignore[import] # isort:skip # pylint: disable=no-name-in-module
        # fmt: on

        influx_db_connection_config = influxdb.InfluxDBConnectionConfig()
        influx_db_connection_valuespec = influxdb.ModeEditInfluxDBConnection().valuespec()
        influx_db_connection_config.save(
            {
                connection_id: influx_db_connection_valuespec.transform_value(connection_config)
                for connection_id, connection_config in influx_db_connection_config.load_for_modification().items()
            }
        )


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
