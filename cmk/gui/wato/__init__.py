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
import cmk.gui.plugin_registry
import cmk.gui.view_utils
import cmk.gui.plugins.wato.utils
import cmk.gui.plugins.wato.utils.base_modes
import cmk.gui.wato.mkeventd
from cmk.gui.i18n import _u, _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKGeneralException, MKUserError, MKAuthException, \
                           MKInternalError, MKException
from cmk.gui.log import logger
from cmk.gui.display_options import display_options
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, WatoWebApiMode

from cmk.gui.wato.pages.activate_changes import (
    ModeActivateChanges,
    ModeAjaxStartActivation,
    ModeAjaxActivationState
)
from cmk.gui.wato.pages.analyze_configuration import ModeAnalyzeConfig
from cmk.gui.wato.pages.audit_log import ModeAuditLog
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
    ModeEditSiteGlobalSetting
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
    ModeAjaxExecuteCheck
)
from cmk.gui.wato.pages.sites import (
    ModeSites,
    ModeEditSite,
    ModeDistributedMonitoring,
    ModeEditSiteGlobals
)
from cmk.gui.wato.pages.timeperiods import (
    ModeTimeperiods,
    ModeTimeperiodImportICal,
    ModeEditTimeperiod
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
from cmk.gui.valuespec import * # pylint: disable=wildcard-import
syslog_facilities = cmk.gui.mkeventd.syslog_facilities
ALL_HOSTS         = watolib.ALL_HOSTS
ALL_SERVICES      = watolib.ALL_SERVICES
NEGATE            = watolib.NEGATE
NO_ITEM           = watolib.NO_ITEM
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
)

