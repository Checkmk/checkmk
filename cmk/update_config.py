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

import re
from pathlib import Path
import errno
from typing import List, Tuple, Any, Dict, Set, Optional
import argparse
import logging
import copy
import subprocess
import time
import ast
import gzip
import multiprocessing

from werkzeug.test import create_environ

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
import cmk.base.autochecks  # pylint: disable=cmk-module-layer-violation
import cmk.base.config  # pylint: disable=cmk-module-layer-violation
import cmk.base.check_api  # pylint: disable=cmk-module-layer-violation
from cmk.base.check_utils import Service  # pylint: disable=cmk-module-layer-violation
from cmk.base.api.agent_based import register  # pylint: disable=cmk-module-layer-violation

import cmk.utils.log as log
from cmk.gui.display_options import DisplayOptions  # pylint: disable=cmk-module-layer-violation
from cmk.utils.regex import unescape
from cmk.utils.log import VERBOSE
import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException
import cmk.utils.paths
import cmk.utils
from cmk.utils.check_utils import maincheckify
from cmk.utils.type_defs import CheckPluginName, UserId
from cmk.utils.bi.bi_legacy_config_converter import BILegacyPacksConverter
from cmk.gui.bi import BIManager  # pylint: disable=cmk-module-layer-violation

import cmk.gui.pagetypes as pagetypes  # pylint: disable=cmk-module-layer-violation
import cmk.gui.visuals as visuals  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.views.utils import get_all_views  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.dashboard.utils import builtin_dashboards, get_all_dashboards, transform_topology_dashlet  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.userdb.utils import save_connection_config, load_connection_config, USER_SCHEME_SERIAL  # pylint: disable=cmk-module-layer-violation
from cmk.gui.plugins.watolib.utils import filter_unknown_settings  # pylint: disable=cmk-module-layer-violation
from cmk.gui.watolib.changes import AuditLogStore, ObjectRef, ObjectRefType  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.tags  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.hosts_and_folders  # pylint: disable=cmk-module-layer-violation
import cmk.gui.watolib.rulesets  # pylint: disable=cmk-module-layer-violation
import cmk.gui.modules  # pylint: disable=cmk-module-layer-violation
import cmk.gui.config  # pylint: disable=cmk-module-layer-violation
from cmk.gui.userdb import load_users, save_users  # pylint: disable=cmk-module-layer-violation
import cmk.gui.utils  # pylint: disable=cmk-module-layer-violation
import cmk.gui.htmllib as htmllib  # pylint: disable=cmk-module-layer-violation
from cmk.gui.globals import AppContext, RequestContext  # pylint: disable=cmk-module-layer-violation
from cmk.gui.http import Request  # pylint: disable=cmk-module-layer-violation

import cmk.update_rrd_fs_names  # pylint: disable=cmk-module-layer-violation  # TODO: this should be fine

# mapping removed check plugins to their replacement:
REMOVED_CHECK_PLUGIN_MAP = {
    CheckPluginName("snmp_uptime"): CheckPluginName("uptime"),
    CheckPluginName("ps_perf"): CheckPluginName("ps"),
    CheckPluginName("aix_memory"): CheckPluginName("mem_used"),
    CheckPluginName("docker_container_mem"): CheckPluginName("mem_used"),
    CheckPluginName("hr_mem"): CheckPluginName("mem_used"),
    CheckPluginName("solaris_mem"): CheckPluginName("mem_used"),
    CheckPluginName("statgrab_mem"): CheckPluginName("mem_used"),
    CheckPluginName("cisco_mem_asa64"): CheckPluginName("cisco_mem_asa"),
    CheckPluginName("if64adm"): CheckPluginName("if64"),
    CheckPluginName("winperf_tcp_conn"): CheckPluginName("tcp_conn_stats"),
    CheckPluginName("datapower_tcp"): CheckPluginName("tcp_conn_stats"),
}

# List[(old_config_name, new_config_name, replacement_dict{old: new})]
REMOVED_GLOBALS_MAP: List[Tuple[str, str, Dict]] = [
    ("use_inline_snmp", "snmp_backend_default", {
        True: "inline",
        False: "classic"
    }),
    ("config", "notification_spooler_config", {}),
]

