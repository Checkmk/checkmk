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
# directory a file name "hosts.mk" is kept.
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
from typing import TYPE_CHECKING, Type, Any, Dict, Optional as _Optional, Tuple as _Tuple, Union
from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.translations
import cmk.utils.store as store
from cmk.utils.regex import regex
from cmk.utils.defines import short_service_state_name
import cmk.utils.render as render
from cmk.utils.type_defs import HostName, HostAddress as TypingHostAddress

import cmk.gui.utils as utils
import cmk.gui.sites as sites
import cmk.gui.config as config
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
from cmk.gui.display_options import display_options
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
    ModeStaticChecksRulesets,
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
    may_edit_ruleset,
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
    wato_confirm,
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

NetworkScanFoundHosts = List[_Tuple[HostName, TypingHostAddress]]
NetworkScanResult = Dict[str, Any]

if TYPE_CHECKING:
    from cmk.gui.watolib.hosts_and_folders import CREFolder

#.
#   .--Network Scan--------------------------------------------------------.
#   |   _   _      _                      _      ____                      |
#   |  | \ | | ___| |___      _____  _ __| | __ / ___|  ___ __ _ _ __      |
#   |  |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / \___ \ / __/ _` | '_ \     |
#   |  | |\  |  __/ |_ \ V  V / (_) | |  |   <   ___) | (_| (_| | | | |    |
#   |  |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\ |____/ \___\__,_|_| |_|    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The WATO folders network scan for new hosts.                         |
#   '----------------------------------------------------------------------'


# Executed by the multisite cron job once a minute. Is only executed in the
# master site. Finds the next folder to scan and starts it via WATO
# automation. The result is written to the folder in the master site.
def execute_network_scan_job() -> None:
    init_wato_datastructures(with_wato_lock=True)

    if watolib.is_wato_slave_site():
        return  # Don't execute this job on slaves.

    folder = find_folder_to_scan()
    if not folder:
        return  # Nothing to do.

    # We need to have the context of the user. The jobs are executed when
    # config.set_user_by_id() has not been executed yet. So there is no user context
    # available. Use the run_as attribute from the job config and revert
    # the previous state after completion.
    old_user = config.user.id
    run_as = folder.attribute("network_scan")["run_as"]
    if not userdb.user_exists(run_as):
        raise MKGeneralException(
            _("The user %s used by the network "
              "scan of the folder %s does not exist.") % (run_as, folder.title()))
    config.set_user_by_id(folder.attribute("network_scan")["run_as"])

    result: NetworkScanResult = {
        "start": time.time(),
        "end": True,  # means currently running
        "state": None,
        "output": "The scan is currently running.",
    }

    # Mark the scan in progress: Is important in case the request takes longer than
    # the interval of the cron job (1 minute). Otherwise the scan might be started
    # a second time before the first one finished.
    save_network_scan_result(folder, result)

    try:
        if config.site_is_local(folder.site_id()):
            found = cmk.gui.watolib.network_scan.do_network_scan(folder)
        else:
            found = watolib.do_remote_automation(config.site(folder.site_id()), "network-scan",
                                                 [("folder", folder.path())])

        if not isinstance(found, list):
            raise MKGeneralException(_("Received an invalid network scan result: %r") % found)

        add_scanned_hosts_to_folder(folder, found)

        result.update({
            "state": True,
            "output": _("The network scan found %d new hosts.") % len(found),
        })
    except Exception as e:
        result.update({
            "state": False,
            "output": _("An exception occured: %s") % e,
        })
        logger.error("Exception in network scan:\n%s", traceback.format_exc())

    result["end"] = time.time()

    save_network_scan_result(folder, result)

    if old_user:
        config.set_user_by_id(old_user)


def find_folder_to_scan() -> '_Optional[CREFolder]':
    """Find the folder which network scan is longest waiting and return the folder object."""
    folder_to_scan = None
    for folder in watolib.Folder.all_folders().values():
        scheduled_time = folder.next_network_scan_at()
        if scheduled_time is not None and scheduled_time < time.time():
            if folder_to_scan is None:
                folder_to_scan = folder
            elif folder_to_scan.next_network_scan_at() > folder.next_network_scan_at():
                folder_to_scan = folder
    return folder_to_scan


def add_scanned_hosts_to_folder(folder: 'CREFolder', found: NetworkScanFoundHosts) -> None:
    network_scan_properties = folder.attribute("network_scan")

    translation = network_scan_properties.get("translate_names", {})

    entries = []
    for host_name, ipaddr in found:
        host_name = ensure_str(
            cmk.utils.translations.translate_hostname(translation, ensure_str(host_name)))

        attrs = cmk.gui.watolib.hosts_and_folders.update_metadata({}, created_by=_("Network scan"))

        if "tag_criticality" in network_scan_properties:
            attrs["tag_criticality"] = network_scan_properties.get("tag_criticality", "offline")

        if network_scan_properties.get("set_ipaddress", True):
            attrs["ipaddress"] = ipaddr

        if not watolib.Host.host_exists(host_name):
            entries.append((host_name, attrs, None))

    with store.lock_checkmk_configuration():
        folder.create_hosts(entries)
        folder.save()


