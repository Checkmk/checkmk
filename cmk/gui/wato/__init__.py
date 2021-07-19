#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# WATO
#
# This file contain acutal page handlers and WATO modes. It does HTML creation
# and implement AJAX handlers. It uses classes, functions and globals
# from watolib.py.

#   .--README--------------------------------------------------------------.
#   |               ____                _                                  |
#   |              |  _ \ ___  __ _  __| |  _ __ ___   ___                 |
#   |              | |_) / _ \/ _` |/ _` | | '_ ` _ \ / _ \                |
#   |              |  _ <  __/ (_| | (_| | | | | | | |  __/                |
#   |              |_| \_\___|\__,_|\__,_| |_| |_| |_|\___|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A few words about the implementation details of WATO.                |
#   `----------------------------------------------------------------------'

# [1] Files and Folders
# WATO organizes hosts in folders. A wato folder is represented by a
# OS directory. If the folder contains host definitions, then in that
# directory a file name "hosts{.mk|.cfg}" is kept.
# The directory hierarchy of WATO is rooted at etc/check_mk/conf.d/wato.
# All files in and below that directory are kept by WATO. WATO does not
# touch any other files or directories in conf.d.
# A *path* in WATO means a relative folder path to that directory. The
# root folder has the empty path (""). Folders are separated by slashes.
# Each directory contains a file ".wato" which keeps information needed
# by WATO but not by Checkmk itself.

# [3] Convention for variable names:
# site_id     --> The id of a site, None for the local site in non-distributed setup
# site        --> The dictionary datastructure of a site
# host_name   --> A string containing a host name
# host        --> An instance of the class Host
# folder_path --> A relative specification of a folder (e.g. "linux/prod")
# folder      --> An instance of the class Folder

#.
#   .--Init----------------------------------------------------------------.
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Importing, Permissions, global variables                             |
#   `----------------------------------------------------------------------'

# A huge number of imports are here to be compatible with old GUI plugins. Once we dropped support
# for them, we can remove this here and the imports
# flake8: noqa
# pylint: disable=unused-import,cmk-module-layer-violation

import abc
import ast
import csv
import datetime
import fcntl
import glob
import json
import math
import multiprocessing
import pprint
import random
import re
import tarfile
import shutil
import socket
import subprocess
import sys
import time
import traceback
import copy
import inspect
from hashlib import sha256
from typing import Type, Any, Dict, Optional as _Optional, Tuple as _Tuple, Union
from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.regex import regex
from cmk.utils.defines import short_service_state_name
import cmk.utils.render as render

import cmk.gui.utils as utils
import cmk.gui.sites as sites
from cmk.gui.globals import config
from cmk.gui.table import table_element
import cmk.gui.userdb as userdb
import cmk.gui.weblib as weblib
import cmk.gui.mkeventd
import cmk.gui.forms as forms
import cmk.gui.backup as backup
import cmk.gui.watolib as watolib
import cmk.gui.watolib.hosts_and_folders
from cmk.gui.watolib.activate_changes import update_config_generation
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.i18n
import cmk.gui.view_utils
import cmk.gui.plugins.wato.utils
import cmk.gui.plugins.wato.utils.base_modes
import cmk.gui.wato.mkeventd
import cmk.gui.wato.permissions
from cmk.gui.type_defs import PermissionName
from cmk.gui.pages import page_registry, Page
from cmk.gui.i18n import _u, _, _l
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import (
    HTTPRedirect,
    MKGeneralException,
    MKUserError,
    MKAuthException,
    MKInternalError,
    MKException,
)
from cmk.gui.permissions import (
    permission_registry,
    Permission,
)
from cmk.gui.log import logger
from cmk.gui.plugins.wato.utils.base_modes import WatoMode