REMOVED_WATO_RULESETS_MAP = {
    "non_inline_snmp_hosts": "snmp_backend_hosts",
}


# TODO: Better make our application available?
class DummyApplication:
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response


class UpdateConfig:
    def __init__(self, logger: logging.Logger, arguments: argparse.Namespace) -> None:
        super(UpdateConfig, self).__init__()
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

    def run(self):

        self._logger.log(VERBOSE, "Initializing application...")
        environ = dict(create_environ(), REQUEST_URI='')

        this_html = htmllib.html(Request(environ))
        # Currently the htmllib.html constructor enables the timeout by default. This side effect
        # should really be cleaned up.
        this_html.disable_request_timeout()

        with AppContext(DummyApplication(environ,
                                         None)), RequestContext(this_html,
                                                                display_options=DisplayOptions(),
                                                                prefix_logs_with_url=False):
            self._initialize_gui_environment()
            self._initialize_base_environment()

            self._logger.log(VERBOSE, "Updating Checkmk configuration...")
            for step_func, title in self._steps():
                self._logger.log(VERBOSE, " + %s..." % title)
                try:
                    step_func()
                except Exception:
                    self._logger.error(" + \"%s\" failed" % title, exc_info=True)
                    if self._arguments.debug:
                        raise

        self._logger.log(VERBOSE, "Done")

    def _steps(self):
        return [
            (self._migrate_topology_dashlet, "Migrate deprecated network topology dashlet"),
            (self._rewrite_removed_global_settings, "Rewriting removed global settings"),
            (self._rewrite_wato_tag_config, "Rewriting WATO tags"),
            (self._rewrite_wato_host_and_folder_config, "Rewriting WATO hosts and folders"),
            (self._rewrite_wato_rulesets, "Rewriting WATO rulesets"),
            (self._rewrite_autochecks, "Rewriting autochecks"),
            (self._cleanup_version_specific_caches, "Cleanup version specific caches"),
            (self._update_fs_used_name, "Migrating fs_used name"),
            (self._migrate_pagetype_topics_to_ids, "Migrate pagetype topics"),
            (self._add_missing_type_to_ldap_connections, "Migrate LDAP connections"),
            (self._rewrite_bi_configuration, "Rewrite BI Configuration"),
            (self._set_user_scheme_serial, "Set version specific user attributes"),
            (self._rewrite_py2_inventory_data, "Rewriting inventory data"),
            (self._migrate_pre_2_0_audit_log, "Migrate audit log"),
        ]

    def _initialize_base_environment(self):
        # Failing to load the config here will result in the loss of *all*
        # services due to an exception thrown by cmk.base.config.service_description
        # in _parse_autocheck_entry of cmk.base.autochecks.
        cmk.base.config.load()
        cmk.base.config.load_all_agent_based_plugins(cmk.base.check_api.get_check_api_context)

    # FS_USED UPDATE DELETE THIS FOR CMK 1.8, THIS ONLY migrates 1.6->2.0
    def _update_fs_used_name(self):
        check_df_includes_use_new_metric()
        cmk.update_rrd_fs_names.update()

    def _rewrite_wato_tag_config(self):
        tag_config_file = cmk.gui.watolib.tags.TagConfigFile()
        tag_config = cmk.utils.tags.TagConfig()
        tag_config.parse_config(tag_config_file.load_for_reading())
        tag_config_file.save(tag_config.get_dict_format())

    def _rewrite_wato_host_and_folder_config(self):
        root_folder = cmk.gui.watolib.hosts_and_folders.Folder.root_folder()
        root_folder.save()
        root_folder.rewrite_hosts_files()

    def _rewrite_removed_global_settings(self):
        # Load full config (with undefined settings)
        global_config = cmk.gui.watolib.global_settings.load_configuration_settings(
            full_config=True)
        # Replace old settings with new ones
        for old_config_name, new_config_name, replacement in REMOVED_GLOBALS_MAP:
            if old_config_name in global_config:
                self._logger.log(VERBOSE,
                                 "Replacing %s with %s" % (old_config_name, new_config_name))
                old_value = global_config[old_config_name]
                if replacement:
                    global_config.setdefault(new_config_name, replacement[old_value])
                else:
                    global_config.setdefault(new_config_name, old_value)

                del global_config[old_config_name]

        # Delete unused settings
        global_config = filter_unknown_settings(global_config)

        # Write updated settings
        cmk.gui.watolib.global_settings.save_global_settings(global_config)

    def _rewrite_autochecks(self):
        check_variables = cmk.base.config.get_check_variables()
        failed_hosts: List[str] = []

        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()

        for autocheck_file in Path(cmk.utils.paths.autochecks_dir).glob("*.mk"):
            hostname = autocheck_file.stem
            try:
                autochecks = cmk.base.autochecks.parse_autochecks_file(
                    hostname,
                    cmk.base.config.service_description,
                    check_variables,
                )
            except MKGeneralException as exc:
                msg = ("%s\nIf you encounter this error during the update process "
                       "you need to replace the the variable by its actual value, e.g. "
                       "replace `my_custom_levels` by `{'levels': (23, 42)}`." % exc)
                if self._arguments.debug:
                    raise MKGeneralException(msg)
                self._logger.error(msg)
                failed_hosts.append(hostname)
                continue

            autochecks = [self._fix_service(s, all_rulesets, hostname) for s in autochecks]
            cmk.base.autochecks.save_autochecks_file(hostname, autochecks)

        if failed_hosts:
            msg = "Failed to rewrite autochecks file for hosts: %s" % ", ".join(failed_hosts)
            self._logger.error(msg)
            raise MKGeneralException(msg)

    def _transformed_params(
        self,
        plugin_name: CheckPluginName,
        params: Any,
        all_rulesets: cmk.gui.watolib.rulesets.AllRulesets,
        hostname: str,
    ) -> Any:
        check_plugin = register.get_check_plugin(plugin_name)
        if check_plugin is None:
            return None

        ruleset_name = "checkgroup_parameters:%s" % check_plugin.check_ruleset_name
        if ruleset_name not in all_rulesets.get_rulesets():
            return None

        debug_info = "host=%r, plugin=%r, ruleset=%r, params=%r" % (
            hostname, str(plugin_name), str(check_plugin.check_ruleset_name), params)

        try:
            ruleset = all_rulesets.get_rulesets()[ruleset_name]

            # TODO: in order to keep the original input parameters and to identify misbehaving
            #       transform_values() implementations we check the passed values for modifications
            #       In that case we have to fix that transform_values() before using it
            #       This hack chould vanish as soon as we know transform_values() works as expected
            param_copy = copy.deepcopy(params)
            new_params = ruleset.valuespec().transform_value(param_copy) if params else {}
            if not param_copy == params:
                self._logger.warning("transform_value() for ruleset '%s' altered input" %
                                     check_plugin.check_ruleset_name)

            assert new_params or not params, "non-empty params vanished"
            assert not isinstance(params, dict) or isinstance(
                new_params, dict), ("transformed params down-graded from dict: %r" % new_params)

            # TODO: in case of known exceptions we don't want the transformed values be combined
            #       with old keys. As soon as we can remove the workaround below we should not
            #       handle any ruleset differently
            if str(check_plugin.check_ruleset_name) in {"if"}:
                return new_params

            # TODO: some transform_value() implementations (e.g. 'ps') return parameter with
            #       missing keys - so for safety-reasons we keep keys that don't exist in the
            #       transformed values
            #       On the flipside this can lead to problems with the check itself and should
            #       be vanished as soon as we can be sure no keys are deleted accidentally
            return {**params, **new_params} if isinstance(params, dict) else new_params

        except Exception as exc:
            msg = ("Transform failed: %s, error=%r" % (debug_info, exc))
            if self._arguments.debug:
                raise RuntimeError(msg) from exc
            self._logger.error(msg)

        return None

    def _fix_service(
        self,
        service: Service,
        all_rulesets: cmk.gui.watolib.rulesets.AllRulesets,
        hostname: str,
    ) -> Service:
        """Change names of removed plugins to the new ones and transform parameters"""
        new_plugin_name = REMOVED_CHECK_PLUGIN_MAP.get(service.check_plugin_name)
        new_params = self._transformed_params(
            new_plugin_name or service.check_plugin_name,
            service.parameters,
            all_rulesets,
            hostname,
        )

        if new_plugin_name is None and new_params is None:
            # don't create a new service if nothing has changed
            return service

        return Service(
            check_plugin_name=new_plugin_name or service.check_plugin_name,
            item=service.item,
            description=service.description,
            parameters=new_params or service.parameters,
            service_labels=service.service_labels,
        )

    def _rewrite_wato_rulesets(self):
        all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
        all_rulesets.load()
        self._transform_ignored_checks_to_maincheckified_list(all_rulesets)
        self._extract_disabled_snmp_sections_from_ignored_checks(all_rulesets)
        self._transform_replaced_wato_rulesets(all_rulesets)
        self._transform_wato_rulesets_params(all_rulesets)
        self._transform_discovery_disabled_services(all_rulesets)
        all_rulesets.save()

    def _transform_ignored_checks_to_maincheckified_list(self, all_rulesets):
        ignored_checks_ruleset = all_rulesets.get("ignored_checks")
        if ignored_checks_ruleset.is_empty():
            return

        for _folder, _index, rule in ignored_checks_ruleset.get_rules():
            if isinstance(rule.value, str):
                rule.value = [maincheckify(rule.value)]
            else:
                rule.value = [maincheckify(s) for s in rule.value]

    def _extract_disabled_snmp_sections_from_ignored_checks(self, all_rulesets):
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
            "snmp_exclude_sections", ignored_checks_ruleset.tag_to_group_map)

        for folder, _index, rule in ignored_checks_ruleset.get_rules():
            disabled = {CheckPluginName(n) for n in rule.value}
            still_needed_sections_names = set(
                register.get_relevant_raw_sections(
                    check_plugin_names=all_check_plugin_names - disabled,
                    inventory_plugin_names=all_inventory_plugin_names,
                ))
            sections_to_disable = all_snmp_section_names - still_needed_sections_names
            if not sections_to_disable:
                continue

            new_rule = cmk.gui.watolib.rulesets.Rule(rule.folder, snmp_exclude_sections_ruleset)
            new_rule.from_config(rule.to_config())
            new_rule.id = cmk.gui.watolib.rulesets.utils.gen_id()
            new_rule.value = {  # type: ignore[assignment]
                'sections_disabled': sorted(str(s) for s in sections_to_disable),
                'sections_enabled': [],
            }
            new_rule.rule_options["comment"] = (
                '%s - Checkmk: automatically converted during upgrade from rule '
                '"Disabled checks". Please review if these rules can be deleted.') % time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime())
            snmp_exclude_sections_ruleset.append_rule(folder, new_rule)

        all_rulesets.set(snmp_exclude_sections_ruleset.name, snmp_exclude_sections_ruleset)

    def _transform_replaced_wato_rulesets(self, all_rulesets):
        replacements: Dict[str, cmk.gui.watolib.rulesets.Ruleset] = {}
        for ruleset_name in all_rulesets.get_rulesets():
            if ruleset_name not in REMOVED_WATO_RULESETS_MAP:
                continue
            new_ruleset = all_rulesets.get(ruleset_name).clone()
            new_ruleset.set_name(REMOVED_WATO_RULESETS_MAP[ruleset_name])
            if not new_ruleset.is_empty():
                self._logger.log(VERBOSE, "Found deprecated ruleset: %s" % ruleset_name)
                replacements.setdefault(ruleset_name, new_ruleset)

        for old_ruleset_name, ruleset in replacements.items():
            self._logger.log(VERBOSE,
                             "Replacing ruleset %s with %s" % (old_ruleset_name, ruleset.name))
            all_rulesets.set(ruleset.name, ruleset)
            all_rulesets.delete(old_ruleset_name)

    def _transform_wato_rulesets_params(self, all_rulesets):
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
                        "Rule: %d, Value: %s: %s", ruleset.name, folder.path(), folder_index,
                        rule.value, e)
                    num_errors += 1

        if num_errors:
            raise MKGeneralException("Failed to transform %d rule values" % num_errors)

    def _transform_discovery_disabled_services(self, all_rulesets):
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

        for _folder, _index, rule in ruleset.get_rules():
            if not rule.is_discovery_rule():
                continue

            rule.conditions.service_description = [
                cmk.gui.watolib.rulesets.service_description_to_condition(
                    unescape(s["$regex"].rstrip("$")))
                for s in rule.conditions.service_description
                if "$regex" in s
            ]

    def _initialize_gui_environment(self):
        self._logger.log(VERBOSE, "Loading GUI plugins...")
        cmk.gui.modules.load_all_plugins()
        failed_plugins = cmk.gui.utils.get_failed_plugins()

        if failed_plugins:
            self._logger.error("")
            self._logger.error("ERROR: Failed to load some GUI plugins. You will either have \n"
                               "       to remove or update them to be compatible with this \n"
                               "       Checkmk version.")
            self._logger.error("")

        # TODO: We are about to rewrite parts of the config. Would be better to be executable without
        # loading the configuration first (because the load_config() may miss some conversion logic
        # which is only known to cmk.update_config in the future).
        cmk.gui.config.load_config()
        cmk.gui.config.set_super_user()

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

    def _migrate_pagetype_topics_to_ids(self):
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

    def _migrate_pagetype_topics(self, topics: Dict):
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
                    topics, instance.internal_representation())

                if instance_modified and owner:
                    modified_user_instances.add(owner)

                if topic_created and owner:
                    topic_created_for.add(owner)

            # Now persist all modified instances
            for user_id in modified_user_instances:
                page_type_cls.save_user_instances(user_id)

        return topic_created_for

    def _migrate_all_visuals_topics(self, topics: Dict):
        topic_created_for: Set[UserId] = set()

        # Views
        topic_created_for.update(
            self._migrate_visuals_topics(topics, visual_type="views", all_visuals=get_all_views()))

        # Dashboards
        topic_created_for.update(
            self._migrate_visuals_topics(topics,
                                         visual_type="dashboards",
                                         all_visuals=get_all_dashboards()))

        # Reports
        try:
            import cmk.gui.cee.reporting as reporting  # pylint: disable=cmk-module-layer-violation
        except ImportError:
            reporting = None  # type: ignore[assignment]

        if reporting:
            reporting.load_reports()
            topic_created_for.update(
                self._migrate_visuals_topics(topics,
                                             visual_type="reports",
                                             all_visuals=reporting.reports))

        return topic_created_for

    def _migrate_visuals_topics(self, topics, visual_type: str, all_visuals: Dict) -> Set[UserId]:
        topic_created_for: Set[UserId] = set()
        modified_user_instances: Set[UserId] = set()

        # First modify all instances in memory and remember which things have changed
        for (owner, _name), visual_spec in all_visuals.items():
            instance_modified, topic_created = self._transform_pre_17_topic_to_id(
                topics, visual_spec)

            if instance_modified and owner:
                modified_user_instances.add(owner)

            if topic_created and owner:
                topic_created_for.add(owner)

        # Now persist all modified instances
        for user_id in modified_user_instances:
            visuals.save(visual_type, all_visuals, user_id)

        return topic_created_for

    def _transform_pre_17_topic_to_id(self, topics: Dict, spec: Dict[str,
                                                                     Any]) -> Tuple[bool, bool]:
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
            pagetypes.PagetypeTopics({
                "name": name,
                "title": topic,
                "description": "",
                "public": spec["public"],
                "icon_name": "missing",
                "sort_index": 99,
                "owner": spec["owner"],
            }),
        )

        spec["topic"] = name
        return True, True

    def _add_missing_type_to_ldap_connections(self):
        """Each user connections needs to declare it's connection type.

        This is done using the "type" attribute. Previous versions did not always set this
        attribute, which is corrected with this update method."""
        connections = load_connection_config()
        if not connections:
            return

        for connection in connections:
            connection.setdefault("type", "ldap")
        save_connection_config(connections)

    def _rewrite_bi_configuration(self):
        """Convert the bi configuration to the new (REST API compatible) format"""
        BILegacyPacksConverter(BIManager.bi_configuration_file()).convert_config()

    def _migrate_topology_dashlet(self):
        global_config = cmk.gui.watolib.global_settings.load_configuration_settings(
            full_config=True)
        filter_group = global_config.get("topology_default_filter_group", "")

        dashboards = visuals.load("dashboards", builtin_dashboards)
        modified_user_instances: Set[UserId] = set()
        for (owner, _name), dashboard in dashboards.items():
            for dashlet in dashboard["dashlets"]:
                if dashlet["type"] == "network_topology":
                    transform_topology_dashlet(dashlet, filter_group)
                    modified_user_instances.add(owner)

        for user_id in modified_user_instances:
            visuals.save("dashboards", dashboards, user_id)

    def _set_user_scheme_serial(self):
        """Set attribute to detect with what cmk version the user was created.
        We start that with 2.0"""
        users = load_users(lock=True)
        for user_id in users:
            # pre 2.0 user
            if users[user_id].get("user_scheme_serial") is None:
                _set_show_mode(users, user_id)
            # here you could set attributes based on the current scheme

            users[user_id]["user_scheme_serial"] = USER_SCHEME_SERIAL
        save_users(users)

    def _rewrite_py2_inventory_data(self):
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
                    f for f in dirpath.iterdir()
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
                with open(filepath, 'rb') as f_in, gzip.open(str(filepath) + '.gz', 'wb') as f_out:
                    f_out.writelines(f_in)

        if returncode == 0:
            self._create_donefile(done_file)

    def _create_donefile(self, done_file: Path):
        self._logger.log(VERBOSE, "Creating file %r" % str(done_file))
        done_file.parent.mkdir(parents=True, exist_ok=True)
        done_file.touch(exist_ok=True)

    def _fix_with_2to3(self, files: List[str]) -> int:
        self._logger.log(VERBOSE, "Try to fix corrupt files with 2to3")
        cmd = [
            '2to3',
            '--write',
            '--nobackups',
        ] + files

        self._logger.log(VERBOSE, "Executing: %s", subprocess.list2cmdline(cmd))
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
        output = p.communicate()[0]
        if p.returncode != 0:
            self._logger.error("Failed to run 2to3 (Exit code: %d): %s", p.returncode, output)
        self._logger.log(VERBOSE, "Finished.")
        return p.returncode

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

    def _find_files_recursively(self, files: List[Path], path: Path):
        for f in path.iterdir():
            if f.is_file():
                if not f.name.endswith(".gz") and not f.name.startswith("."):
                    files.append(f)
            elif f.is_dir():
                self._find_files_recursively(files, f)

    def _migrate_pre_2_0_audit_log(self):
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

    def _read_pre_2_0_audit_log(self, old_path: Path):
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

    def _object_ref_from_linkinfo(self, linkinfo: str) -> Optional[ObjectRef]:
        if ':' not in linkinfo:
            return None

        folder_path, host_name = linkinfo.split(':', 1)
        if not host_name:
            return ObjectRef(ObjectRefType.Folder, folder_path)
        return ObjectRef(ObjectRefType.Host, host_name)