def save_network_scan_result(folder: 'CREFolder', result: NetworkScanResult) -> None:
    # Reload the folder, lock WATO before to protect against concurrency problems.
    with store.lock_checkmk_configuration():
        # A user might have changed the folder somehow since starting the scan. Load the
        # folder again to get the current state.
        write_folder = watolib.Folder.folder(folder.path())
        write_folder.set_attribute("network_scan_result", result)
        write_folder.save()


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


permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="use",
        title=_l("Use WATO"),
        description=_l("This permissions allows users to use WATO - Check_MK's "
                       "Web Administration Tool. Without this "
                       "permission all references to WATO (buttons, links, "
                       "snapins) will be invisible."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="edit",
        title=_l("Make changes, perform actions"),
        description=_l("This permission is needed in order to make any "
                       "changes or perform any actions at all. "
                       "Without this permission, the user is only "
                       "able to view data, and that only in modules he "
                       "has explicit permissions for."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="seeall",
        title=_l("Read access to all modules"),
        description=_l("When this permission is set then the user sees "
                       "also such modules he has no explicit "
                       "access to (see below)."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="activate",
        title=_l("Activate Configuration"),
        description=_l("This permission is needed for activating the "
                       "current configuration (and thus rewriting the "
                       "monitoring configuration and restart the monitoring daemon.)"),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="activateforeign",
        title=_l("Activate Foreign Changes"),
        description=_l("When several users work in parallel with WATO then "
                       "several pending changes of different users might pile up "
                       "before changes are activate. Only with this permission "
                       "a user will be allowed to activate the current configuration "
                       "if this situation appears."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="auditlog",
        title=_l("Audit Log"),
        description=_l("Access to the historic audit log. "
                       "The currently pending changes can be seen by all users "
                       "with access to WATO."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="clear_auditlog",
        title=_l("Clear audit Log"),
        description=_l(
            "Clear the entries of the audit log. To be able to clear the audit log "
            "a user needs the generic WATO permission \"Make changes, perform actions\", "
            "the \"View audit log\" and this permission."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="hosts",
        title=_l("Host management"),
        description=_l("Access to the management of hosts and folders. This "
                       "module has some additional permissions (see below)."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="edit_hosts",
        title=_l("Modify existing hosts"),
        description=_l("Modify the properties of existing hosts. Please note: "
                       "for the management of services (inventory) there is "
                       "a separate permission (see below)"),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="parentscan",
        title=_l("Perform network parent scan"),
        description=_l("This permission is neccessary for performing automatic "
                       "scans for network parents of hosts (making use of traceroute). "
                       "Please note, that for actually modifying the parents via the "
                       "scan and for the creation of gateway hosts proper permissions "
                       "for host and folders are also neccessary."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="move_hosts",
        title=_l("Move existing hosts"),
        description=_l("Move existing hosts to other folders. Please also add the permission "
                       "<i>Modify existing hosts</i>."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="manage_hosts",
        title=_l("Add & remove hosts"),
        description=_l("Add hosts to the monitoring and remove hosts "
                       "from the monitoring. Please also add the permission "
                       "<i>Modify existing hosts</i>."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="rename_hosts",
        title=_l("Rename existing hosts"),
        description=_l("Rename existing hosts. Please also add the permission "
                       "<i>Modify existing hosts</i>."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="diag_host",
        title=_l("Host Diagnostic"),
        description=_l("Check whether or not the host is reachable, test the different methods "
                       "a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out "
                       "the correct monitoring configuration for that host."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="clone_hosts",
        title=_l("Clone hosts"),
        description=_l("Clone existing hosts to create new ones from the existing one."
                       "Please also add the permission <i>Add & remove hosts</i>."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="random_hosts",
        title=_l("Create random hosts"),
        description=_l("The creation of random hosts is a facility for test and development "
                       "and disabled by default. It allows you to create a number of random "
                       "hosts and thus simulate larger environments."),
        defaults=[],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="update_dns_cache",
        title=_l("Update DNS Cache"),
        description=_l("Updating the DNS cache is neccessary in order to reflect IP address "
                       "changes in hosts that are configured without an explicit address."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="services",
        title=_l("Manage services"),
        description=_l("Do inventory and service configuration on existing hosts."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="edit_folders",
        title=_l("Modify existing folders"),
        description=_l("Modify the properties of existing folders."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="manage_folders",
        title=_l("Add & remove folders"),
        description=_l(
            "Add new folders and delete existing folders. If a folder to be deleted contains hosts then "
            "the permission to delete hosts is also required."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="passwords",
        title=_l("Password management"),
        description=_l("This permission is needed for the module <i>Passwords</i>."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="edit_all_passwords",
        title=_l("Write access to all passwords"),
        description=_l(
            "Without this permission, users can only edit passwords which are shared with a contact "
            "group they are member of. This permission grants full access to all passwords."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="edit_all_predefined_conditions",
        title=_l("Write access to all predefined conditions"),
        description=_l(
            "Without this permission, users can only edit predefined conditions which are "
            "shared with a contact group they are member of. This permission grants full "
            "access to all predefined conditions."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="see_all_folders",
        title=_l("Read access to all hosts and folders"),
        description=_l(
            "Users without this permissions can only see folders with a contact group they are in."
        ),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="all_folders",
        title=_l("Write access to all hosts and folders"),
        description=_l(
            "Without this permission, operations on folders can only be done by users that are members of "
            "one of the folders contact groups. This permission grants full access to all folders and hosts."
        ),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="hosttags",
        title=_l("Manage tags"),
        description=_l("Create, remove and edit tags. Removing tags also might remove rules, "
                       "so this permission should not be available to normal users."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="global",
        title=_l("Global settings"),
        description=_l("Access to the module <i>Global settings</i>"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="rulesets",
        title=_l("Rulesets"),
        description=_l(
            "Access to the module for managing Check_MK rules. Please note that a user can only "
            "manage rules in folders he has permissions to. "),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="groups",
        title=_l("Host & Service Groups"),
        description=_l("Access to the modules for managing host and service groups."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="timeperiods",
        title=_l("Timeperiods"),
        description=_l("Access to the module <i>Timeperiods</i>"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="sites",
        title=_l("Site management"),
        description=_l("Access to the module for managing connections to remote monitoring sites."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="automation",
        title=_l("Site remote automation"),
        description=_l("This permission is needed for a remote administration of the site "
                       "as a distributed WATO slave."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="users",
        title=_l("User management"),
        description=_l("This permission is needed for the modules <b>Users</b>, "
                       "<b>Roles</b> and <b>Contact Groups</b>"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="show_last_user_activity",
        title=_l("Show last user activity"),
        description=_l("Show the online state and last user activity on the users page"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="notifications",
        title=_l("Notification configuration"),
        description=_l(
            "This permission is needed for the new rule based notification configuration via the WATO module <i>Notifications</i>."
        ),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="snapshots",
        title=_l("Manage snapshots"),
        description=_l(
            "Access to the module <i>Snaphsots</i>. Please note: a user with "
            "write access to this module "
            "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="backups",
        title=_l("Backup & Restore"),
        description=_l(
            "Access to the module <i>Site backup</i>. Please note: a user with "
            "write access to this module "
            "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="pattern_editor",
        title=_l("Logfile Pattern Analyzer"),
        description=_l("Access to the module for analyzing and validating logfile patterns."),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="icons",
        title=_l("Manage Custom Icons"),
        description=_l("Upload or delete custom icons"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="custom_attributes",
        title=_l("Manage custom attributes"),
        description=_l("Manage custom host- and user attributes"),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="download_agents",
        title=_l("Monitoring Agents"),
        description=_l("Download the default Check_MK monitoring agents for Linux, "
                       "Windows and other operating systems."),
        defaults=config.builtin_role_ids,
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="download_agent_output",
        title=_l("Download Agent Output / SNMP Walks"),
        description=_l(
            "Allows to download the current agent output or SNMP walks of the monitored hosts."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="set_read_only",
        title=_l("Set WATO to read only mode for other users"),
        description=_l("Prevent other users from making modifications to WATO."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="analyze_config",
        title=_l("Access the best analyze configuration functionality provided by WATO"),
        description=_l(
            "WATO has a module that gives you hints on how to tune your Check_MK installation."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="diagnostics",
        title=_l("Access the diagnostics mode"),
        description=_l("Collect information of Checkmk sites for diagnostic analysis."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="add_or_modify_executables",
        title=_l("Can add or modify executables"),
        description=_l(
            "There are different places in Check_MK where an admin can use the GUI to add "
            "executable code to Check_MK. For example when configuring "
            "datasource programs, the user inserts a command line for gathering monitoring data. "
            "This command line is then executed during monitoring by Check_MK. Another example is "
            "the upload of extension packages (MKPs). All these functions have in "
            "common that the user provides data that is executed by Check_MK. "
            "If you want to ensure that your WATO users cannot \"inject\" arbitrary executables "
            "into your Check_MK installation, you only need to remove this permission for them. "
            "This permission is needed in addition to the other component related permissions. "
            "For example you need the <tt>wato.rulesets</tt> permission together with this "
            "permission to be able to configure rulesets where bare command lines are "
            "configured."),
        defaults=["admin"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="service_discovery_to_undecided",
        title=_l("Service discovery: Move to undecided services"),
        description=_l("Service discovery: Move to undecided services"),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="service_discovery_to_monitored",
        title=_l("Service discovery: Move to monitored services"),
        description=_l("Service discovery: Move to monitored services"),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="service_discovery_to_ignored",
        title=_l("Service discovery: Disabled services"),
        description=_l("Service discovery: Disabled services"),
        defaults=["admin", "user"],
    ))

permission_registry.register(
    Permission(
        section=cmk.gui.plugins.wato.utils.PermissionSectionWATO,
        name="service_discovery_to_removed",
        title=_l("Service discovery: Remove services"),
        description=_l("Service discovery: Remove services"),
        defaults=["admin", "user"],
    ))