from cmk.gui.wato.pages.activate_changes import (
    ModeActivateChanges,
    ModeAjaxStartActivation,
    ModeAjaxActivationState,
)
from cmk.gui.wato.pages.analyze_configuration import ModeAnalyzeConfig
from cmk.gui.wato.pages.diagnostics import ModeDiagnostics
from cmk.gui.wato.pages.audit_log import ModeAuditLog
from cmk.gui.wato.pages.automation import ModeAutomationLogin, ModeAutomation
import cmk.gui.wato.pages.fetch_agent_output
from cmk.gui.wato.pages.backup import (
    ModeBackup,
    ModeBackupTargets,
    ModeEditBackupTarget,
    ModeEditBackupJob,
    ModeBackupJobState,
    ModeBackupKeyManagement,
    ModeBackupEditKey,
    ModeBackupUploadKey,
    ModeBackupDownloadKey,
    ModeBackupRestore,
)
from cmk.gui.wato.pages.bulk_discovery import ModeBulkDiscovery
from cmk.gui.wato.pages.bulk_edit import ModeBulkEdit, ModeBulkCleanup
from cmk.gui.wato.pages.bulk_import import ModeBulkImport
from cmk.gui.wato.pages.check_catalog import ModeCheckManPage, ModeCheckPlugins
from cmk.gui.wato.pages.custom_attributes import (
    ModeEditCustomAttr,
    ModeEditCustomUserAttr,
    ModeEditCustomHostAttr,
    ModeCustomAttrs,
    ModeCustomUserAttrs,
    ModeCustomHostAttrs,
)
from cmk.gui.wato.pages.download_agents import ModeDownloadAgentsOther
from cmk.gui.wato.pages.folders import (
    ModeFolder,
    ModeAjaxPopupMoveToFolder,
    ModeEditFolder,
    ModeCreateFolder,
    ModeAjaxSetFoldertree,
)
from cmk.gui.wato.pages.global_settings import (
    ModeEditGlobals,
    ModeEditGlobalSetting,
)
from cmk.gui.wato.pages.groups import (
    ModeGroups,
    ModeHostgroups,
    ModeServicegroups,
    ModeContactgroups,
    ModeEditHostgroup,
    ModeEditServicegroup,
    ModeEditContactgroup,
)
from cmk.gui.wato.pages.host_diagnose import ModeDiagHost
from cmk.gui.wato.pages.host_rename import ModeBulkRenameHost, ModeRenameHost
from cmk.gui.wato.pages.tags import (
    ModeTags,
    ModeEditAuxtag,
    ModeEditTagGroup,
)
from cmk.gui.wato.pages.hosts import ModeEditHost, ModeCreateHost, ModeCreateCluster
from cmk.gui.wato.pages.icons import ModeIcons
from cmk.gui.wato.pages.ldap import ModeLDAPConfig, ModeEditLDAPConnection
from cmk.gui.wato.pages.not_implemented import ModeNotImplemented
from cmk.gui.wato.pages.notifications import (
    ModeNotifications,
    ModeUserNotifications,
    ModePersonalUserNotifications,
    ModeEditNotificationRule,
    ModeEditPersonalNotificationRule,
)
from cmk.gui.wato.pages.object_parameters import ModeObjectParameters
from cmk.gui.wato.pages.parentscan import ModeParentScan
from cmk.gui.wato.pages.password_store import ModePasswords, ModeEditPassword
from cmk.gui.wato.pages.predefined_conditions import ModePredefinedConditions, ModeEditPredefinedCondition
from cmk.gui.wato.pages.pattern_editor import ModePatternEditor
from cmk.gui.wato.pages.random_hosts import ModeRandomHosts
from cmk.gui.wato.pages.read_only import ModeManageReadOnly
from cmk.gui.wato.pages.roles import (
    ModeRoles,
    ModeEditRole,
    ModeRoleMatrix,
)
from cmk.gui.wato.pages.rulesets import (
    ModeEditRuleset,
    ModeEditRule,
    ModeCloneRule,
    ModeNewRule,
)
from cmk.gui.wato.pages.search import ModeSearch
from cmk.gui.wato.pages.services import (
    ModeDiscovery,
    ModeAjaxExecuteCheck,
)
from cmk.gui.wato.pages.sites import (
    ModeEditSite,
    ModeDistributedMonitoring,
    ModeEditSiteGlobals,
)
from cmk.gui.wato.pages.timeperiods import (
    ModeTimeperiods,
    ModeTimeperiodImportICal,
    ModeEditTimeperiod,
)
from cmk.gui.wato.pages.users import ModeUsers, ModeEditUser

import cmk.gui.plugins.wato

