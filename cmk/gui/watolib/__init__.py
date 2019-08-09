#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""WATO LIBRARY

This component contains classes, functions and globals that are being used by
WATO. It does not contain any acutal page handlers or WATO modes. Nor complex
HTML creation. This is all contained in cmk.gui.wato."""

import abc
import ast
import base64
import cStringIO
import copy
import glob
from hashlib import sha256
import multiprocessing
import os
import pickle
import pprint
import pwd
import re
import shutil
import signal
import socket
import subprocess
import tarfile
import threading
import time
import traceback
from typing import NamedTuple, List  # pylint: disable=unused-import

import requests
import urllib3  # type: ignore
from pathlib2 import Path
import six

import cmk
import cmk.utils.daemon as daemon
import cmk.utils.paths
import cmk.utils.defines
import cmk.utils
import cmk.utils.store as store
import cmk.utils.render as render
import cmk.ec.defaults
import cmk.ec.export
import cmk.utils.regex
import cmk.utils.plugin_registry

import cmk.gui.utils
import cmk.gui.sites
import cmk.utils.tags
import cmk.gui.config as config
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.multitar as multitar
import cmk.gui.mkeventd as mkeventd
import cmk.gui.werks as werks
import cmk.gui.log as log
import cmk.gui.background_job as background_job
import cmk.gui.weblib as weblib
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML, Encoder
from cmk.gui.log import logger
from cmk.gui.exceptions import MKGeneralException, MKAuthException, MKUserError, RequestTimeout
from cmk.gui.valuespec import (
    Dictionary,
    Integer,
    HostAddress,
    ListOfStrings,
    IPNetwork,
    Checkbox,
    Transform,
    DropdownChoice,
    ListOf,
    EmailAddressUnicode,
    DualListChoice,
    UserID,
    FixedValue,
    Alternative,
    CascadingDropdown,
    TextAscii,
    TextUnicode,
    TextAreaUnicode,
    TextAsciiAutocomplete,
    ValueSpec,
    ListChoice,
    Float,
    Foldable,
    Tuple,
    Age,
    RegExp,
    MonitoredHostname,
)
# TODO: cleanup all call sites to this name
from cmk.gui.config import (
    is_wato_slave_site,
    site_choices,
)

import cmk.gui.watolib.timeperiods
import cmk.gui.watolib.git
import cmk.gui.watolib.changes
# TODO: Cleanup all except declare_host_attribute which is still neded for pre 1.6 plugin
# compatibility. For the others: Find the call sites and change to full module import
from cmk.gui.watolib.notifications import save_notification_rules
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.host_attributes import (
    get_sorted_host_attribute_topics,
    get_sorted_host_attributes_by_topic,
    declare_host_attribute,
    undeclare_host_attribute,
    host_attribute,
    collect_attributes,
    TextAttribute,
    ValueSpecAttribute,
    FixedTextAttribute,
    NagiosTextAttribute,
    EnumAttribute,
    NagiosValueSpecAttribute,
)
from cmk.gui.watolib.automations import (
    MKAutomationException,
    do_remote_automation,
    check_mk_automation,
    check_mk_local_automation,
    get_url,
    do_site_login,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainCore,
    ConfigDomainGUI,
    ConfigDomainLiveproxy,
    ConfigDomainOMD,
    ConfigDomainCACertificates,
    ConfigDomainEventConsole,
)
from cmk.gui.watolib.sites import (
    SiteManagementFactory,
    CEESiteManagement,
    LivestatusViaTCP,
    create_distributed_wato_file,
)
from cmk.gui.watolib.changes import (
    log_entry,
    log_audit,
    add_change,
    add_service_change,
)
from cmk.gui.watolib.activate_changes import (
    get_replication_paths,
    add_replication_paths,
    ActivateChanges,
    ActivateChangesManager,
    ActivateChangesSite,
    confirm_all_local_changes,
    get_pending_changes_info,
    get_number_of_pending_changes,
)
from cmk.gui.watolib.groups import (
    edit_group,
    add_group,
    delete_group,
    save_group_information,
    find_usages_of_group,
    is_alias_used,
)
from cmk.gui.watolib.rulespecs import (
    RulespecGroup,
    RulespecSubGroup,
    RulespecGroupRegistry,
    rulespec_group_registry,
    RulespecGroupManualChecks,
    register_rulegroup,
    get_rulegroup,
    Rulespec,
    register_rule,
)
from cmk.gui.watolib.rulesets import (
    RulesetCollection,
    AllRulesets,
    SingleRulesetRecursively,
    FolderRulesets,
    FilteredRulesetCollection,
    StaticChecksRulesets,
    NonStaticChecksRulesets,
    SearchedRulesets,
    Ruleset,
    Rule,
)
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    Host,
    validate_all_hosts,
    call_hook_hosts_changed,
    folder_preserving_link,
    get_folder_title_path,
    get_folder_title,
    check_wato_foldername,
    make_action_link,
)
from cmk.gui.watolib.sidebar_reload import (
    is_sidebar_reload_needed,
    need_sidebar_reload,
)
from cmk.gui.watolib.analyze_configuration import (
    ACResultNone,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    ACTestCategories,
    ACTest,
    ac_test_registry,
)
from cmk.gui.watolib.user_scripts import (
    load_user_scripts,
    load_notification_scripts,
    user_script_choices,
    user_script_title,
)
from cmk.gui.watolib.snapshots import backup_domains
from cmk.gui.watolib.automation_commands import (AutomationCommand, automation_command_registry)
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    save_site_global_settings,
    save_global_settings,
)
from cmk.gui.watolib.users import (
    get_vs_flexible_notifications,
    get_vs_user_idle_timeout,
    notification_script_choices,
    verify_password_policy,
)
from cmk.gui.watolib.utils import (
    ALL_HOSTS,
    ALL_SERVICES,
    NEGATE,
    wato_root_dir,
    multisite_dir,
    rename_host_in_list,
    convert_cgroups_from_tuple,
    host_attribute_matches,
    default_site,
    format_config_value,
    liveproxyd_config_dir,
    mk_repr,
    mk_eval,
    has_agent_bakery,
    site_neutral_path,
)
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed

from cmk.gui.plugins.watolib.utils import (
    ConfigDomain,
    config_domain_registry,
    config_variable_registry,
    wato_fileheader,
    SampleConfigGenerator,
    sample_config_generator_registry,
)

import cmk.gui.plugins.watolib

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.watolib

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_watolib_plugins():
    cmk.gui.utils.load_web_plugins("watolib", globals())


# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock=False):
    if os.path.exists(ConfigDomainCACertificates.trusted_cas_file) and\
        not _need_to_create_sample_config():
        return

    def init():
        if not os.path.exists(ConfigDomainCACertificates.trusted_cas_file):
            ConfigDomainCACertificates().activate()
        _create_sample_config()

    if with_wato_lock:
        with store.lock_checkmk_configuration():
            init()
    else:
        init()


def _need_to_create_sample_config():
    if os.path.exists(multisite_dir() + "tags.mk") \
        or os.path.exists(wato_root_dir() + "rules.mk") \
        or os.path.exists(wato_root_dir() + "groups.mk") \
        or os.path.exists(wato_root_dir() + "notifications.mk") \
        or os.path.exists(wato_root_dir() + "global.mk"):
        return False
    return True


def _create_sample_config():
    """Create a very basic sample configuration

    But only if none of the files that we will create already exists. That is
    e.g. the case after an update from an older version where no sample config
    had been created.
    """
    if not _need_to_create_sample_config():
        return

    logger.debug("Start creating the sample config")
    for generator in sample_config_generator_registry.get_generators():
        try:
            logger.debug("Starting [%s]", generator.ident())
            generator.generate()
            logger.debug("Finished [%s]", generator.ident())
        except Exception:
            logger.exception("Exception in sample config generator [%s]", generator.ident())

    logger.debug("Finished creating the sample config")


@sample_config_generator_registry.register
class ConfigGeneratorBasicWATOConfig(SampleConfigGenerator):
    @classmethod
    def ident(cls):
        return "basic_wato_config"

    @classmethod
    def sort_index(cls):
        return 10

    def generate(self):
        save_global_settings({
            "use_new_descriptions_for": [
                "df",
                "df_netapp",
                "df_netapp32",
                "esx_vsphere_datastores",
                "hr_fs",
                "vms_diskstat.df",
                "zfsget",
                "ps",
                "ps.perf",
                "wmic_process",
                "services",
                "logwatch",
                "logwatch.groups",
                "cmk-inventory",
                "hyperv_vms",
                "ibm_svc_mdiskgrp",
                "ibm_svc_system",
                "ibm_svc_systemstats.diskio",
                "ibm_svc_systemstats.iops",
                "ibm_svc_systemstats.disk_latency",
                "ibm_svc_systemstats.cache",
                "casa_cpu_temp",
                "cmciii.temp",
                "cmciii.psm_current",
                "cmciii_lcp_airin",
                "cmciii_lcp_airout",
                "cmciii_lcp_water",
                "etherbox.temp",
                "liebert_bat_temp",
                "nvidia.temp",
                "ups_bat_temp",
                "innovaphone_temp",
                "enterasys_temp",
                "raritan_emx",
                "raritan_pdu_inlet",
                "mknotifyd",
                "mknotifyd.connection",
                "postfix_mailq",
                "nullmailer_mailq",
                "barracuda_mailqueues",
                "qmail_stats",
                "http",
                "mssql_backup",
                "mssql_counters.cache_hits",
                "mssql_counters.transactions",
                "mssql_counters.locks",
                "mssql_counters.sqlstats",
                "mssql_counters.pageactivity",
                "mssql_counters.locks_per_batch",
                "mssql_counters.file_sizes",
                "mssql_databases",
                "mssql_datafiles",
                "mssql_tablespaces",
                "mssql_transactionlogs",
                "mssql_versions",
            ],
            "enable_rulebased_notifications": True,
            "ui_theme": "facelift",
            "lock_on_logon_failures": 10,
        })

        # A contact group for all hosts and services
        groups = {
            "contact": {
                'all': {
                    'alias': u'Everything'
                }
            },
        }
        save_group_information(groups)

        self._initialize_tag_config()

        # Rules that match the upper host tag definition
        ruleset_config = {
            # Make the tag 'offline' remove hosts from the monitoring
            'only_hosts': [{
                'condition': {
                    'host_tags': {
                        'criticality': {
                            '$ne': 'offline'
                        }
                    }
                },
                'value': True,
                'options': {
                    'description': u'Do not monitor hosts with the tag "offline"'
                },
            },],

            # Rule for WAN hosts with adapted PING levels
            'ping_levels': [{
                'condition': {
                    'host_tags': {
                        'networking': 'wan',
                    }
                },
                'value': {
                    'loss': (80.0, 100.0),
                    'packets': 6,
                    'timeout': 20,
                    'rta': (1500.0, 3000.0)
                },
                'options': {
                    'description': u'Allow longer round trip times when pinging WAN hosts'
                },
            },],

            # All hosts should use SNMP v2c if not specially tagged
            'bulkwalk_hosts': [{
                'condition': {
                    'host_tags': {
                        'snmp': 'snmp',
                        'snmp_ds': {
                            '$ne': 'snmp-v1'
                        },
                    },
                },
                'value': True,
                'options': {
                    'description': u'Hosts with the tag "snmp-v1" must not use bulkwalk'
                },
            },],

            # Put all hosts and the contact group 'all'
            'host_contactgroups': [{
                'condition': {},
                'value': 'all',
                'options': {
                    'description': u'Put all hosts into the contact group "all"'
                },
            },],

            # Interval for HW/SW-Inventory check
            'extra_service_conf': {
                'check_interval': [{
                    'condition': {
                        'service_description': [{
                            '$regex': 'Check_MK HW/SW Inventory$'
                        }]
                    },
                    'value': 1440,
                    'options': {
                        'description': u'Restrict HW/SW-Inventory to once a day'
                    },
                },],
            },

            # Disable unreachable notifications by default
            'extra_host_conf': {
                'notification_options': [{
                    'condition': {},
                    'value': 'd,r,f,s'
                },],
            },

            # Periodic service discovery
            'periodic_discovery': [{
                'condition': {},
                'value': {
                    'severity_unmonitored': 1,
                    'severity_vanished': 0,
                    'check_interval': 120.0,
                    'inventory_check_do_scan': True
                },
                'options': {
                    'description': u'Perform every two hours a service discovery'
                },
            },],
        }

        rulesets = FolderRulesets(Folder.root_folder())
        rulesets.load()
        rulesets.from_config(Folder.root_folder(), ruleset_config)
        rulesets.save()

        notification_rules = [
            {
                'allow_disable': True,
                'contact_all': False,
                'contact_all_with_email': False,
                'contact_object': True,
                'description': 'Notify all contacts of a host/service via HTML email',
                'disabled': False,
                'notify_plugin': ('mail', {}),
            },
        ]
        save_notification_rules(notification_rules)

    def _initialize_tag_config(self):
        tag_config = cmk.utils.tags.TagConfig()
        tag_config.parse_config(cmk.utils.tags.sample_tag_config())
        TagConfigFile().save(tag_config.get_dict_format())
        # Make sure the host tag attributes are immediately declared!
        config.tags = tag_config


@sample_config_generator_registry.register
class ConfigGeneratorAcknowledgeInitialWerks(SampleConfigGenerator):
    """This is not really the correct place for such kind of action, but the best place we could
    find to execute it only for new created sites."""
    @classmethod
    def ident(cls):
        return "acknowledge_initial_werks"

    @classmethod
    def sort_index(cls):
        return 40

    def generate(self):
        werks.acknowledge_all_werks(check_permission=False)


@sample_config_generator_registry.register
class ConfigGeneratorAutomationUser(SampleConfigGenerator):
    """Create the default Checkmk "automation" user"""
    @classmethod
    def ident(cls):
        return "create_automation_user"

    @classmethod
    def sort_index(cls):
        return 60

    def generate(self):
        userdb.create_cmk_automation_user()
