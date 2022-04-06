#!/usr/bin/env python3
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

import abc
import ast
import base64
import copy
import glob
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
import sys
import tarfile
import threading
import time
import traceback
from hashlib import sha256
from pathlib import Path
from typing import List, NamedTuple

import requests
import urllib3  # type: ignore[import]

import cmk.utils
import cmk.utils.daemon as daemon
import cmk.utils.defines
import cmk.utils.paths
import cmk.utils.plugin_registry
import cmk.utils.regex
import cmk.utils.render as render
import cmk.utils.store as store
import cmk.utils.tags
import cmk.utils.version as cmk_version

import cmk.gui.background_job as background_job
import cmk.gui.hooks as hooks
import cmk.gui.log as log
import cmk.gui.mkeventd as mkeventd
import cmk.gui.sites
import cmk.gui.userdb as userdb
import cmk.gui.utils
import cmk.gui.watolib.auth_php
import cmk.gui.watolib.changes
import cmk.gui.watolib.git
import cmk.gui.watolib.timeperiods
import cmk.gui.weblib as weblib
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError, RequestTimeout
from cmk.gui.globals import active_config, html
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _, _u
from cmk.gui.log import logger

# TODO: cleanup all call sites to this name
from cmk.gui.valuespec import (
    Age,
    AjaxDropdownChoice,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    DualListChoice,
    EmailAddress,
    FixedValue,
    Float,
    Foldable,
    HostAddress,
    Integer,
    IPNetwork,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoredHostname,
    RegExp,
    TextAreaUnicode,
    TextInput,
    Transform,
    Tuple,
    UserID,
    ValueSpec,
)
from cmk.gui.watolib.activate_changes import (
    activate_changes_start,
    activate_changes_wait,
    ActivateChanges,
    ActivateChangesManager,
    ActivateChangesSite,
    add_replication_paths,
    confirm_all_local_changes,
    get_number_of_pending_changes,
    get_pending_changes_info,
    get_replication_paths,
)
from cmk.gui.watolib.analyze_configuration import (
    ac_test_registry,
    ACResult,
    ACResultCRIT,
    ACResultNone,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
)
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import (
    check_mk_local_automation_serialized,
    do_remote_automation,
    do_site_login,
    get_url,
    local_automation_failure,
    MKAutomationException,
    remote_automation_call_came_from_pre21,
)
from cmk.gui.watolib.changes import add_change, add_service_change, log_audit, make_diff_text
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainCore,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainLiveproxy,
    ConfigDomainOMD,
)
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    save_global_settings,
    save_site_global_settings,
)
from cmk.gui.watolib.groups import (
    add_group,
    delete_group,
    edit_group,
    find_usages_of_group,
    is_alias_used,
    save_group_information,
)
from cmk.gui.watolib.host_attributes import (
    collect_attributes,
    declare_host_attribute,
    EnumAttribute,
    FixedTextAttribute,
    get_sorted_host_attribute_topics,
    get_sorted_host_attributes_by_topic,
    host_attribute,
    NagiosTextAttribute,
    NagiosValueSpecAttribute,
    TextAttribute,
    undeclare_host_attribute,
    ValueSpecAttribute,
)
from cmk.gui.watolib.hosts_and_folders import (
    call_hook_hosts_changed,
    check_wato_foldername,
    collect_all_hosts,
    CREFolder,
    CREHost,
    Folder,
    folder_preserving_link,
    get_folder_title,
    get_folder_title_path,
    Host,
    make_action_link,
    validate_all_hosts,
)

# TODO: Cleanup all except declare_host_attribute which is still neded for pre 1.6 plugin
# compatibility. For the others: Find the call sites and change to full module import
from cmk.gui.watolib.notifications import save_notification_rules
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FilteredRulesetCollection,
    FolderRulesets,
    Rule,
    Ruleset,
    RulesetCollection,
    SearchedRulesets,
    SingleRulesetRecursively,
    StaticChecksRulesets,
)
from cmk.gui.watolib.rulespecs import (
    get_rulegroup,
    register_rule,
    register_rulegroup,
    Rulespec,
    rulespec_group_registry,
    RulespecGroup,
    RulespecGroupRegistry,
    RulespecSubGroup,
)
from cmk.gui.watolib.sample_config import init_wato_datastructures
from cmk.gui.watolib.sidebar_reload import is_sidebar_reload_needed, need_sidebar_reload
from cmk.gui.watolib.sites import CEESiteManagement, LivestatusViaTCP, SiteManagementFactory
from cmk.gui.watolib.snapshots import backup_domains
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.timeperiods import TimeperiodSelection
from cmk.gui.watolib.user_scripts import (
    load_notification_scripts,
    load_user_scripts,
    user_script_choices,
    user_script_title,
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
    convert_cgroups_from_tuple,
    format_config_value,
    has_agent_bakery,
    host_attribute_matches,
    liveproxyd_config_dir,
    mk_eval,
    mk_repr,
    multisite_dir,
    NEGATE,
    rename_host_in_list,
    site_neutral_path,
    wato_root_dir,
)
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_domain_registry,
    config_variable_registry,
    sample_config_generator_registry,
    SampleConfigGenerator,
    wato_fileheader,
)

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_watolib_plugins():
    cmk.gui.utils.load_web_plugins("watolib", globals())