# Make some functions of watolib available to WATO plugins without using the
# watolib module name. This is mainly done for compatibility reasons to keep
# the current plugin API functions working
from cmk.gui.watolib import (
    PasswordStore,
    TimeperiodSelection,
    register_rulegroup,
    register_rule,
    register_configvar,
    register_configvar_group,
    register_hook,
    add_replication_paths,
    UserSelection,
    ConfigDomainGUI,
    ConfigDomainCore,
    ConfigDomainOMD,
    ConfigDomainEventConsole,
    configvar_order,
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
    WatoModule,
    register_modules,
    get_modules,
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
        raise MKGeneralException(_("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
                                   " in your <tt>multisite.mk</tt> if you want to use WATO."))

    if cmk.is_managed_edition() and not managed.is_provider(config.current_customer):
        raise MKGeneralException(_("Check_MK can only be configured on "
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
    if mode_permissions != None and not config.user.may("wato.seeall"):
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
            if type(result) == tuple:
                newmode, action_message = result
            else:
                newmode = result

            # If newmode is False, then we shall immediately abort.
            # This is e.g. the case, if the page outputted non-HTML
            # data, such as a tarball (in the export function). We must
            # be sure not to output *any* further data in that case.
            if newmode == False:
                return

            # if newmode is not None, then the mode has been changed
            elif newmode != None:
                if newmode == "": # no further information: configuration dialog, etc.
                    if action_message:
                        html.message(action_message)
                        wato_html_footer()
                    return
                mode_permissions, mode_class = get_mode_permission_and_class(newmode)
                current_mode = newmode
                mode = mode_class()
                html.set_var("mode", newmode) # will be used by makeuri

                # Check general permissions for the new mode
                if mode_permissions != None and not config.user.may("wato.seeall"):
                    for pname in mode_permissions:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.user.need_permission(pname)

        except MKUserError, e:
            action_message = "%s" % e
            html.add_user_error(e.varname, action_message)

        except MKAuthException, e:
            action_message = e.reason
            html.add_user_error(None, e.reason)

    wato_html_head(mode.title(),
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
                    html.context_button(buttontext, watolib.folder_preserving_link([("mode", target)]))
        html.end_context_buttons()

    if not html.is_transaction() or (watolib.is_read_only_mode_enabled() and watolib.may_override_read_only_mode()):
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

    wato_html_footer(display_options.enabled(display_options.Z),
                     display_options.enabled(display_options.H))


def get_mode_permission_and_class(mode_name):
    mode_class = mode_registry.get(mode_name, ModeNotImplemented)
    mode_permissions = mode_class.permissions()

    if mode_class is None:
        raise MKGeneralException(_("No such WATO module '<tt>%s</tt>'") % mode_name)

    if type(mode_class) == type(lambda: None):
        raise MKGeneralException(_("Deprecated WATO module: Implemented as function. "
                                   "This needs to be refactored as WatoMode child class."))

    if mode_permissions != None and not config.user.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    return mode_permissions, mode_class


def ensure_mode_permissions(mode_permissions):
    for pname in mode_permissions:
        if '.' not in pname:
            pname = "wato." + pname
        config.user.need_permission(pname)



@mode_registry.register
class ModeNotImplemented(WatoMode):
    @classmethod
    def name(cls):
        return ""


    @classmethod
    def permissions(cls):
        return []


    def title(self):
        return _("Sorry")


    def buttons(self):
        home_button()


    def page(self):
        html.show_error(_("This module has not yet been implemented."))


def _show_read_only_warning():
    if watolib.is_read_only_mode_enabled():
        html.show_warning(watolib.read_only_message())


#.
#   .--Automation-Webservice-----------------------------------------------.
#   |          _         _                        _   _                    |
#   |         / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __         |
#   |        / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \        |
#   |       / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |       |
#   |      /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | These function implement a web service with that a master can call   |
#   | automation functions on slaves.                                      |
#   '----------------------------------------------------------------------'

class ModeAutomationLogin(WatoWebApiMode):
    """Is executed by the central Check_MK site during creation of the WATO master/slave sync to

    When the page method is execute a remote (master) site has successfully
    logged in using valid credentials of an administrative user. The login is
    done be exchanging a login secret. If such a secret is not yet present it
    is created on the fly."""
    def page(self):
        if not config.user.may("wato.automation"):
            raise MKAuthException(_("This account has no permission for automation."))

        html.set_output_format("python")
        html.write_html(repr(watolib.get_login_secret(True)))



class ModeAutomation(WatoWebApiMode):
    """Executes the requested automation call

    This page is accessible without regular login. The request is authenticated using the given
    login secret that has previously been exchanged during "site login" (see above).
    """

    def __init__(self):
        super(ModeAutomation, self).__init__()

        # The automation page is accessed unauthenticated. After leaving the index.py area
        # into the page handler we always want to have a user context initialized to keep
        # the code free from special cases (if no user logged in, then...). So fake the
        # logged in user here.
        config.set_super_user()

        # To prevent mixups in written files we use the same lock here as for
        # the normal WATO page processing. This might not be needed for some
        # special automation requests, like inventory e.g., but to keep it simple,
        # we request the lock in all cases.
        watolib.lock_exclusive()

        init_wato_datastructures(with_wato_lock=False)


    def _from_vars(self):
        self._authenticate()
        self._command = html.var("command")


    def _authenticate(self):
        secret = html.var("secret")

        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if secret != watolib.get_login_secret():
            raise MKAuthException(_("Invalid automation secret."))


    def page(self):
        if self._command == "checkmk-automation":
            self._execute_cmk_automation()

        elif self._command == "push-profile":
            self._execute_push_profile()

        elif watolib.automation_command_exists(self._command):
            self._execute_automation_command()

        else:
            raise MKGeneralException(_("Invalid automation command: %s.") % self._command)


    def _execute_cmk_automation(self):
        cmk_command = html.var("automation")
        args        = watolib.mk_eval(html.var("arguments"))
        indata      = watolib.mk_eval(html.var("indata"))
        stdin_data  = watolib.mk_eval(html.var("stdin_data"))
        timeout     = watolib.mk_eval(html.var("timeout"))
        result = watolib.check_mk_local_automation(cmk_command, args, indata, stdin_data, timeout)
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        html.write(repr(result))


    def _execute_push_profile(self):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(watolib.mk_repr(self._automation_push_profile()))
        except Exception, e:
            logger.exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))


    def _automation_push_profile(self):
        site_id = html.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        user_id = html.var("user_id")
        if not user_id:
            raise MKGeneralException(_("Missing variable user_id"))

        our_id = config.omd_site()

        if our_id != None and our_id != site_id:
            raise MKGeneralException(
              _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        profile = html.var("profile")
        if not profile:
            raise MKGeneralException(_('Invalid call: The profile is missing.'))

        users = userdb.load_users(lock = True)
        profile = watolib.mk_eval(profile)
        users[user_id] = profile
        userdb.save_users(users)

        return True


    def _execute_automation_command(self):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(repr(watolib.execute_automation_command(self._command)))
        except Exception, e:
            logger.exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % \
                            (e, traceback.format_exc()))


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
        if ty not in [ "walk", "agent" ]:
            raise MKGeneralException(_("Invalid type specified."))
        self._ty = ty

        self._back_url = html.get_url_input("back_url")

        init_wato_datastructures(with_wato_lock=True)

        host = watolib.Folder.current().host(host_name)
        if not host:
            raise MKGeneralException(_("Host is not managed by WATO. "
                "Click <a href=\"%s\">here</a> to go back.") %
                    html.escape_attribute(self._back_url))
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
        html.header(_("%s: Download agent output") % self._host.name(),
                    stylesheets=["status", "pages"])

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
            html.response.http_redirect(html.makeuri_contextless([
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



@gui_background_job.job_registry.register
class FetchAgentOutputBackgroundJob(WatoBackgroundJob):
    job_prefix = "agent-output-"
    gui_title  = _("Fetch agent output")

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

        preview_filepath = os.path.join(job_interface.get_work_dir(),
                                        AgentOutputPage.file_name(self._site_id, self._host_name, self._ty))
        store.save_file(preview_filepath, agent_data)

        download_url = html.makeuri_contextless([
            ("host", self._host_name),
            ("type", self._ty)
        ], filename="download_agent_output.py")

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
        return # Don't execute this job on slaves.

    folder = find_folder_to_scan()
    if not folder:
        return # Nothing to do.

    # We need to have the context of the user. The jobs are executed when
    # config.set_user_by_id() has not been executed yet. So there is no user context
    # available. Use the run_as attribute from the job config and revert
    # the previous state after completion.
    old_user = config.user.id
    run_as = folder.attribute("network_scan")["run_as"]
    if not userdb.user_exists(run_as):
        raise MKGeneralException(_("The user %s used by the network "
            "scan of the folder %s does not exist.") % (run_as, folder.title()))
    config.set_user_by_id(folder.attribute("network_scan")["run_as"])

    result = {
        "start"  : time.time(),
        "end"    : True, # means currently running
        "state"  : None,
        "output" : "The scan is currently running.",
    }

    # Mark the scan in progress: Is important in case the request takes longer than
    # the interval of the cron job (1 minute). Otherwise the scan might be started
    # a second time before the first one finished.
    save_network_scan_result(folder, result)

    try:
        if config.site_is_local(folder.site_id()):
            found = watolib.do_network_scan(folder)
        else:
            found = watolib.do_remote_automation(config.site(folder.site_id()), "network-scan",
                                          [("folder", folder.path())])

        if type(found) != list:
            raise MKGeneralException(_("Received an invalid network scan result: %r") % found)

        add_scanned_hosts_to_folder(folder, found)

        result.update({
            "state"  : True,
            "output" : _("The network scan found %d new hosts.") % len(found),
        })
    except Exception, e:
        result.update({
            "state"  : False,
            "output" : _("An exception occured: %s") % e,
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
        if scheduled_time != None and scheduled_time < time.time():
            if folder_to_scan == None:
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
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Functions needed at various places                                   |
#   '----------------------------------------------------------------------'

# Show HTML form for editing attributes.
#
# new: Boolean flag if this is a creation step or editing
# for_what can be:
#   "host"        -> normal host edit dialog
#   "cluster"     -> normal host edit dialog
#   "folder"      -> properties of folder or file
#   "host_search" -> host search dialog
#   "bulk"        -> bulk change
# parent: The parent folder of the objects to configure
# myself: For mode "folder" the folder itself or None, if we edit a new folder
#         This is needed for handling mandatory attributes.
def configure_attributes(new, hosts, for_what, parent, myself=None, without_attributes=None, varprefix=""):
    if without_attributes is None:
        without_attributes = []

    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    # Make sure, that the topics "Basic settings" and host tags
    # are always show first.
    # TODO: Clean this up! Implement some explicit sorting
    topics = [None]
    if config.host_tag_groups():
        topics.append(_("Address"))
        topics.append(_("Data sources"))
        topics.append(_("Host tags"))

    # The remaining topics are shown in the order of the
    # appearance of the attribute declarations:
    for attr, topic in watolib.all_host_attributes():
        if topic not in topics and attr.is_visible(for_what):
            topics.append(topic)

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags     = {}

    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a, b):
        if a[0].name() == "tag_address_family":
            return -1
        return 0

    volatile_topics = []
    hide_attributes = []
    for topic in topics:
        topic_is_volatile = True # assume topic is sometimes hidden due to dependencies
        if len(topics) > 1:
            if topic == None:
                title = _("Basic settings")
            else:
                title = _u(topic)

            if topic == _("Host tags"):
                topic_id = "wato_host_tags"
            elif topic == _("Address"):
                topic_id = "address"
            elif topic == _("Data sources"):
                topic_id = "data_sources"
            else:
                topic_id = None

            forms.header(title, isopen = topic in [ None, _("Address"), _("Data sources") ], table_id = topic_id)

        for attr, atopic in sorted(watolib.all_host_attributes(), cmp=sort_host_attributes):
            if atopic != topic:
                continue

            attrname = attr.name()
            if attrname in without_attributes:
                continue # e.g. needed to skip ipaddress in CSV-Import

            # Determine visibility information if this attribute is not always hidden
            if attr.is_visible(for_what):
                depends_on_tags = attr.depends_on_tags()
                depends_on_roles = attr.depends_on_roles()
                # Add host tag dependencies, but only in host mode. In other
                # modes we always need to show all attributes.
                if for_what in [ "host", "cluster" ] and depends_on_tags:
                    dependency_mapping_tags[attrname] = depends_on_tags

                if depends_on_roles:
                    dependency_mapping_roles[attrname] = depends_on_roles

                if for_what not in [ "host", "cluster" ]:
                    topic_is_volatile = False

                elif not depends_on_tags and not depends_on_roles:
                    # One attribute is always shown -> topic is always visible
                    topic_is_volatile = False
            else:
                hide_attributes.append(attr.name())

            # "bulk": determine, if this attribute has the same setting for all hosts.
            values = []
            num_haveit = 0
            for host in hosts.itervalues():
                if host and host.has_explicit_attribute(attrname):
                    num_haveit += 1
                    if host.attribute(attrname) not in values:
                        values.append(host.attribute(attrname))

            # The value of this attribute is unique amongst all hosts if
            # either no host has a value for this attribute, or all have
            # one and have the same value
            unique = num_haveit == 0 or (len(values) == 1 and num_haveit == len(hosts))

            if for_what in [ "host", "cluster", "folder" ]:
                if hosts:
                    host = hosts.values()[0]
                else:
                    host = None

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "host_search" mode.
            inherited_from = None
            inherited_value = None
            has_inherited = False
            container = None

            if attr.show_inherited_value():
                if for_what in [ "host", "cluster" ]:
                    url = watolib.Folder.current().edit_url()

                container = parent # container is of type Folder
                while container:
                    if attrname in container.attributes():
                        url = container.edit_url()
                        inherited_from = _("Inherited from ") + html.render_a(container.title(), href=url)

                        inherited_value = container.attributes()[attrname]
                        has_inherited = True
                        if isinstance(attr, watolib.HostTagAttribute):
                            inherited_tags["attr_%s" % attrname] = '|'.join(attr.get_tag_list(inherited_value))
                        break

                    container = container.parent()

            if not container: # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
                inherited_value = attr.default_value()
                # Also add the default values to the inherited values dict
                if isinstance(attr, watolib.HostTagAttribute):
                    inherited_tags["attr_%s" % attrname] = '|'.join(attr.get_tag_list(inherited_value))

            # Checkbox for activating this attribute

            # Determine current state of visibility: If the form has already been submitted (i.e. search
            # or input error), then we take the previous state of the box. In search mode we make those
            # boxes active that have an empty string as default value (simple text boxed). In bulk
            # mode we make those attributes active that have an explicitely set value over all hosts.
            # In host and folder mode we make those attributes active that are currently set.

            # Also determine, if the attribute can be switched off at all. Problematic here are
            # mandatory attributes. We must make sure, that at least one folder/file/host in the
            # chain defines an explicit value for that attribute. If we show a host and no folder/file
            # inherits an attribute to that host, the checkbox will be always active and locked.
            # The same is the case if we show a file/folder and at least one host below this
            # has not set that attribute. In case of bulk edit we never lock: During bulk edit no
            # attribute ca be removed anyway.

            checkbox_name = for_what + "_change_%s" % attrname
            cb = html.get_checkbox(checkbox_name)
            force_entry = False
            disabled = False

            # first handle mandatory cases
            if for_what == "folder" and attr.is_mandatory() \
                and myself \
                and some_host_hasnt_set(myself, attrname) \
                and not has_inherited:
                force_entry = True
                active = True
            elif for_what in [ "host", "cluster" ] and attr.is_mandatory() and not has_inherited:
                force_entry = True
                active = True
            elif cb != None:
                active = cb # get previous state of checkbox
            elif for_what == "bulk":
                active = unique and len(values) > 0
            elif for_what == "folder" and myself:
                active = myself.has_explicit_attribute(attrname)
            elif for_what in [ "host", "cluster" ] and host: # "host"
                active = host.has_explicit_attribute(attrname)
            else:
                active = False

            if not new and (not attr.editable() or not attr.may_edit()):
                # Bug in pylint 1.9.2 https://github.com/PyCQA/pylint/issues/1984, already fixed in master.
                if active:  # pylint: disable=simplifiable-if-statement
                    force_entry = True
                else:
                    disabled = True

            if (for_what in [ "host", "cluster" ] and parent.locked_hosts()) or (for_what == "folder" and myself and myself.locked()):
                checkbox_code = None
            elif force_entry:
                checkbox_code  = html.render_checkbox("ignored_" + checkbox_name, add_attr=["disabled"])
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                add_attr = ["disabled"] if disabled else []
                onclick = "wato_fix_visibility(); wato_toggle_attribute(this, '%s');" % attrname
                checkbox_code = html.render_checkbox(checkbox_name, active,
                                                  onclick=onclick, add_attr=add_attr)

            forms.section(_u(attr.title()), checkbox=checkbox_code, section_id="attr_" + attrname)
            html.help(attr.help())

            if len(values) == 1:
                defvalue = values[0]
            elif attr.is_checkbox_tag():
                defvalue = True
            else:
                defvalue = attr.default_value()

            if not new and (not attr.editable() or not attr.may_edit()):
                # In edit mode only display non editable values, don't show the
                # input fields
                html.open_div(id_="attr_hidden_%s" %attrname, style="display:none;")
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(id_="attr_visible_%s" % attrname, class_=["inherited"])

            else:
                # Now comes the input fields and the inherited / default values
                # as two DIV elements, one of which is visible at one time.

                # DIV with the input elements
                html.open_div(id_="attr_entry_%s" % attrname, style="display: none;" if not active else None)
                attr.render_input(varprefix, defvalue)
                html.close_div()

                html.open_div(class_="inherited", id_="attr_default_%s" % attrname,
                              style="display: none;" if active else None)

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation = u""
            if for_what == "bulk":
                if num_haveit == 0:
                    explanation = u" (%s)" % inherited_from
                    value = inherited_value
                elif not unique:
                    explanation = _("This value differs between the selected hosts.")
                else:
                    value = values[0]

            elif for_what in [ "host", "cluster", "folder" ]:
                if not new and (not attr.editable() or not attr.may_edit()) and active:
                    value = values[0]
                else:
                    explanation = " (" + inherited_from + ")"
                    value = inherited_value

            if for_what != "host_search" and not (for_what == "bulk" and not unique):
                _tdclass, content = attr.paint(value, "")
                if not content:
                    content = _("empty")

                if isinstance(attr, ValueSpecAttribute):
                    html.open_b()
                    html.write(content)
                    html.close_b()
                else:
                    html.b(_u(content))

            html.write_text(explanation)
            html.close_div()


        if len(topics) > 1:
            if topic_is_volatile:
                volatile_topics.append((topic or _("Basic settings")).encode('utf-8'))

    forms.end()
    # Provide Javascript world with the tag dependency information
    # of all attributes.
    html.javascript("var inherited_tags = %s;\n"\
                    "var wato_check_attributes = %s;\n"\
                    "var wato_depends_on_tags = %s;\n"\
                    "var wato_depends_on_roles = %s;\n"\
                    "var volatile_topics = %s;\n"\
                    "var user_roles = %s;\n"\
                    "var hide_attributes = %s;\n"\
                    "wato_fix_visibility();\n" % (
                       json.dumps(inherited_tags),
                       json.dumps(list(set(dependency_mapping_tags.keys()+dependency_mapping_roles.keys()+hide_attributes))),
                       json.dumps(dependency_mapping_tags),
                       json.dumps(dependency_mapping_roles),
                       json.dumps(volatile_topics),
                       json.dumps(config.user.role_ids),
                       json.dumps(hide_attributes)))


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder.all_subfolders().values():
        # If the attribute is not set in the subfolder, we need
        # to check all hosts and that folder.
        if attrname not in subfolder.attributes() \
            and some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    for host in folder.hosts().values():
        if not host.has_explicit_attribute(attrname):
            return True

    return False


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

    # Declare WATO-specific permissions
    config.declare_permission_section("wato", _("WATO - Check_MK's Web Administration Tool"))

    config.declare_permission("wato.use",
         _("Use WATO"),
         _("This permissions allows users to use WATO - Check_MK's "
           "Web Administration Tool. Without this "
           "permission all references to WATO (buttons, links, "
           "snapins) will be invisible."),
         [ "admin", "user" ])

    config.declare_permission("wato.edit",
         _("Make changes, perform actions"),
         _("This permission is needed in order to make any "
           "changes or perform any actions at all. "
           "Without this permission, the user is only "
           "able to view data, and that only in modules he "
           "has explicit permissions for."),
         [ "admin", "user" ])

    config.declare_permission("wato.seeall",
         _("Read access to all modules"),
         _("When this permission is set then the user sees "
           "also such modules he has no explicit "
           "access to (see below)."),
         [ "admin", ])

    config.declare_permission("wato.activate",
         _("Activate Configuration"),
         _("This permission is needed for activating the "
           "current configuration (and thus rewriting the "
           "monitoring configuration and restart the monitoring daemon.)"),
         [ "admin", "user", ])

    config.declare_permission("wato.activateforeign",
         _("Activate Foreign Changes"),
         _("When several users work in parallel with WATO then "
           "several pending changes of different users might pile up "
           "before changes are activate. Only with this permission "
           "a user will be allowed to activate the current configuration "
           "if this situation appears."),
         [ "admin", ])

    config.declare_permission("wato.auditlog",
         _("Audit Log"),
         _("Access to the historic audit log. "
           "The currently pending changes can be seen by all users "
           "with access to WATO."),
         [ "admin", ])

    config.declare_permission("wato.clear_auditlog",
         _("Clear audit Log"),
         _("Clear the entries of the audit log. To be able to clear the audit log "
           "a user needs the generic WATO permission \"Make changes, perform actions\", "
           "the \"View audit log\" and this permission."),
         [ "admin", ])

    config.declare_permission("wato.hosts",
         _("Host management"),
         _("Access to the management of hosts and folders. This "
           "module has some additional permissions (see below)."),
         [ "admin", "user" ])

    config.declare_permission("wato.edit_hosts",
         _("Modify existing hosts"),
         _("Modify the properties of existing hosts. Please note: "
           "for the management of services (inventory) there is "
           "a separate permission (see below)"),
         [ "admin", "user" ])

    config.declare_permission("wato.parentscan",
         _("Perform network parent scan"),
         _("This permission is neccessary for performing automatic "
           "scans for network parents of hosts (making use of traceroute). "
           "Please note, that for actually modifying the parents via the "
           "scan and for the creation of gateway hosts proper permissions "
           "for host and folders are also neccessary."),
         [ "admin", "user" ])

    config.declare_permission("wato.move_hosts",
         _("Move existing hosts"),
         _("Move existing hosts to other folders. Please also add the permission "
           "<i>Modify existing hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.rename_hosts",
         _("Rename existing hosts"),
         _("Rename existing hosts. Please also add the permission "
           "<i>Modify existing hosts</i>."),
         [ "admin" ])

    config.declare_permission("wato.manage_hosts",
         _("Add & remove hosts"),
         _("Add hosts to the monitoring and remove hosts "
           "from the monitoring. Please also add the permission "
           "<i>Modify existing hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.diag_host",
         _("Host Diagnostic"),
         _("Check whether or not the host is reachable, test the different methods "
           "a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out "
           "the correct monitoring configuration for that host."),
         [ "admin", "user" ])


    config.declare_permission("wato.clone_hosts",
         _("Clone hosts"),
         _("Clone existing hosts to create new ones from the existing one."
           "Please also add the permission <i>Add & remove hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.random_hosts",
         _("Create random hosts"),
         _("The creation of random hosts is a facility for test and development "
           "and disabled by default. It allows you to create a number of random "
           "hosts and thus simulate larger environments."),
         [ ])

    config.declare_permission("wato.update_dns_cache",
         _("Update DNS Cache"),
         _("Updating the DNS cache is neccessary in order to reflect IP address "
           "changes in hosts that are configured without an explicit address."),
         [ "admin", "user" ])

    config.declare_permission("wato.services",
         _("Manage services"),
         _("Do inventory and service configuration on existing hosts."),
         [ "admin", "user" ])

    config.declare_permission("wato.edit_folders",
         _("Modify existing folders"),
         _("Modify the properties of existing folders."),
         [ "admin", "user" ])

    config.declare_permission("wato.manage_folders",
         _("Add & remove folders"),
         _("Add new folders and delete existing folders. If a folder to be deleted contains hosts then "
           "the permission to delete hosts is also required."),
         [ "admin", "user" ])

    config.declare_permission("wato.passwords",
         _("Password management"),
         _("This permission is needed for the module <i>Passwords</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.edit_all_passwords",
         _("Write access to all passwords"),
         _("Without this permission, users can only edit passwords which are shared with a contact "
           "group they are member of. This permission grants full access to all passwords."),
         [ "admin" ])

    config.declare_permission("wato.see_all_folders",
         _("Read access to all hosts and folders"),
         _("Users without this permissions can only see folders with a contact group they are in."),
         [ "admin" ])

    config.declare_permission("wato.all_folders",
         _("Write access to all hosts and folders"),
         _("Without this permission, operations on folders can only be done by users that are members of "
           "one of the folders contact groups. This permission grants full access to all folders and hosts."),
         [ "admin" ])

    config.declare_permission("wato.hosttags",
         _("Manage host tags"),
         _("Create, remove and edit host tags. Removing host tags also might remove rules, "
           "so this permission should not be available to normal users. "),
         [ "admin" ])

    config.declare_permission("wato.global",
         _("Global settings"),
         _("Access to the module <i>Global settings</i>"),
         [ "admin", ])

    config.declare_permission("wato.rulesets",
         _("Rulesets"),
         _("Access to the module for managing Check_MK rules. Please note that a user can only "
           "manage rules in folders he has permissions to. "),
         [ "admin", "user" ])

    config.declare_permission("wato.groups",
         _("Host & Service Groups"),
         _("Access to the modules for managing host and service groups."),
         [ "admin", ])

    config.declare_permission("wato.timeperiods",
         _("Timeperiods"),
         _("Access to the module <i>Timeperiods</i>"),
         [ "admin", ])

    config.declare_permission("wato.sites",
         _("Site management"),
         _("Access to the module for managing connections to remote monitoring sites."),
         [ "admin", ])

    config.declare_permission("wato.automation",
        _("Site remote automation"),
        _("This permission is needed for a remote administration of the site "
          "as a distributed WATO slave."),
        [ "admin", ])

    config.declare_permission("wato.users",
         _("User management"),
         _("This permission is needed for the modules <b>Users</b>, <b>Roles</b> and <b>Contact Groups</b>"),
         [ "admin", ])

    config.declare_permission("wato.notifications",
         _("Notification configuration"),
         _("This permission is needed for the new rule based notification configuration via the WATO module <i>Notifications</i>."),
         [ "admin", ])

    config.declare_permission("wato.snapshots",
         _("Manage snapshots"),
         _("Access to the module <i>Snaphsots</i>. Please note: a user with "
           "write access to this module "
           "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
         [ "admin", ])

    config.declare_permission("wato.backups",
         _("Backup & Restore"),
         _("Access to the module <i>Site backup</i>. Please note: a user with "
           "write access to this module "
           "can make arbitrary changes to the configuration by restoring uploaded snapshots."),
         [ "admin", ])

    config.declare_permission("wato.pattern_editor",
         _("Logfile Pattern Analyzer"),
         _("Access to the module for analyzing and validating logfile patterns."),
         [ "admin", "user" ])

    config.declare_permission("wato.icons",
         _("Manage Custom Icons"),
         _("Upload or delete custom icons"),
         [ "admin" ])

    config.declare_permission("wato.custom_attributes",
         _("Manage custom attributes"),
         _("Manage custom host- and user attributes"),
         [ "admin" ])

    config.declare_permission("wato.download_agents",
        _("Monitoring Agents"),
        _("Download the default Check_MK monitoring agents for Linux, "
          "Windows and other operating systems."),
       [ "admin", "user", "guest" ])

    config.declare_permission("wato.download_agent_output",
        _("Download Agent Output / SNMP Walks"),
        _("Allows to download the current agent output or SNMP walks of the monitored hosts."),
        [ "admin" ])

    config.declare_permission("wato.set_read_only",
        _("Set WATO to read only mode for other users"),
        _("Prevent other users from making modifications to WATO."),
        [ "admin" ])

    config.declare_permission("wato.analyze_config",
        _("Access the best analyze configuration functionality provided by WATO"),
        _("WATO has a module that gives you hints on how to tune your Check_MK installation."),
        [ "admin" ])

    config.declare_permission("wato.add_or_modify_executables",
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
        [ "admin" ])

    config.declare_permission("wato.service_discovery_to_undecided",
         _("Service discovery: Move to undecided services"),
         _("Service discovery: Move to undecided services"),
         [ "admin", "user" ])

    config.declare_permission("wato.service_discovery_to_monitored",
         _("Service discovery: Move to monitored services"),
         _("Service discovery: Move to monitored services"),
         [ "admin", "user" ])

    config.declare_permission("wato.service_discovery_to_ignored",
         _("Service discovery: Disabled services"),
         _("Service discovery: Disabled services"),
         [ "admin", "user" ])

    config.declare_permission("wato.service_discovery_to_removed",
         _("Service discovery: Remove services"),
         _("Service discovery: Remove services"),
         [ "admin", "user" ])

    utils.load_web_plugins("wato", globals())

    if modes:
        raise MKGeneralException(_("Deprecated WATO modes found: %r. "
            "They need to be refactored to new API.") % modes.keys())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = cmk.gui.i18n.get_current_language()


# TODO: Clean this up! We would like to use the cmk.gui.pages.register() decorator instead
# of this
_wato_pages = {
    "ajax_start_activation"     : lambda: ModeAjaxStartActivation().handle_page(),
    "ajax_activation_state"     : lambda: ModeAjaxActivationState().handle_page(),

    "automation_login"          : lambda: ModeAutomationLogin().page(),
    "noauth:automation"         : lambda: ModeAutomation().page(),
    "ajax_set_foldertree"       : lambda: ModeAjaxSetFoldertree().handle_page(),
    "wato_ajax_execute_check"   : lambda: ModeAjaxExecuteCheck().handle_page(),
    "fetch_agent_output"        : lambda: PageFetchAgentOutput().page(),
    "download_agent_output"     : lambda: PageDownloadAgentOutput().page(),
    "ajax_popup_move_to_folder" : lambda: ModeAjaxPopupMoveToFolder().page(),
}
for path, page_func in _wato_pages.items():
    cmk.gui.pages.register_page_handler(path, page_func)