if not cmk_version.is_raw_edition():
    import cmk.gui.cee.plugins.wato  # pylint: disable=no-name-in-module

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
    import cmk.gui.cme.plugins.wato  # pylint: disable=no-name-in-module
    import cmk.gui.cme.plugins.wato.managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

wato_root_dir = watolib.wato_root_dir
multisite_dir = watolib.multisite_dir

# TODO: Kept for old plugin compatibility. Remove this one day
from cmk.gui.valuespec import *  # pylint: disable=wildcard-import,unused-wildcard-import

syslog_facilities = cmk.gui.mkeventd.syslog_facilities
ALL_HOSTS = watolib.ALL_HOSTS
ALL_SERVICES = watolib.ALL_SERVICES
NEGATE = watolib.NEGATE
from cmk.gui.plugins.wato import (
    monitoring_macro_help,
    UserIconOrAction,
    SNMPCredentials,
    HostnameTranslation,
    register_check_parameters,
    sort_sites,
    Levels,
    PredictiveLevels,
    mode_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
    RulespecGroupCheckParametersEnvironment,
    RulespecGroupCheckParametersHardware,
    RulespecGroupCheckParametersNetworking,
    RulespecGroupCheckParametersOperatingSystem,
    RulespecGroupCheckParametersPrinters,
    RulespecGroupCheckParametersStorage,
    RulespecGroupCheckParametersVirtualization,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
    get_search_expression,
    register_notification_parameters,
    register_hook,
)
# Has to be kept for compatibility with pre 1.6 register_rule() and register_check_parameters()
# calls in the WATO plugin context
subgroup_networking = RulespecGroupCheckParametersNetworking().sub_group_name
subgroup_storage = RulespecGroupCheckParametersStorage().sub_group_name
subgroup_os = RulespecGroupCheckParametersOperatingSystem().sub_group_name
subgroup_printing = RulespecGroupCheckParametersPrinters().sub_group_name
subgroup_environment = RulespecGroupCheckParametersEnvironment().sub_group_name
subgroup_applications = RulespecGroupCheckParametersApplications().sub_group_name
subgroup_virt = RulespecGroupCheckParametersVirtualization().sub_group_name
subgroup_hardware = RulespecGroupCheckParametersHardware().sub_group_name
subgroup_inventory = RulespecGroupCheckParametersDiscovery().sub_group_name

# Make some functions of watolib available to WATO plugins without using the
# watolib module name. This is mainly done for compatibility reasons to keep
# the current plugin API functions working
import cmk.gui.watolib.network_scan
import cmk.gui.watolib.read_only
from cmk.gui.watolib import (
    register_rulegroup,
    register_rule,
    add_replication_paths,
    ConfigDomainGUI,
    ConfigDomainCore,
    ConfigDomainOMD,
    ConfigDomainEventConsole,
    add_change,
    add_service_change,
    site_neutral_path,
    declare_host_attribute,
    NagiosTextAttribute,
    ValueSpecAttribute,
    ACTestCategories,
    ACTest,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    LivestatusViaTCP,
    make_action_link,
    init_wato_datastructures,
)
from cmk.gui.plugins.watolib.utils import (
    register_configvar,
    configvar_order,
)

modes: Dict[Any, Any] = {}

from cmk.gui.plugins.wato.utils.html_elements import (
    wato_html_head,
    initialize_wato_html_head,
    wato_html_footer,
    search_form,
)

from cmk.gui.plugins.wato.utils.main_menu import (
    MainMenu,
    MenuItem,
    # Kept for compatibility with pre 1.6 plugins
    WatoModule,
    register_modules,
)

# Import the module to register page handler
import cmk.gui.wato.page_handler

#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Prepare plugin-datastructures and load WATO plugins                  |
#   '----------------------------------------------------------------------'

modes = {}

loaded_with_language: Union[bool, None, str] = False


def load_plugins(force: bool) -> None:
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Initialize watolib things which are needed before loading the WATO plugins.
    # This also loads the watolib plugins.
    watolib.load_watolib_plugins()

    utils.load_web_plugins("wato", globals())

    if modes:
        raise MKGeneralException(
            _("Deprecated WATO modes found: %r. "
              "They need to be refactored to new API.") % list(modes.keys()))

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()
