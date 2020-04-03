#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO LIBRARY

This component contains classes, functions and globals that are being used by
WATO. It does not contain any acutal page handlers or WATO modes. Nor complex
HTML creation. This is all contained in cmk.gui.wato."""

# NOTE: flake8 has no way to ignore just e.g. F401 for the whole file! :-P
# flake8: noqa
# pylint: disable=unused-import

import sys
import abc
import ast
import base64
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
import urllib3  # type: ignore[import]
import six

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import cmk.utils.version as cmk_version
import cmk.utils.daemon as daemon
import cmk.utils.paths
import cmk.utils.defines
import cmk.utils
import cmk.utils.store as store
import cmk.utils.render as render
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
from cmk.gui.htmllib import HTML
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
    EmailAddress,
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
import cmk.gui.watolib.auth_php
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
    CREFolder,
    Folder,
    CREHost,
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
    ACResult,
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
if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_domain_registry,
    config_variable_registry,
    wato_fileheader,
    SampleConfigGenerator,
    sample_config_generator_registry,
)

import cmk.gui.plugins.watolib

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.watolib  # pylint: disable=no-name-in-module

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
        save_global_settings(self._initial_global_settings())

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

            # Docker container specific host check commands
            'host_check_commands': [{
                'condition': {
                    'host_labels': {
                        u'cmk/docker_object': u'container'
                    }
                },
                'value': ('service', u'Docker container status'),
                'options': {
                    'description': u'Make all docker container host states base on the "Docker container status" service',
                },
            },],

            # Enable HW/SW inventory + status data inventory for docker containers and Check-MK servers by default to
            # simplify the setup procedure for them
            'active_checks': {
                'cmk_inv': [
                    {
                        'condition': {
                            'host_labels': {
                                u'cmk/docker_object': u'node',
                            }
                        },
                        'value': {
                            'status_data_inventory': True
                        },
                    },
                    {
                        'condition': {
                            'host_labels': {
                                u'cmk/check_mk_server': u'yes',
                            }
                        },
                        'value': {
                            'status_data_inventory': True
                        },
                    },
                ]
            },

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

            # Include monitoring of checkmk's tmpfs
            'inventory_df_rules': [{
                'condition': {
                    'host_labels': {
                        u'cmk/check_mk_server': u'yes',
                    },
                },
                'value': {
                    'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                    'never_ignore_mountpoints': [u'~.*/omd/sites/[^/]+/tmp$']
                }
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

    def _initial_global_settings(self):
        settings = {
            "use_new_descriptions_for": [
                "aix_memory",
                "barracuda_mailqueues",
                "brocade_sys.mem",
                "casa_cpu_temp",
                "cisco_mem",
                "cisco_mem_asa",
                "cisco_mem_asa64",
                "cmciii.psm_current",
                "cmciii.temp",
                "cmciii_lcp_airin",
                "cmciii_lcp_airout",
                "cmciii_lcp_water",
                "cmk-inventory",
                "db2_mem",
                "df",
                "df_netapp",
                "df_netapp32",
                "docker_container_mem",
                "enterasys_temp",
                "esx_vsphere_datastores",
                "esx_vsphere_hostsystem.mem_usage",
                "esx_vsphere_hostsystem.mem_usage_cluster",
                "etherbox.temp",
                "fortigate_memory",
                "fortigate_memory_base",
                "fortigate_node.memory",
                "hr_fs",
                "hr_mem",
                "http",
                "huawei_switch_mem",
                "hyperv_vms",
                "ibm_svc_mdiskgrp",
                "ibm_svc_system",
                "ibm_svc_systemstats.cache",
                "ibm_svc_systemstats.disk_latency",
                "ibm_svc_systemstats.diskio",
                "ibm_svc_systemstats.iops",
                "innovaphone_mem",
                "innovaphone_temp",
                "juniper_mem",
                "juniper_screenos_mem",
                "juniper_trpz_mem",
                "liebert_bat_temp",
                "logwatch",
                "logwatch.groups",
                "mem.used",
                "mem.win",
                "mknotifyd",
                "mknotifyd.connection",
                "mssql_backup",
                "mssql_counters.cache_hits",
                "mssql_counters.file_sizes",
                "mssql_counters.locks",
                "mssql_counters.locks_per_batch",
                "mssql_counters.pageactivity",
                "mssql_counters.sqlstats",
                "mssql_counters.transactions",
                "mssql_databases",
                "mssql_datafiles",
                "mssql_tablespaces",
                "mssql_transactionlogs",
                "mssql_versions",
                "netscaler_mem",
                "nullmailer_mailq",
                "nvidia.temp",
                "postfix_mailq",
                "ps",
                "ps.perf",
                "qmail_stats",
                "raritan_emx",
                "raritan_pdu_inlet",
                "services",
                "solaris_mem",
                "sophos_memory",
                "statgrab_mem",
                "tplink_mem",
                "ups_bat_temp",
                "vms_diskstat.df",
                "wmic_process",
                "zfsget",
            ],
            "enable_rulebased_notifications": True,
            "ui_theme": "facelift",
            "lock_on_logon_failures": 10,
        }

        if cmk_version.is_demo():
            settings["cmc_cmk_helpers"] = 3

        return settings

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
