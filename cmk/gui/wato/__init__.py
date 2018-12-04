#!/usr/bin/env python
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
# by WATO but not by Check_MK itself.

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
import Queue
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

import cmk
import cmk.paths
import cmk.translations
import cmk.store as store
from cmk.regex import regex
from cmk.defines import short_service_state_name
import cmk.render as render

import cmk.gui.utils as utils
import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.table as table
import cmk.gui.multitar as multitar
import cmk.gui.userdb as userdb
import cmk.gui.weblib as weblib
import cmk.gui.mkeventd
import cmk.gui.forms as forms
import cmk.gui.backup as backup
import cmk.gui.watolib as watolib
import cmk.gui.background_job as background_job
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.view_utils
import cmk.gui.plugins.wato.utils
import cmk.gui.plugins.wato.utils.base_modes
import cmk.gui.wato.mkeventd
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import (
    MKGeneralException,
    MKUserError,
    MKAuthException,
    MKInternalError,
    MKException,
)
from cmk.gui.log import logger
from cmk.gui.display_options import display_options
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, WatoWebApiMode

from cmk.gui.wato.pages.activate_changes import (
    ModeActivateChanges,
    ModeAjaxStartActivation,
    ModeAjaxActivationState,
)
from cmk.gui.wato.pages.analyze_configuration import ModeAnalyzeConfig
from cmk.gui.wato.pages.audit_log import ModeAuditLog
from cmk.gui.wato.pages.automation import ModeAutomationLogin, ModeAutomation
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
from cmk.gui.wato.pages.download_agents import ModeDownloadAgents
from cmk.gui.wato.pages.folders import (
    ModeFolder,
    ModeAjaxPopupMoveToFolder,
    ModeEditFolder,
    ModeCreateFolder,
    ModeAjaxSetFoldertree,
)
from cmk.gui.wato.pages.global_settings import (
    GlobalSettingsMode,
    EditGlobalSettingMode,
    ModeEditGlobals,
    ModeEditGlobalSetting,
    ModeEditSiteGlobalSetting,
)
from cmk.gui.wato.pages.groups import (
    ModeGroups,
    ModeHostgroups,
    ModeServicegroups,
    ModeContactgroups,
    ModeEditGroup,
    ModeEditHostgroup,
    ModeEditServicegroup,
    ModeEditContactgroup,
)
from cmk.gui.wato.pages.host_diagnose import ModeDiagHost
from cmk.gui.wato.pages.host_rename import ModeBulkRenameHost, ModeRenameHost
from cmk.gui.wato.pages.host_tags import (
    ModeHostTags,
    ModeEditHosttagConfiguration,
    ModeEditAuxtag,
    ModeEditHosttagGroup,
)
from cmk.gui.wato.pages.hosts import ModeEditHost, ModeCreateHost, ModeCreateCluster
from cmk.gui.wato.pages.icons import ModeIcons
from cmk.gui.wato.pages.ldap import ModeLDAPConfig, ModeEditLDAPConnection
from cmk.gui.wato.pages.main import ModeMain
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
from cmk.gui.wato.pages.pattern_editor import ModePatternEditor
from cmk.gui.wato.pages.random_hosts import ModeRandomHosts
from cmk.gui.wato.pages.read_only import ModeManageReadOnly
from cmk.gui.wato.pages.roles import (
    ModeRoles,
    ModeEditRole,
    ModeRoleMatrix,
)
from cmk.gui.wato.pages.rulesets import (
    ModeRuleEditor,
    ModeRulesets,
    ModeStaticChecksRulesets,
    ModeEditRuleset,
    ModeRuleSearch,
    ModeEditRule,
    ModeCloneRule,
    ModeNewRule,
)
from cmk.gui.wato.pages.search import ModeSearch
from cmk.gui.wato.pages.services import (
    ModeDiscovery,
    ModeFirstDiscovery,
    ModeAjaxExecuteCheck,
)
from cmk.gui.wato.pages.sites import (
    ModeSites,
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
import cmk.gui.plugins.wato.bi

if not cmk.is_raw_edition():
    import cmk.gui.cee.plugins.wato

if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed
    import cmk.gui.cme.plugins.wato
    import cmk.gui.cme.plugins.wato.managed
else:
    managed = None

wato_root_dir = watolib.wato_root_dir
multisite_dir = watolib.multisite_dir

# TODO: Kept for old plugin compatibility. Remove this one day
from cmk.gui.valuespec import *  # pylint: disable=wildcard-import,redefined-builtin
syslog_facilities = cmk.gui.mkeventd.syslog_facilities
ALL_HOSTS = watolib.ALL_HOSTS
ALL_SERVICES = watolib.ALL_SERVICES
NEGATE = watolib.NEGATE
NO_ITEM = watolib.NO_ITEM
ENTRY_NEGATE_CHAR = watolib.ENTRY_NEGATE_CHAR
from cmk.gui.plugins.wato import (
    may_edit_ruleset,
    monitoring_macro_help,
    UserIconOrAction,
    SNMPCredentials,
    HostnameTranslation,
    GroupSelection,
    rule_option_elements,
    register_check_parameters,
    sort_sites,
    Levels,
    PredictiveLevels,
    EventsMode,
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
from cmk.gui.watolib import (
    PasswordStore,
    TimeperiodSelection,
    register_rulegroup,
    register_rule,
    register_hook,
    add_replication_paths,
    UserSelection,
    ConfigDomainGUI,
    ConfigDomainCore,
    ConfigDomainOMD,
    ConfigDomainEventConsole,
    add_change,
    add_service_change,
    site_neutral_path,
    register_notification_parameters,
    declare_host_attribute,
    Attribute,
    ContactGroupsAttribute,
    NagiosTextAttribute,
    ValueSpecAttribute,
    ACTestCategories,
    ACTest,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    LivestatusViaTCP,
    SiteBackupJobs,
    make_action_link,
    is_a_checkbox,
    get_search_expression,
    may_edit_configvar,
    multifolder_host_rule_match_conditions,
    simple_host_rule_match_conditions,
    transform_simple_to_multi_host_rule_match_conditions,
    WatoBackgroundJob,
    init_wato_datastructures,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
)
from cmk.gui.plugins.watolib.utils import (
    register_configvar,
    configvar_order,
)

modes = {}

from cmk.gui.plugins.wato.utils.html_elements import (
    wato_styles,
    wato_confirm,
    wato_html_head,
    initialize_wato_html_head,
    wato_html_footer,
    search_form,
)

from cmk.gui.plugins.wato.utils.context_buttons import (
    global_buttons,
    changelog_button,
    home_button,
    host_status_button,
    service_status_button,
    folder_status_button,
)

from cmk.gui.plugins.wato.utils.main_menu import (
    MainMenu,
    MenuItem,
    get_modules,
    # Kept for compatibility with pre 1.6 plugins
    WatoModule,
    register_modules,
)

#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Der Seitenaufbau besteht aus folgenden Teilen:                       |
#   | 1. Kontextbuttons: wo kann man von hier aus hinspringen, ohne Aktion |
#   | 2. Verarbeiten einer Aktion, falls eine gültige Transaktion da ist   |
#   | 3. Anzeigen von Inhalten                                             |
#   |                                                                      |
#   | Der Trick: welche Inhalte angezeigt werden, hängt vom Ausgang der    |
#   | Aktion ab. Wenn man z.B. bei einem Host bei "Create new host" auf    |
#   | [Save] klickt, dann kommt bei Erfolg die Inventurseite, bei Miss-    |
#   | bleibt man auf der Neuanlegen-Seite                                  |
#   |                                                                      |
#   | Dummerweise kann ich aber die Kontextbuttons erst dann anzeigen,     |
#   | wenn ich den Ausgang der Aktion kenne. Daher wird zuerst die Aktion  |
#   | ausgeführt, welche aber keinen HTML-Code ausgeben darf.              |
#   `----------------------------------------------------------------------'


@cmk.gui.pages.register("wato")
def page_handler():
    initialize_wato_html_head()

    if not config.wato_enabled:
        raise MKGeneralException(
            _("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
              " in your <tt>multisite.mk</tt> if you want to use WATO."))

    if cmk.is_managed_edition() and not managed.is_provider(config.current_customer):
        raise MKGeneralException(
            _("Check_MK can only be configured on "
              "the managers central site."))

    current_mode = html.var("mode") or "main"
    mode_permissions, mode_class = get_mode_permission_and_class(current_mode)

    display_options.load_from_html()

    if display_options.disabled(display_options.N):
        html.add_body_css_class("inline")

    # If we do an action, we aquire an exclusive lock on the complete WATO.
    if html.is_transaction():
        watolib.lock_exclusive()

    try:
        init_wato_datastructures(with_wato_lock=not html.is_transaction())
    except:
        # Snapshot must work in any case
        if current_mode == 'snapshot':
            pass
        else:
            raise

    # Check general permission for this mode
    if mode_permissions is not None and not config.user.may("wato.seeall"):
        ensure_mode_permissions(mode_permissions)

    mode = mode_class()

    # Do actions (might switch mode)
    action_message = None
    if html.is_transaction():
        try:
            config.user.need_permission("wato.edit")

            # Even if the user has seen this mode because auf "seeall",
            # he needs an explicit access permission for doing changes:
            if config.user.may("wato.seeall"):
                if mode_permissions:
                    ensure_mode_permissions(mode_permissions)

            if watolib.is_read_only_mode_enabled() and not watolib.may_override_read_only_mode():
                raise MKUserError(None, watolib.read_only_message())

            result = mode.action()
            if isinstance(result, tuple):
                newmode, action_message = result
            else:
                newmode = result

            # If newmode is False, then we shall immediately abort.
            # This is e.g. the case, if the page outputted non-HTML
            # data, such as a tarball (in the export function). We must
            # be sure not to output *any* further data in that case.
            if newmode is False:
                return

            # if newmode is not None, then the mode has been changed
            elif newmode is not None:
                if newmode == "":  # no further information: configuration dialog, etc.
                    if action_message:
                        html.message(action_message)
                        wato_html_footer()
                    return
                mode_permissions, mode_class = get_mode_permission_and_class(newmode)
                current_mode = newmode
                mode = mode_class()
                html.set_var("mode", newmode)  # will be used by makeuri

                # Check general permissions for the new mode
                if mode_permissions is not None and not config.user.may("wato.seeall"):
                    for pname in mode_permissions:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.user.need_permission(pname)

        except MKUserError as e:
            action_message = "%s" % e
            html.add_user_error(e.varname, action_message)

        except MKAuthException as e:
            action_message = e.reason
            html.add_user_error(None, e.reason)

    wato_html_head(
        mode.title(),
        show_body_start=display_options.enabled(display_options.H),
        show_top_heading=display_options.enabled(display_options.T))

    if display_options.enabled(display_options.B):
        # Show contexts buttons
        html.begin_context_buttons()
        mode.buttons()
        for inmode, buttontext, target in extra_buttons:
            if inmode == current_mode:
                if hasattr(target, '__call__'):
                    target = target()
                    if not target:
                        continue
                if target[0] == '/' or target.startswith('../') or '://' in target:
                    html.context_button(buttontext, target)
                else:
                    html.context_button(buttontext,
                                        watolib.folder_preserving_link([("mode", target)]))
        html.end_context_buttons()

    if not html.is_transaction() or (watolib.is_read_only_mode_enabled() and
                                     watolib.may_override_read_only_mode()):
        _show_read_only_warning()

    # Show outcome of action
    if html.has_user_errors():
        html.show_error(action_message)
    elif action_message:
        html.message(action_message)

    # Show content
    mode.handle_page()

    if watolib.is_sidebar_reload_needed():
        html.reload_sidebar()

    if config.wato_use_git and html.is_transaction():
        watolib.do_git_commit()

    wato_html_footer(
        display_options.enabled(display_options.Z), display_options.enabled(display_options.H))


def get_mode_permission_and_class(mode_name):
    mode_class = mode_registry.get(mode_name, ModeNotImplemented)
    mode_permissions = mode_class.permissions()

    if mode_class is None:
        raise MKGeneralException(_("No such WATO module '<tt>%s</tt>'") % mode_name)

    if inspect.isfunction(mode_class):
        raise MKGeneralException(
            _("Deprecated WATO module: Implemented as function. "
              "This needs to be refactored as WatoMode child class."))

    if mode_permissions is not None and not config.user.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    return mode_permissions, mode_class


def ensure_mode_permissions(mode_permissions):
    for pname in mode_permissions:
        if '.' not in pname:
            pname = "wato." + pname
        config.user.need_permission(pname)


def _show_read_only_warning():
    if watolib.is_read_only_mode_enabled():
        html.show_warning(watolib.read_only_message())


#.
#   .--Agent-Output--------------------------------------------------------.
#   |     _                    _         ___        _               _      |
#   |    / \   __ _  ___ _ __ | |_      / _ \ _   _| |_ _ __  _   _| |_    |
#   |   / _ \ / _` |/ _ \ '_ \| __|____| | | | | | | __| '_ \| | | | __|   |
#   |  / ___ \ (_| |  __/ | | | ||_____| |_| | |_| | |_| |_) | |_| | |_    |
#   | /_/   \_\__, |\___|_| |_|\__|     \___/ \__,_|\__| .__/ \__,_|\__|   |
#   |         |___/                                    |_|                 |
#   +----------------------------------------------------------------------+
#   | Page for downloading the current agent output / SNMP walk of a host  |
#   '----------------------------------------------------------------------'
# TODO: This feature is used exclusively from the GUI. Why is the code in
#       wato.py? The only reason is because the WATO automation is used. Move
#       to better location.


class AgentOutputPage(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(AgentOutputPage, self).__init__()
        self._from_vars()

    def _from_vars(self):
        config.user.need_permission("wato.download_agent_output")

        host_name = html.var("host")
        if not host_name:
            raise MKGeneralException(_("The host is missing."))

        ty = html.var("type")
        if ty not in ["walk", "agent"]:
            raise MKGeneralException(_("Invalid type specified."))
        self._ty = ty

        self._back_url = html.get_url_input("back_url")

        init_wato_datastructures(with_wato_lock=True)

        host = watolib.Folder.current().host(host_name)
        if not host:
            raise MKGeneralException(
                _("Host is not managed by WATO. "
                  "Click <a href=\"%s\">here</a> to go back.") % html.escape_attribute(
                      self._back_url))
        host.need_permission("read")
        self._host = host

        self._job = FetchAgentOutputBackgroundJob(self._host.site_id(), self._host.name(), self._ty)

    @abc.abstractmethod
    def page(self):
        pass

    @staticmethod
    def file_name(site_id, host_name, ty):
        return "%s-%s-%s.txt" % (site_id, host_name, ty)


class PageFetchAgentOutput(AgentOutputPage):
    def page(self):
        html.header(
            _("%s: Download agent output") % self._host.name(), stylesheets=["status", "pages"])

        html.begin_context_buttons()
        if self._back_url:
            html.context_button(_("Back"), self._back_url, "back")
        html.end_context_buttons()

        self._action()

        if html.has_var("_start"):
            try:
                self._job.start()
            except background_job.BackgroundJobAlreadyRunning:
                pass

        self._show_status(self._job)

        html.footer()

    def _action(self):
        if not html.transaction_valid():
            return

        action_handler = gui_background_job.ActionHandler()

        if action_handler.handle_actions() and action_handler.did_delete_job():
            html.response.http_redirect(
                html.makeuri_contextless([
                    ("host", self._host.name()),
                    ("type", self._ty),
                    ("back_url", self._back_url),
                ]))

    def _show_status(self, job):
        job_snapshot = job.get_status_snapshot()

        if job_snapshot.is_running():
            html.h3(_("Current status of process"))
            html.immediate_browser_redirect(0.8, html.makeuri([]))
        elif job.exists():
            html.h3(_("Result of last process"))

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot=job_snapshot)


# TODO: Clean this up! We would like to use the cmk.gui.pages.register() decorator instead
# of this
cmk.gui.pages.register_page_handler("fetch_agent_output", lambda: PageFetchAgentOutput().page())


@gui_background_job.job_registry.register
class FetchAgentOutputBackgroundJob(WatoBackgroundJob):
    job_prefix = "agent-output-"
    gui_title = _("Fetch agent output")

    def __init__(self, site_id, host_name, ty):
        self._site_id = site_id
        self._host_name = host_name
        self._ty = ty

        job_id = "%s%s-%s-%s" % (self.job_prefix, site_id, host_name, ty)
        title = _("Fetching %s of %s / %s") % (ty, site_id, host_name)
        super(FetchAgentOutputBackgroundJob, self).__init__(job_id, title=title)

        self.set_function(self._fetch_agent_output)

    def _fetch_agent_output(self, job_interface):
        job_interface.send_progress_update(_("Fetching '%s'...") % self._ty)

        success, output, agent_data = watolib.check_mk_automation(self._site_id, "get-agent-output",
                                                                  [self._host_name, self._ty])

        if not success:
            job_interface.send_progress_update(_("Failed: %s") % output)

        preview_filepath = os.path.join(
            job_interface.get_work_dir(),
            AgentOutputPage.file_name(self._site_id, self._host_name, self._ty))
        store.save_file(preview_filepath, agent_data)

        download_url = html.makeuri_contextless([("host", self._host_name), ("type", self._ty)],
                                                filename="download_agent_output.py")

        button = html.render_icon_button(download_url, _("Download"), "agent_output")
        job_interface.send_progress_update(_("Finished. Click on the icon to download the data."))
        job_interface.send_result_message(_("%s Finished.") % button)


class PageDownloadAgentOutput(AgentOutputPage):
    def page(self):
        file_name = self.file_name(self._host.site_id(), self._host.name(), self._ty)

        html.set_output_format("text")
        html.response.set_http_header("Content-Disposition", "Attachment; filename=%s" % file_name)

        preview_filepath = os.path.join(self._job.get_work_dir(), file_name)
        html.write(file(preview_filepath).read())


cmk.gui.pages.register_page_handler("download_agent_output",
                                    lambda: PageDownloadAgentOutput().page())

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
def execute_network_scan_job():
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

    result = {
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
            found = watolib.do_network_scan(folder)
        else:
            found = watolib.do_remote_automation(
                config.site(folder.site_id()), "network-scan", [("folder", folder.path())])

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
        logger.error("Exception in network scan:\n%s" % (traceback.format_exc()))

    result["end"] = time.time()

    save_network_scan_result(folder, result)

    if old_user:
        config.set_user_by_id(old_user)


# Find the folder which network scan is longest waiting and return the
# folder object.
def find_folder_to_scan():
    folder_to_scan = None
    for folder in watolib.Folder.all_folders().itervalues():
        scheduled_time = folder.next_network_scan_at()
        if scheduled_time is not None and scheduled_time < time.time():
            if folder_to_scan is None:
                folder_to_scan = folder
            elif folder_to_scan.next_network_scan_at() > folder.next_network_scan_at():
                folder_to_scan = folder
    return folder_to_scan


def add_scanned_hosts_to_folder(folder, found):
    network_scan_properties = folder.attribute("network_scan")

    translation = network_scan_properties.get("translate_names", {})

    entries = []
    for host_name, ipaddress in found:
        host_name = cmk.translations.translate_hostname(translation, host_name)

        attrs = {}
        if "tag_criticality" in network_scan_properties:
            attrs["tag_criticality"] = network_scan_properties.get("tag_criticality", "offline")

        if network_scan_properties.get("set_ipaddress", True):
            attrs["ipaddress"] = ipaddress

        if not watolib.Host.host_exists(host_name):
            entries.append((host_name, attrs, None))

    watolib.lock_exclusive()
    folder.create_hosts(entries)
    folder.save()
    watolib.unlock_exclusive()


def save_network_scan_result(folder, result):
    # Reload the folder, lock WATO before to protect against concurrency problems.
    watolib.lock_exclusive()

    # A user might have changed the folder somehow since starting the scan. Load the
    # folder again to get the current state.
    write_folder = watolib.Folder.folder(folder.path())
    write_folder.set_attribute("network_scan_result", result)
    write_folder.save()

    watolib.unlock_exclusive()


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
# TODO: Drop this and probably replace with a hook at button rendering?
extra_buttons = []

loaded_with_language = False


def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == cmk.gui.i18n.get_current_language() and not force:
        return

    # Reset global vars
    del extra_buttons[:]

    # Initialize watolib things which are needed before loading the WATO plugins.
    # This also loads the watolib plugins.
    watolib.load_watolib_plugins()

    config.declare_permission(
        "wato.use",
        _("Use WATO"),
        _("This permissions allows users to use WATO - Check_MK's "
          "Web Administration Tool. Without this "
          "permission all references to WATO (buttons, links, "
          "snapins) will be invisible."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.edit",
        _("Make changes, perform actions"),
        _("This permission is needed in order to make any "
          "changes or perform any actions at all. "
          "Without this permission, the user is only "
          "able to view data, and that only in modules he "
          "has explicit permissions for."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.seeall",
        _("Read access to all modules"),
        _("When this permission is set then the user sees "
          "also such modules he has no explicit "
          "access to (see below)."),
        ["admin"],
    )

    config.declare_permission(
        "wato.activate",
        _("Activate Configuration"),
        _("This permission is needed for activating the "
          "current configuration (and thus rewriting the "
          "monitoring configuration and restart the monitoring daemon.)"),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.activateforeign",
        _("Activate Foreign Changes"),
        _("When several users work in parallel with WATO then "
          "several pending changes of different users might pile up "
          "before changes are activate. Only with this permission "
          "a user will be allowed to activate the current configuration "
          "if this situation appears."),
        ["admin"],
    )

    config.declare_permission(
        "wato.auditlog",
        _("Audit Log"),
        _("Access to the historic audit log. "
          "The currently pending changes can be seen by all users "
          "with access to WATO."),
        ["admin"],
    )

    config.declare_permission(
        "wato.clear_auditlog",
        _("Clear audit Log"),
        _("Clear the entries of the audit log. To be able to clear the audit log "
          "a user needs the generic WATO permission \"Make changes, perform actions\", "
          "the \"View audit log\" and this permission."),
        ["admin"],
    )

    config.declare_permission(
        "wato.hosts",
        _("Host management"),
        _("Access to the management of hosts and folders. This "
          "module has some additional permissions (see below)."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.edit_hosts",
        _("Modify existing hosts"),
        _("Modify the properties of existing hosts. Please note: "
          "for the management of services (inventory) there is "
          "a separate permission (see below)"),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.parentscan",
        _("Perform network parent scan"),
        _("This permission is neccessary for performing automatic "
          "scans for network parents of hosts (making use of traceroute). "
          "Please note, that for actually modifying the parents via the "
          "scan and for the creation of gateway hosts proper permissions "
          "for host and folders are also neccessary."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.move_hosts",
        _("Move existing hosts"),
        _("Move existing hosts to other folders. Please also add the permission "
          "<i>Modify existing hosts</i>."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.rename_hosts",
        _("Rename existing hosts"),
        _("Rename existing hosts. Please also add the permission "
          "<i>Modify existing hosts</i>."),
        ["admin"],
    )

    config.declare_permission(
        "wato.manage_hosts",
        _("Add & remove hosts"),
        _("Add hosts to the monitoring and remove hosts "
          "from the monitoring. Please also add the permission "
          "<i>Modify existing hosts</i>."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.diag_host",
        _("Host Diagnostic"),
        _("Check whether or not the host is reachable, test the different methods "
          "a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out "
          "the correct monitoring configuration for that host."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.clone_hosts",
        _("Clone hosts"),
        _("Clone existing hosts to create new ones from the existing one."
          "Please also add the permission <i>Add & remove hosts</i>."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.random_hosts",
        _("Create random hosts"),
        _("The creation of random hosts is a facility for test and development "
          "and disabled by default. It allows you to create a number of random "
          "hosts and thus simulate larger environments."),
        [],
    )

    config.declare_permission(
        "wato.update_dns_cache",
        _("Update DNS Cache"),
        _("Updating the DNS cache is neccessary in order to reflect IP address "
          "changes in hosts that are configured without an explicit address."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.services",
        _("Manage services"),
        _("Do inventory and service configuration on existing hosts."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.edit_folders",
        _("Modify existing folders"),
        _("Modify the properties of existing folders."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.manage_folders",
        _("Add & remove folders"),
        _("Add new folders and delete existing folders. If a folder to be deleted contains hosts then "
          "the permission to delete hosts is also required."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.passwords",
        _("Password management"),
        _("This permission is needed for the module <i>Passwords</i>."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.edit_all_passwords",
        _("Write access to all passwords"),
        _("Without this permission, users can only edit passwords which are shared with a contact "
          "group they are member of. This permission grants full access to all passwords."),
        ["admin"],
    )

    config.declare_permission(
        "wato.see_all_folders",
        _("Read access to all hosts and folders"),
        _("Users without this permissions can only see folders with a contact group they are in."),
        ["admin"],
    )

    config.declare_permission(
        "wato.all_folders",
        _("Write access to all hosts and folders"),
        _("Without this permission, operations on folders can only be done by users that are members of "
          "one of the folders contact groups. This permission grants full access to all folders and hosts."
         ),
        ["admin"],
    )

    config.declare_permission(
        "wato.hosttags",
        _("Manage host tags"),
        _("Create, remove and edit host tags. Removing host tags also might remove rules, "
          "so this permission should not be available to normal users. "),
        ["admin"],
    )

    config.declare_permission(
        "wato.global",
        _("Global settings"),
        _("Access to the module <i>Global settings</i>"),
        ["admin"],
    )

    config.declare_permission(
        "wato.rulesets",
        _("Rulesets"),
        _("Access to the module for managing Check_MK rules. Please note that a user can only "
          "manage rules in folders he has permissions to. "),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.groups",
        _("Host & Service Groups"),
        _("Access to the modules for managing host and service groups."),
        ["admin"],
    )

    config.declare_permission(
        "wato.timeperiods",
        _("Timeperiods"),
        _("Access to the module <i>Timeperiods</i>"),
        ["admin"],
    )

    config.declare_permission(
        "wato.sites",
        _("Site management"),
        _("Access to the module for managing connections to remote monitoring sites."),
        ["admin"],
    )

    config.declare_permission(
        "wato.automation",
        _("Site remote automation"),
        _("This permission is needed for a remote administration of the site "
          "as a distributed WATO slave."),
        ["admin"],
    )

    config.declare_permission(
        "wato.users",
        _("User management"),
        _("This permission is needed for the modules <b>Users</b>, <b>Roles</b> and <b>Contact Groups</b>"
         ),
        ["admin"],
    )

    config.declare_permission(
        "wato.notifications",
        _("Notification configuration"),
        _("This permission is needed for the new rule based notification configuration via the WATO module <i>Notifications</i>."
         ),
        ["admin"],
    )

    config.declare_permission(
        "wato.snapshots",
        _("Manage snapshots"),
        _("Access to the module <i>Snaphsots</i>. Please note: a user with "
          "write access to this module "
          "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
        ["admin"],
    )

    config.declare_permission(
        "wato.backups",
        _("Backup & Restore"),
        _("Access to the module <i>Site backup</i>. Please note: a user with "
          "write access to this module "
          "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
        ["admin"],
    )

    config.declare_permission(
        "wato.pattern_editor",
        _("Logfile Pattern Analyzer"),
        _("Access to the module for analyzing and validating logfile patterns."),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.icons",
        _("Manage Custom Icons"),
        _("Upload or delete custom icons"),
        ["admin"],
    )

    config.declare_permission(
        "wato.custom_attributes",
        _("Manage custom attributes"),
        _("Manage custom host- and user attributes"),
        ["admin"],
    )

    config.declare_permission(
        "wato.download_agents",
        _("Monitoring Agents"),
        _("Download the default Check_MK monitoring agents for Linux, "
          "Windows and other operating systems."),
        ["admin", "user", "guest"],
    )

    config.declare_permission(
        "wato.download_agent_output",
        _("Download Agent Output / SNMP Walks"),
        _("Allows to download the current agent output or SNMP walks of the monitored hosts."),
        ["admin"],
    )

    config.declare_permission(
        "wato.set_read_only",
        _("Set WATO to read only mode for other users"),
        _("Prevent other users from making modifications to WATO."),
        ["admin"],
    )

    config.declare_permission(
        "wato.analyze_config",
        _("Access the best analyze configuration functionality provided by WATO"),
        _("WATO has a module that gives you hints on how to tune your Check_MK installation."),
        ["admin"],
    )

    config.declare_permission(
        "wato.add_or_modify_executables",
        _("Can add or modify executables"),
        _("There are different places in Check_MK where an admin can use the GUI to add "
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
        ["admin"],
    )

    config.declare_permission(
        "wato.service_discovery_to_undecided",
        _("Service discovery: Move to undecided services"),
        _("Service discovery: Move to undecided services"),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.service_discovery_to_monitored",
        _("Service discovery: Move to monitored services"),
        _("Service discovery: Move to monitored services"),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.service_discovery_to_ignored",
        _("Service discovery: Disabled services"),
        _("Service discovery: Disabled services"),
        ["admin", "user"],
    )

    config.declare_permission(
        "wato.service_discovery_to_removed",
        _("Service discovery: Remove services"),
        _("Service discovery: Remove services"),
        ["admin", "user"],
    )

    utils.load_web_plugins("wato", globals())

    if modes:
        raise MKGeneralException(
            _("Deprecated WATO modes found: %r. "
              "They need to be refactored to new API.") % modes.keys())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()