def _set_show_mode(users, user_id):
    """Set show_mode for existing user to 'default to show more' on upgrade to
    2.0"""
    users[user_id]["show_mode"] = "default_show_more"
    return users


def _id_from_title(title):
    return re.sub("[^-a-zA-Z0-9_]+", "", title.lower().replace(" ", "_"))


def main(args: List[str]) -> int:
    arguments = parse_arguments(args)
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))
    logger = logging.getLogger("cmk.update_config")
    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    try:
        UpdateConfig(logger, arguments).run()
    except Exception:
        if arguments.debug:
            raise
        logger.exception("ERROR: Please repair this and run \"cmk-update-config -v\" "
                         "BEFORE starting the site again.")
        return 1
    return 0


def parse_arguments(args: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--debug', action='store_true', help='Debug mode: raise Python exceptions')
    p.add_argument('-v',
                   '--verbose',
                   action='count',
                   default=0,
                   help='Verbose mode (use multiple times for more output)')

    return p.parse_args(args)


# RRD migration cleaups


def check_df_includes_use_new_metric():
    "Check that df.include files can return fs_used metric name"
    df_file = cmk.utils.paths.local_checks_dir / 'df.include'
    if df_file.exists():
        with df_file.open('r') as fid:
            r = fid.read()
            mat = re.search('fs_used', r, re.M)
            if not mat:
                msg = ('source: %s\n Returns the wrong perfdata\n' % df_file +
                       'Checkmk 2.0 requires Filesystem check plugins to deliver '
                       '"Used filesystem space" perfdata under the metric name fs_used. '
                       'Your local extension pluging seems to be using the old convention '
                       'of mountpoints as the metric name. Please update your include file '
                       'to match our reference implementation.')
                raise RuntimeError(msg)
