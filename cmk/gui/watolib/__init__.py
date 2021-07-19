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
from typing import NamedTuple, List
from pathlib import Path

import requests
import urllib3  # type: ignore[import]

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
from cmk.gui.globals import config
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.mkeventd as mkeventd
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
    TextInput,
    TextAreaUnicode,
    AjaxDropdownChoice,
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
from cmk.gui.sites import (
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
)
from cmk.gui.watolib.changes import (
    log_audit,
    add_change,
    add_service_change,
    make_diff_text,
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
    activate_changes_start,
    activate_changes_wait,
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
    RulespecGroupEnforcedServices,
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
    collect_all_hosts,
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
from cmk.gui.watolib.automation_commands import AutomationCommand, automation_command_registry
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    save_site_global_settings,
    save_global_settings,
)
from cmk.gui.watolib.sample_config import (
    init_wato_datastructures,)
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
