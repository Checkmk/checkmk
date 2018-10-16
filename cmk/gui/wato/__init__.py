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
from cmk.gui.valuespec import *
from cmk.gui.display_options import display_options
from cmk.gui.plugins.userdb.htpasswd import encrypt_password

from cmk.gui.plugins.wato.utils.base_modes import WatoMode, WatoWebApiMode
from cmk.gui.wato.pages.global_settings import GlobalSettingsMode, EditGlobalSettingMode
from cmk.gui.wato.pages.sites import ModeSites, ModeEditSite
from cmk.gui.wato.pages.password_store import ModePasswords, ModeEditPassword
from cmk.gui.wato.pages.audit_log import ModeAuditLog
from cmk.gui.wato.pages.custom_attributes import (
    ModeEditCustomAttr,
    ModeEditCustomUserAttr,
    ModeEditCustomHostAttr,
    ModeCustomAttrs,
    ModeCustomUserAttrs,
    ModeCustomHostAttrs,
)
from cmk.gui.wato.pages.timeperiods import ModeTimeperiods, ModeTimeperiodImportICal, ModeEditTimeperiod
from cmk.gui.wato.pages.analyze_configuration import ModeAnalyzeConfig
from cmk.gui.wato.pages.bulk_discovery import ModeBulkDiscovery
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
from cmk.gui.wato.pages.icons import ModeIcons
from cmk.gui.wato.pages.check_catalog import ModeCheckManPage, ModeCheckPlugins
from cmk.gui.wato.pages.host_tags import (
    ModeHostTags,
    ModeEditHosttagConfiguration,
    ModeEditAuxtag,
    ModeEditHosttagGroup,
)
from cmk.gui.wato.pages.roles import (
    ModeRoles,
    ModeEditRole,
    ModeRoleMatrix,
)
from cmk.gui.wato.pages.users import (
    ModeUsers,
    ModeEditUser,
    select_language,
)
from cmk.gui.wato.pages.notifications import (
    ModeNotifications,
    ModeUserNotifications,
    ModePersonalUserNotifications,
    ModeEditNotificationRule,
    ModeEditPersonalNotificationRule,
)
from cmk.gui.wato.pages.random_hosts import ModeRandomHosts
from cmk.gui.wato.pages.pattern_editor import ModePatternEditor
from cmk.gui.wato.pages.host_diagnose import ModeDiagHost
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
from cmk.gui.wato.pages.ldap import ModeLDAPConfig, ModeEditLDAPConnection

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


class RenameHostsBackgroundJob(WatoBackgroundJob):
    gui_title  = _("Host renaming")
    job_prefix = "rename-hosts"
    def __init__(self, title=None):
        if not title:
            title = _("Host renaming")

        kwargs = {}
        kwargs["title"]     = title
        kwargs["lock_wato"] = True
        kwargs["stoppable"] = False
        last_job_status = WatoBackgroundJob(self.job_prefix).get_status()
        if "duration" in last_job_status:
            kwargs["estimated_duration"] = last_job_status["duration"]

        super(RenameHostsBackgroundJob, self).__init__(self.job_prefix, **kwargs)

        if self.is_running():
            raise MKGeneralException(_("Another renaming operation is currently in progress"))


    def _back_url(self):
        return html.makeuri([])



class RenameHostBackgroundJob(RenameHostsBackgroundJob):
    def __init__(self, host, title=None):
        super(RenameHostBackgroundJob, self).__init__(title)
        self._host = host


    def _back_url(self):
        return self._host.folder().url()


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
        show_read_only_warning()

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


#.
#   .--Folders-------------------------------------------------------------.
#   |                   _____     _     _                                  |
#   |                  |  ___|__ | | __| | ___ _ __ ___                    |
#   |                  | |_ / _ \| |/ _` |/ _ \ '__/ __|                   |
#   |                  |  _| (_) | | (_| |  __/ |  \__ \                   |
#   |                  |_|  \___/|_|\__,_|\___|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for showing a folder, bulk actions on hosts.                    |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeFolder(WatoMode):
    @classmethod
    def name(cls):
        return "folder"


    @classmethod
    def permissions(cls):
        return ["hosts"]


    def __init__(self):
        super(ModeFolder, self).__init__()
        self._folder = watolib.Folder.current()


    def title(self):
        return self._folder.title()


    def buttons(self):
        global_buttons()
        if self._folder.is_disk_folder():
            if config.user.may("wato.rulesets") or config.user.may("wato.seeall"):
                html.context_button(_("Rulesets"),        watolib.folder_preserving_link([("mode", "ruleeditor")]), "rulesets")
                html.context_button(_("Manual Checks"),   watolib.folder_preserving_link([("mode", "static_checks")]), "static_checks")
            if self._folder.may("read"):
                html.context_button(_("Folder Properties"), self._folder.edit_url(backfolder=self._folder), "edit")
            if not self._folder.locked_subfolders() and config.user.may("wato.manage_folders") and self._folder.may("write"):
                html.context_button(_("New folder"),        self._folder.url([("mode", "newfolder")]), "newfolder")
            if not self._folder.locked_hosts() and config.user.may("wato.manage_hosts") and self._folder.may("write"):
                html.context_button(_("New host"),    self._folder.url([("mode", "newhost")]), "new")
                html.context_button(_("New cluster"), self._folder.url([("mode", "newcluster")]), "new_cluster")
                html.context_button(_("Bulk import"), self._folder.url([("mode", "bulk_import")]), "bulk_import")
            if config.user.may("wato.services"):
                html.context_button(_("Bulk discovery"), self._folder.url([("mode", "bulkinventory"), ("all", "1")]),
                            "inventory")
            if config.user.may("wato.rename_hosts"):
                html.context_button(_("Bulk renaming"), self._folder.url([("mode", "bulk_rename_host")]), "rename_host")
            if config.user.may("wato.custom_attributes"):
                html.context_button(_("Custom attributes"), watolib.folder_preserving_link([("mode", "host_attrs")]), "custom_attr")
            if not self._folder.locked_hosts() and config.user.may("wato.parentscan") and self._folder.may("write"):
                html.context_button(_("Parent scan"), self._folder.url([("mode", "parentscan"), ("all", "1")]),
                            "parentscan")
            folder_status_button()
            if config.user.may("wato.random_hosts"):
                html.context_button(_("Random Hosts"), self._folder.url([("mode", "random_hosts")]), "random")
            html.context_button(_("Search"), watolib.folder_preserving_link([("mode", "search")]), "search")
        else:
            html.context_button(_("Back"), self._folder.parent().url(), "back")
            html.context_button(_("Refine Search"), self._folder.url([("mode", "search")]), "search")


    def action(self):
        if html.var("_search"): # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.var("_delete_folder"):
            if html.transaction_valid():
                return self._delete_subfolder_after_confirm(html.var("_delete_folder"))
            return

        elif html.has_var("_move_folder_to"):
            if html.check_transaction():
                what_folder = watolib.Folder.folder(html.var("_ident"))
                target_folder = watolib.Folder.folder(html.var("_move_folder_to"))
                watolib.Folder.current().move_subfolder_to(what_folder, target_folder)
            return

        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.var("_delete_host")
        if delname and watolib.Folder.current().has_host(delname):
            return delete_host_after_confirm(delname)

        # Move single hosts to other folders
        if html.has_var("_move_host_to"):
            hostname = html.var("_ident")
            if hostname:
                target_folder = watolib.Folder.folder(html.var("_move_host_to"))
                watolib.Folder.current().move_hosts([hostname], target_folder)
                return

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        # Host table: No error message on search filter reset
        if html.var("_hosts_reset_sorting") or html.var("_hosts_sort"):
            return

        selected_host_names = get_hostnames_from_checkboxes()
        if len(selected_host_names) == 0:
            raise MKUserError(None,
            _("Please select some hosts before doing bulk operations on hosts."))

        if html.var("_bulk_inventory"):
            return "bulkinventory"

        elif html.var("_parentscan"):
            return "parentscan"

        # Deletion
        if html.var("_bulk_delete"):
            return self._delete_hosts_after_confirm(selected_host_names)

        # Move
        elif html.var("_bulk_move"):
            target_folder_path = html.var("bulk_moveto", html.var("_top_bulk_moveto"))
            if target_folder_path == "@":
                raise MKUserError("bulk_moveto", _("Please select the destination folder"))
            target_folder = watolib.Folder.folder(target_folder_path)
            watolib.Folder.current().move_hosts(selected_host_names, target_folder)
            return None, _("Moved %d hosts to %s") % (len(selected_host_names), target_folder.title())

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
            return self._move_to_imported_folders(selected_host_names)

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"


    def _delete_subfolder_after_confirm(self, subfolder_name):
        subfolder = self._folder.subfolder(subfolder_name)
        msg = _("Do you really want to delete the folder %s?") % subfolder.title()
        if not config.wato_hide_filenames:
            msg += _(" Its directory is <tt>%s</tt>.") % subfolder.filesystem_path()
        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts:
            msg += _(" The folder contains <b>%d</b> hosts, which will also be deleted!") % num_hosts
        c = wato_confirm(_("Confirm folder deletion"), msg)

        if c:
            self._folder.delete_subfolder(subfolder_name) # pylint: disable=no-member
            return "folder"
        elif c == False: # not yet confirmed
            return ""
        return None # browser reload


    def page(self):
        self._folder.show_breadcrump()

        if not self._folder.may("read"):
            html.message(html.render_icon("autherr", cssclass="authicon")
                         + " " + self._folder.reason_why_may_not("read"))

        self._folder.show_locking_information()
        self._show_subfolders_of()
        if self._folder.may("read"):
            self._show_hosts()

        if not self._folder.has_hosts():
            if self._folder.is_search_folder():
                html.message(_("No matching hosts found."))
            elif not self._folder.has_subfolders() and self._folder.may("write"):
                self._show_empty_folder_menu()


    def _show_empty_folder_menu(self):
        menu_items = []

        if not self._folder.locked_hosts():
            menu_items.extend([
            MenuItem("newhost", _("Create new host"), "new", "hosts",
              _("Add a new host to the monitoring (agent must be installed)")),
            MenuItem("newcluster", _("Create new cluster"), "new_cluster", "hosts",
              _("Use Check_MK clusters if an item can move from one host "
                "to another at runtime"))])

        if not self._folder.locked_subfolders():
            menu_items.extend([
            MenuItem("newfolder", _("Create new folder"), "newfolder", "hosts",
              _("Folders group your hosts, can inherit attributes and can have permissions."))
            ])

        MainMenu(menu_items).show()


    def _show_subfolders_of(self):
        if self._folder.has_subfolders():
            html.open_div(class_="folders") # This won't hurt even if there are no visible subfolders
            for subfolder in self._folder.visible_subfolders_sorted_by_title(): # pylint: disable=no-member
                self._show_subfolder(subfolder)
            html.close_div()
            html.div('', class_="folder_foot")


    def _show_subfolder(self, subfolder):
        html.open_div(class_=["floatfolder", "unlocked" if subfolder.may("read") else "locked"],
                      id_="folder_%s" % subfolder.name(),
                      onclick="wato_open_folder(event, \'%s\');" % subfolder.url())
        self._show_subfolder_hoverarea(subfolder)
        self._show_subfolder_infos(subfolder)
        self._show_subfolder_title(subfolder)
        html.close_div() # floatfolder


    def _show_subfolder_hoverarea(self, subfolder):
        # Only make folder openable when permitted to edit
        if subfolder.may("read"):
            html.open_div(class_="hoverarea", onmouseover="wato_toggle_folder(event, this, true);",
                                              onmouseout="wato_toggle_folder(event, this, false);")
            self._show_subfolder_buttons(subfolder)
            html.close_div() # hoverarea
        else:
            html.icon(html.strip_tags(subfolder.reason_why_may_not("read")), "autherr", class_=["autherr"])
            html.div('', class_="hoverarea")


    def _show_subfolder_title(self, subfolder):
        title = subfolder.title()
        if not config.wato_hide_filenames:
            title += ' (%s)' % subfolder.name()

        html.open_div(class_="title", title=title)
        if subfolder.may("read"):
            html.a(subfolder.title(), href=subfolder.url())
        else:
            html.write_text(subfolder.title())
        html.close_div()


    def _show_subfolder_buttons(self, subfolder):
        self._show_subfolder_edit_button(subfolder)

        if not subfolder.locked_subfolders() and not subfolder.locked():
            if subfolder.may("write") and config.user.may("wato.manage_folders"):
                self._show_move_to_folder_action(subfolder)
                self._show_subfolder_delete_button(subfolder)


    def _show_subfolder_edit_button(self, subfolder):
        html.icon_button(
            subfolder.edit_url(subfolder.parent()),
            _("Edit the properties of this folder"),
            "edit",
            id_ = 'edit_' + subfolder.name(),
            cssclass = 'edit',
            style = 'display:none',
        )


    def _show_subfolder_delete_button(self, subfolder):
        html.icon_button(
            make_action_link([("mode", "folder"), ("_delete_folder", subfolder.name())]),
            _("Delete this folder"),
            "delete",
            id_ = 'delete_' + subfolder.name(),
            cssclass = 'delete',
            style = 'display:none',
        )


    def _show_subfolder_infos(self, subfolder):
        html.open_div(class_="infos")
        html.open_div(class_="infos_content")
        groups = userdb.load_group_information().get("contact", {})
        permitted_groups, _folder_contact_groups, _use_for_services = subfolder.groups()
        for num, pg in enumerate(permitted_groups):
            cgalias = groups.get(pg, {'alias': pg})['alias']
            html.icon(_("Contactgroups that have permission on this folder"), "contactgroups")
            html.write_text(' %s' % cgalias)
            html.br()
            if num > 1 and len(permitted_groups) > 4:
                html.write_text(_('<i>%d more contact groups</i><br>') % (len(permitted_groups) - num - 1))
                break

        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts == 1:
            html.write_text(_("1 Host"))
        elif num_hosts > 0:
            html.write_text("%d %s" % (num_hosts, _("Hosts")))
        else:
            html.i(_("(no hosts)"))
        html.close_div()
        html.close_div()


    def _show_move_to_folder_action(self, obj):
        if isinstance(obj, watolib.Host):
            what = "host"
            what_title = _("host")
            ident = obj.name()
            style = None
        else:
            what = "folder"
            what_title = _("folder")
            ident = obj.path()
            style = "display:none"

        html.popup_trigger(
            html.render_icon("move", title=_("Move this %s to another folder") % what_title,
                             cssclass="iconbutton"),
            ident="move_"+obj.name(),
            what="move_to_folder",
            url_vars=[
                ("what", what),
                ("ident", ident),
                ("back_url", html.makeactionuri([])),
            ],
            style=style,
        )


    def _show_hosts(self):
        if not self._folder.has_hosts():
            return

        show_checkboxes = html.var('show_checkboxes', '0') == '1'

        hostnames = self._folder.hosts().keys()
        hostnames.sort(cmp=utils.cmp_num_split)
        search_text = html.var("search")

        # Helper function for showing bulk actions. This is needed at the bottom
        # of the table of hosts and - if there are more than just a few - also
        # at the top of the table.
        search_shown = False
        def bulk_actions(at_least_one_imported, top, withsearch, colspan, show_checkboxes):
            table.row(collect_headers=False, fixed=True)
            table.cell(css="bulksearch", colspan=3)

            if not show_checkboxes:
                onclick_uri = html.makeuri([('show_checkboxes', '1'), ('selection', weblib.selection_id())])
                checkbox_title = _('Show Checkboxes and bulk actions')
            else:
                onclick_uri = html.makeuri([('show_checkboxes', '0')])
                checkbox_title = _('Hide Checkboxes and bulk actions')

            html.toggle_button("checkbox_on", show_checkboxes, "checkbox",
                title=checkbox_title,
                onclick="location.href=\'%s\'" % onclick_uri,
                is_context_button=False)

            if withsearch:
                html.text_input("search")
                html.button("_search", _("Search"))
                html.set_focus("search")
            table.cell(css="bulkactions", colspan=colspan-3)
            html.write_text(' ' + _("Selected hosts:\n"))

            if not self._folder.locked_hosts():
                if config.user.may("wato.manage_hosts"):
                    html.button("_bulk_delete", _("Delete"))
                if config.user.may("wato.edit_hosts"):
                    html.button("_bulk_edit", _("Edit"))
                    html.button("_bulk_cleanup", _("Cleanup"))

            if config.user.may("wato.services"):
                html.button("_bulk_inventory", _("Discovery"))

            if not self._folder.locked_hosts():
                if config.user.may("wato.parentscan"):
                    html.button("_parentscan", _("Parentscan"))
                if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
                    self._host_bulk_move_to_folder_combo(top)
                    if at_least_one_imported:
                        html.button("_bulk_movetotarget", _("Move to Target Folders"))

        # Show table of hosts in this folder
        html.begin_form("hosts", method = "POST")
        table.begin("hosts", title=_("Hosts"), searchable=False)

        # Remember if that host has a target folder (i.e. was imported with
        # a folder information but not yet moved to that folder). If at least
        # one host has a target folder, then we show an additional bulk action.
        at_least_one_imported = False
        more_than_ten_items = False
        for num, hostname in enumerate(hostnames):
            if search_text and (search_text.lower() not in hostname.lower()):
                continue

            host = self._folder.host(hostname)
            effective = host.effective_attributes()

            if effective.get("imported_folder"):
                at_least_one_imported = True

            if num == 11:
                more_than_ten_items = True


        # Compute colspan for bulk actions
        colspan = 6
        for attr, _topic in watolib.all_host_attributes():
            if attr.show_in_table():
                colspan += 1
        if not self._folder.locked_hosts() and config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
            colspan += 1
        if show_checkboxes:
            colspan += 1
        if self._folder.is_search_folder():
            colspan += 1

        # Add the bulk action buttons also to the top of the table when this
        # list shows more than 10 rows
        if more_than_ten_items and \
            (config.user.may("wato.edit_hosts") or config.user.may("wato.manage_hosts")):
            bulk_actions(at_least_one_imported, True, True, colspan, show_checkboxes)
            search_shown = True

        contact_group_names = userdb.load_group_information().get("contact", {})
        def render_contact_group(c):
            display_name = contact_group_names.get(c, {'alias': c})['alias']
            return html.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)

        host_errors = self._folder.host_validation_errors()
        rendered_hosts = []

        # Now loop again over all hosts and display them
        for hostname in hostnames:
            if search_text and (search_text.lower() not in hostname.lower()):
                continue

            host = self._folder.host(hostname)
            rendered_hosts.append(hostname)
            effective = host.effective_attributes()

            table.row()

            # Column with actions (buttons)

            if show_checkboxes:
                table.cell(html.render_input("_toggle_group", type_="button",
                            class_="checkgroup", onclick="toggle_all_rows();",
                            value='X'), sortable=False, css="checkbox")
                # Use CSS class "failed" in order to provide information about
                # selective toggling inventory-failed hosts for Javascript
                html.input(name="_c_%s" % hostname, type_="checkbox", value=colspan,
                           class_="failed" if host.discovery_failed() else None)
                html.label("", "_c_%s" % hostname)

            table.cell(_("Actions"), css="buttons", sortable=False)
            self._show_host_actions(host)

            # Hostname with link to details page (edit host)
            table.cell(_("Hostname"))
            errors = host_errors.get(hostname,[]) + host.validation_errors()
            if errors:
                msg = _("Warning: This host has an invalid configuration: ")
                msg += ", ".join(errors)
                html.icon(msg, "validation_error")
                html.nbsp()

            if host.is_offline():
                html.icon(_("This host is disabled"), "disabled")
                html.nbsp()

            if host.is_cluster():
                html.icon(_("This host is a cluster of %s") % ", ".join(host.cluster_nodes()), "cluster")
                html.nbsp()

            html.a(hostname, href=host.edit_url())

            # Show attributes
            for attr, _topic in watolib.all_host_attributes():
                if attr.show_in_table():
                    attrname = attr.name()
                    if attrname in host.attributes():
                        tdclass, tdcontent = attr.paint(host.attributes()[attrname], hostname)
                    else:
                        tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                        tdclass += " inherited"
                    table.cell(attr.title(), html.attrencode(tdcontent), css=tdclass)

            # Am I authorized?
            reason = host.reason_why_may_not("read")
            if not reason:
                icon = "authok"
                title = _("You have permission to this host.")
            else:
                icon = "autherr"
                title = html.strip_tags(reason)

            table.cell(_('Auth'), html.render_icon(icon, title), sortable=False)

            # Permissions and Contact groups - through complete recursion and inhertance
            permitted_groups, host_contact_groups, _use_for_services = host.groups()
            table.cell(_("Permissions"), HTML(", ").join(map(render_contact_group, permitted_groups)))
            table.cell(_("Contact Groups"), HTML(", ").join(map(render_contact_group, host_contact_groups)))

            if not config.wato_hide_hosttags:
                # Raw tags
                #
                # Optimize wraps:
                # 1. add <nobr> round the single tags to prevent wrap within tags
                # 2. add "zero width space" (&#8203;)
                tag_title = "|".join([ '%s' % t for t in host.tags() ])
                table.cell(_("Tags"), help_txt=tag_title, css="tag-ellipsis")
                html.write("<b style='color: #888;'>|</b>&#8203;".join([ '<nobr>%s</nobr>' % t for t in host.tags() ]))

            # Located in folder
            if self._folder.is_search_folder():
                table.cell(_("Folder"))
                html.a(host.folder().alias_path(), href=host.folder().url())

        if config.user.may("wato.edit_hosts") or config.user.may("wato.manage_hosts"):
            bulk_actions(at_least_one_imported, False, not search_shown, colspan, show_checkboxes)

        table.end()
        html.hidden_fields()
        html.end_form()

        selected = weblib.get_rowselection('wato-folder-/' + self._folder.path())

        row_count = len(rendered_hosts)
        headinfo = "%d %s" % (row_count, _("host") if row_count == 1 else _("hosts"))
        html.javascript("update_headinfo('%s');" % headinfo)

        if show_checkboxes:
            html.javascript(
                'g_page_id = "wato-folder-%s";\n'
                'g_selection = "%s";\n'
                'g_selected_rows = %s;\n'
                'init_rowselect();' % ('/' + self._folder.path(), weblib.selection_id(), json.dumps(selected))
            )


    def _show_host_actions(self, host):
        html.icon_button(host.edit_url(), _("Edit the properties of this host"), "edit")
        if config.user.may("wato.rulesets"):
            html.icon_button(host.params_url(), _("View the rule based parameters of this host"), "rulesets")

        if host.may('read'):
            if config.user.may("wato.services"):
                msg = _("Edit the services of this host, do a service discovery")
            else:
                msg = _("Display the services of this host")
            image =  "services"
            if host.discovery_failed():
                image = "inventory_failed"
                msg += ". " + _("The service discovery of this host failed during a previous bulk service discovery.")
            html.icon_button(host.services_url(), msg, image)

        if not host.locked():
            if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts") \
               and host.folder().choices_for_moving_host():
                self._show_move_to_folder_action(host)

            if config.user.may("wato.manage_hosts"):
                if config.user.may("wato.clone_hosts"):
                    html.icon_button(host.clone_url(), _("Create a clone of this host"), "insert")
                delete_url  = make_action_link([("mode", "folder"), ("_delete_host", host.name())])
                html.icon_button(delete_url, _("Delete this host"), "delete")


    def _delete_hosts_after_confirm(self, host_names):
        c = wato_confirm(_("Confirm deletion of %d hosts") % len(host_names),
                         _("Do you really want to delete the %d selected hosts?") % len(host_names))
        if c:
            self._folder.delete_hosts(host_names)
            return "folder", _("Successfully deleted %d hosts") % len(host_names)
        elif c == False: # not yet confirmed
            return ""
        return None # browser reload


    # FIXME: Cleanup
    def _host_bulk_move_to_folder_combo(self, top):
        choices = self._folder.choices_for_moving_host()
        if len(choices):
            choices = [("@", _("(select target folder)"))] + choices
            html.button("_bulk_move", _("Move to:"))
            html.write("&nbsp;")
            field_name = 'bulk_moveto'
            if top:
                field_name = '_top_bulk_moveto'
                if html.has_var('bulk_moveto'):
                    html.javascript('update_bulk_moveto("%s")' % html.var('bulk_moveto', ''))
            html.dropdown(field_name, choices, deflt="@",
                          onchange = "update_bulk_moveto(this.value)",
                          class_ = 'bulk_moveto')


    def _move_to_imported_folders(self, host_names_to_move):
        c = wato_confirm(
                  _("Confirm moving hosts"),
                  _('You are going to move the selected hosts to folders '
                    'representing their original folder location in the system '
                    'you did the import from. Please make sure that you have '
                    'done an <b>inventory</b> before moving the hosts.'))
        if c == False: # not yet confirmed
            return ""
        elif not c:
            return None # browser reload

        # Create groups of hosts with the same target folder
        target_folder_names = {}
        for host_name in host_names_to_move:
            host = self._folder.host(host_name)
            imported_folder_name = host.attribute('imported_folder')
            if imported_folder_name == None:
                continue
            target_folder_names.setdefault(imported_folder_name, []).append(host_name)

            # Remove target folder information, now that the hosts are
            # at their target position.
            host.remove_attribute('imported_folder')

        # Now handle each target folder
        for imported_folder, host_names in target_folder_names.items():
            # Next problem: The folder path in imported_folder refers
            # to the Alias of the folders, not to the internal file
            # name. And we need to create folders not yet existing.
            target_folder = self._create_target_folder_from_aliaspath(imported_folder)
            self._folder.move_hosts(host_names, target_folder)

        return None, _("Successfully moved hosts to their original folder destinations.")


    def _create_target_folder_from_aliaspath(self, aliaspath):
        # The alias path is a '/' separated path of folder titles.
        # An empty path is interpreted as root path. The actual file
        # name is the host list with the name "Hosts".
        if aliaspath == "" or aliaspath == "/":
            folder = watolib.Folder.root_folder()
        else:
            parts = aliaspath.strip("/").split("/")
            folder = watolib.Folder.root_folder()
            while len(parts) > 0:
                # Look in current folder for subfolder with the target name
                subfolder = folder.subfolder_by_title(parts[0])
                if subfolder:
                    folder = subfolder
                else:
                    name = watolib.create_wato_foldername(parts[0], folder)
                    folder = folder.create_subfolder(name, parts[0], {})
                parts = parts[1:]

        return folder



# TODO: Move to WatoHostFolderMode() once mode_edit_host has been migrated
def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        watolib.Folder.current().delete_hosts([delname])
        # Delete host files
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    return None # browser reload


# TODO: Split this into one base class and one subclass for folder and hosts
class ModeAjaxPopupMoveToFolder(WatoWebApiMode):
    """Renders the popup menu contents for either moving a host or a folder to another folder"""

    def _from_vars(self):
        self._what = html.var("what")
        if self._what not in [ "host", "folder" ]:
            raise NotImplementedError()

        self._ident = html.var("ident")

        self._back_url = html.get_url_input("back_url")
        if not self._back_url or not self._back_url.startswith("wato.py"):
            raise MKUserError("back_url", _("Invalid back URL provided."))


    # TODO: Better use handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def page(self):
        html.span(self._move_title())

        choices = self._get_choices()
        if not choices:
            html.write_text(_("No valid target folder."))
            return

        html.dropdown("_host_move_%s" % self._ident,
            choices=choices,
            deflt="@",
            size = '10',
            onchange="location.href='%s&_ident=%s&_move_%s_to=' + this.value;" %
                                    (self._back_url, self._ident, self._what),
        )


    def _move_title(self):
        if self._what == "host":
            return _('Move this host to:')
        return _('Move this folder to:')


    def _get_choices(self):
        choices = [
            ("@", _("(select target folder)")),
        ]

        if self._what == "host":
            obj = watolib.Host.host(self._ident)
            choices += obj.folder().choices_for_moving_host()

        elif self._what == "folder":
            obj = watolib.Folder.folder(self._ident)
            choices += obj.choices_for_moving_folder()

        else:
            raise NotImplementedError()

        return choices

#.
#   .--Edit Folder---------------------------------------------------------.
#   |           _____    _ _ _     _____     _     _                       |
#   |          | ____|__| (_) |_  |  ___|__ | | __| | ___ _ __             |
#   |          |  _| / _` | | __| | |_ / _ \| |/ _` |/ _ \ '__|            |
#   |          | |__| (_| | | |_  |  _| (_) | | (_| |  __/ |               |
#   |          |_____\__,_|_|\__| |_|  \___/|_|\__,_|\___|_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for editing the properties of a folder. This includes the       |
#   | creation of new folders.                                             |
#   '----------------------------------------------------------------------'

class FolderMode(WatoMode):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(FolderMode, self).__init__()
        self._folder = self._init_folder()


    @abc.abstractmethod
    def _init_folder(self):
        # TODO: Needed to make pylint know the correct type of the return value.
        # Will be cleaned up in future when typing is established
        return watolib.Folder(name=None)


    @abc.abstractmethod
    def _save(self, title, attributes):
        raise NotImplementedError()


    def buttons(self):
        if html.has_var("backfolder"):
            back_folder = watolib.Folder.folder(html.var("backfolder"))
        else:
            back_folder = self._folder
        html.context_button(_("Back"), back_folder.url(), "back")


    def action(self):
        if not html.check_transaction():
            return "folder"

        # Title
        title = TextUnicode().from_html_vars("title")
        TextUnicode(allow_empty = False).validate_value(title, "title")

        attributes = watolib.collect_attributes("folder")
        self._save(title, attributes)

        # Edit icon on subfolder preview should bring user back to parent folder
        if html.has_var("backfolder"):
            watolib.Folder.set_current(watolib.Folder.folder(html.var("backfolder")))
        return "folder"


    # TODO: Clean this method up! Split new/edit handling to sub classes
    def page(self):
        new = self._folder.name() is None

        watolib.Folder.current().show_breadcrump()
        watolib.Folder.current().need_permission("read")

        if new and watolib.Folder.current().locked():
            watolib.Folder.current().show_locking_information()

        html.begin_form("edit_host", method = "POST")

        # title
        forms.header(_("Title"))
        forms.section(_("Title"))
        TextUnicode().render_input("title", self._folder.title())
        html.set_focus("title")

        # folder name (omit this for root folder)
        if new or not watolib.Folder.current().is_root():
            if not config.wato_hide_filenames:
                forms.section(_("Internal directory name"))
                if new:
                    html.text_input("name")
                else:
                    html.write_text(self._folder.name())
                html.help(_("This is the name of subdirectory where the files and "
                    "other folders will be created. You cannot change this later."))

        # Attributes inherited to hosts
        if new:
            parent = watolib.Folder.current()
            myself = None
        else:
            parent = watolib.Folder.current().parent()
            myself = watolib.Folder.current()

        configure_attributes(new, {"folder": myself}, "folder", parent, myself)

        forms.end()
        if new or not watolib.Folder.current().locked():
            html.button("save", _("Save & Finish"), "submit")
        html.hidden_fields()
        html.end_form()



@mode_registry.register
class ModeEditFolder(FolderMode):
    @classmethod
    def name(cls):
        return "editfolder"


    @classmethod
    def permissions(cls):
        return ["hosts"]


    def _init_folder(self):
        return watolib.Folder.current()


    def title(self):
        return _("Folder properties")


    def _save(self, title, attributes):
        self._folder.edit(title, attributes)



@mode_registry.register
class ModeCreateFolder(FolderMode):
    @classmethod
    def name(cls):
        return "newfolder"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_folders"]


    def _init_folder(self):
        return watolib.Folder(name=None)


    def title(self):
        return _("Create new folder")


    def _save(self, title, attributes):
        if not config.wato_hide_filenames:
            name = html.var("name", "").strip()
            watolib.check_wato_foldername("name", name)
        else:
            name = watolib.create_wato_foldername(title)

        watolib.Folder.current().create_subfolder(name, title, attributes)



class ModeAjaxSetFoldertree(WatoWebApiMode):
    def page(self):
        request = self.webapi_request()
        config.user.save_file("foldertree", (request.get('topic'), request.get('target')))


#.
#   .--Edit-Host-----------------------------------------------------------.
#   |               _____    _ _ _     _   _           _                   |
#   |              | ____|__| (_) |_  | | | | ___  ___| |_                 |
#   |              |  _| / _` | | __| | |_| |/ _ \/ __| __|                |
#   |              | |__| (_| | | |_  |  _  | (_) \__ \ |_                 |
#   |              |_____\__,_|_|\__| |_| |_|\___/|___/\__|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for host details (new, clone, edit)                             |
#   '----------------------------------------------------------------------'

class HostMode(WatoMode):
    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def _init_host(self):
        raise NotImplementedError()


    def __init__(self):
        self._host = self._init_host()
        self._mode = "edit"
        super(HostMode, self).__init__()


    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "back")


    def _is_cluster(self):
        return self._host.is_cluster()


    def _get_cluster_nodes(self):
        if not self._is_cluster():
            return None

        cluster_nodes = self._vs_cluster_nodes().from_html_vars("nodes")
        self._vs_cluster_nodes().validate_value(cluster_nodes, "nodes")
        if len(cluster_nodes) < 1:
            raise MKUserError("nodes_0", _("The cluster must have at least one node"))
        for nr, cluster_node in enumerate(cluster_nodes):
            if cluster_node == self._host.name():
                raise MKUserError("nodes_%d" % nr, _("The cluster can not be a node of it's own"))

            if not watolib.Host.host_exists(cluster_node):
                raise MKUserError("nodes_%d" % nr, _("The node <b>%s</b> does not exist "
                                  " (must be a host that is configured with WATO)") % cluster_node)
        return cluster_nodes


    # TODO: Extract cluster specific parts from this method
    def page(self):
        # Show outcome of host validation. Do not validate new hosts
        errors = None
        if self._mode != "edit":
            watolib.Folder.current().show_breadcrump()
        else:
            errors = watolib.validate_all_hosts([self._host.name()]).get(self._host.name(), []) + self._host.validation_errors()

        if errors:
            html.open_div(class_="info")
            html.open_table(class_="validationerror", boder=0, cellspacing=0, cellpadding=0)
            html.open_tr()

            html.open_td(class_="img")
            html.img("images/icon_validation_error.png")
            html.close_td()

            html.open_td()
            html.open_p()
            html.h3(_("Warning: This host has an invalid configuration!"))
            html.open_ul()
            for error in errors:
                html.li(error)
            html.close_ul()
            html.close_p()

            if html.form_submitted():
                html.br()
                html.b(_("Your changes have been saved nevertheless."))
            html.close_td()

            html.close_tr()
            html.close_table()
            html.close_div()

        lock_message = ""
        if watolib.Folder.current().locked_hosts():
            if watolib.Folder.current().locked_hosts() == True:
                lock_message = _("Host attributes locked (You cannot edit this host)")
            else:
                lock_message = watolib.Folder.current().locked_hosts()
        if len(lock_message) > 0:
            html.div(lock_message, class_="info")

        html.begin_form("edit_host", method="POST")
        html.prevent_password_auto_completion()

        forms.header(_("General Properties"))
        self._show_host_name()

        # Cluster: nodes
        if self._is_cluster():
            forms.section(_("Nodes"))
            self._vs_cluster_nodes().render_input("nodes", self._host.cluster_nodes() if self._host else [])
            html.help(_('Enter the host names of the cluster nodes. These '
                       'hosts must be present in WATO. '))

        configure_attributes(
            new=self._mode != "edit",
            hosts={self._host.name(): self._host} if self._mode != "new" else {},
            for_what="host" if not self._is_cluster() else "cluster",
            parent = watolib.Folder.current()
        )

        forms.end()
        if not watolib.Folder.current().locked_hosts():
            html.button("services", _("Save & go to Services"), "submit")
            html.button("save", _("Save & Finish"), "submit")
            if not self._is_cluster():
                html.button("diag_host", _("Save & Test"), "submit")
        html.hidden_fields()
        html.end_form()


    def _vs_cluster_nodes(self):
        return ListOfStrings(
            valuespec = TextAscii(size = 19),
            orientation = "horizontal",
        )


    @abc.abstractmethod
    def _show_host_name(self):
        raise NotImplementedError()



# TODO: Split this into two classes ModeEditHost / ModeEditCluster. The problem with this is that
# we simply don't know whether or not a cluster or regular host is about to be edited. The GUI code
# simply wants to link to the "host edit page". We could try to use some factory to decide this when
# the edit_host mode is called.
@mode_registry.register
class ModeEditHost(HostMode):
    @classmethod
    def name(cls):
        return "edit_host"


    @classmethod
    def permissions(cls):
        return ["hosts"]


    def _init_host(self):
        hostname = html.var("host") # may be empty in new/clone mode

        if not watolib.Folder.current().has_host(hostname):
            raise MKGeneralException(_("You called this page with an invalid host name."))

        return watolib.Folder.current().host(hostname)


    def title(self):
        return _("Properties of host") + " " + self._host.name()


    def buttons(self):
        super(ModeEditHost, self).buttons()

        host_status_button(self._host.name(), "hoststatus")

        html.context_button(_("Services"),
              watolib.folder_preserving_link([("mode", "inventory"), ("host", self._host.name())]), "services")
        if watolib.has_agent_bakery() and config.user.may('wato.download_agents'):
            html.context_button(_("Monitoring Agent"),
              watolib.folder_preserving_link([("mode", "agent_of_host"), ("host", self._host.name())]), "agents")

        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"),
              watolib.folder_preserving_link([("mode", "object_parameters"), ("host", self._host.name())]), "rulesets")
            if self._is_cluster():
                html.context_button(_("Clustered Services"),
                  watolib.folder_preserving_link([("mode", "edit_ruleset"), ("varname", "clustered_services")]), "rulesets")

        if not watolib.Folder.current().locked_hosts():
            if config.user.may("wato.rename_hosts"):
                html.context_button(self._is_cluster() and _("Rename cluster") or _("Rename host"),
                  watolib.folder_preserving_link([("mode", "rename_host"), ("host", self._host.name())]), "rename_host")
            html.context_button(self._is_cluster() and _("Delete cluster") or _("Delete host"),
                  html.makeactionuri([("delete", "1")]), "delete")

        if not self._is_cluster():
            html.context_button(_("Diagnostic"),
                  watolib.folder_preserving_link([("mode", "diag_host"), ("host", self._host.name())]), "diagnose")
        html.context_button(_("Update DNS Cache"),
                  html.makeactionuri([("_update_dns_cache", "1")]), "update")


    def action(self):
        if html.var("_update_dns_cache"):
            if html.check_transaction():
                config.user.need_permission("wato.update_dns_cache")
                num_updated, failed_hosts = watolib.check_mk_automation(self._host.site_id(), "update-dns-cache", [])
                infotext = _("Successfully updated IP addresses of %d hosts.") % num_updated
                if failed_hosts:
                    infotext += "<br><br><b>Hostnames failed to lookup:</b> " \
                              + ", ".join(["<tt>%s</tt>" % h for h in failed_hosts])
                return None, infotext
            else:
                return None

        if html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "folder"
            return delete_host_after_confirm(self._host.name())

        if html.check_transaction():
            attributes = watolib.collect_attributes("host" if not self._is_cluster() else "cluster")
            watolib.Host.host(self._host.name()).edit(attributes, self._get_cluster_nodes())
            self._host = watolib.Folder.current().host(self._host.name())

        if html.var("services"):
            return "inventory"
        elif html.var("diag_host"):
            html.set_var("_try", "1")
            return "diag_host"
        return "folder"


    def _show_host_name(self):
        forms.section(_("Hostname"), simple=True)
        html.write_text(self._host.name())



class CreateHostMode(HostMode):
    @classmethod
    @abc.abstractmethod
    def _init_new_host_object(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def _host_type_name(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def _verify_host_type(cls, host):
        raise NotImplementedError()


    def _from_vars(self):
        if html.var("clone") and self._init_host():
            self._mode = "clone"
        else:
            self._mode = "new"


    def _init_host(self):
        clonename = html.var("clone")
        if clonename:
            if not watolib.Folder.current().has_host(clonename):
                raise MKGeneralException(_("You called this page with an invalid host name."))

            if not config.user.may("wato.clone_hosts"):
                raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))

            host = watolib.Folder.current().host(clonename)
            self._verify_host_type(host)
            return host
        else:
            return self._init_new_host_object()


    def action(self):
        if not html.transaction_valid():
            return "folder"

        attributes = watolib.collect_attributes(self._host_type_name())
        cluster_nodes = self._get_cluster_nodes()

        hostname = html.var("host")
        Hostname().validate_value(hostname, "host")

        if html.check_transaction():
            watolib.Folder.current().create_hosts([(hostname, attributes, cluster_nodes)])

        self._host = watolib.Folder.current().host(hostname)

        if "ping" not in self._host.tags():
            create_msg = _('Successfully created the host. Now you should do a '
                           '<a href="%s">service discovery</a> in order to auto-configure '
                           'all services to be checked on this host.') % \
                            watolib.folder_preserving_link([("mode", "inventory"), ("host", self._host.name())])
        else:
            create_msg = None

        if html.var("services"):
            return "inventory"
        elif html.var("diag_host"):
            html.set_var("_try", "1")
            return "diag_host", create_msg
        return "folder", create_msg


    def _show_host_name(self):
        forms.section(_("Hostname"))
        Hostname().render_input("host", "")
        html.set_focus("host")



@mode_registry.register
class ModeCreateHost(CreateHostMode):
    @classmethod
    def name(cls):
        return "newhost"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]


    def title(self):
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Create new host")


    @classmethod
    def _init_new_host_object(cls):
        return watolib.Host(folder=watolib.Folder.current(), host_name=html.var("host"),
                            attributes={}, cluster_nodes=None)


    @classmethod
    def _host_type_name(cls):
        return "host"


    @classmethod
    def _verify_host_type(cls, host):
        if host.is_cluster():
            raise MKGeneralException(_("Can not clone a cluster host as regular host"))




@mode_registry.register
class ModeCreateCluster(CreateHostMode):
    @classmethod
    def name(cls):
        return "newcluster"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]


    def _is_cluster(self):
        return True


    def title(self):
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Create new cluster")


    @classmethod
    def _init_new_host_object(cls):
        return watolib.Host(folder=watolib.Folder.current(), host_name=html.var("host"),
                            attributes={}, cluster_nodes=[])


    @classmethod
    def _host_type_name(cls):
        return "cluster"


    @classmethod
    def _verify_host_type(cls, host):
        if not host.is_cluster():
            raise MKGeneralException(_("Can not clone a regular host as cluster host"))


#.
#   .--Rename Host---------------------------------------------------------.
#   |     ____                                   _   _           _         |
#   |    |  _ \ ___ _ __   __ _ _ __ ___   ___  | | | | ___  ___| |_       |
#   |    | |_) / _ \ '_ \ / _` | '_ ` _ \ / _ \ | |_| |/ _ \/ __| __|      |
#   |    |  _ <  __/ | | | (_| | | | | | |  __/ |  _  | (_) \__ \ |_       |
#   |    |_| \_\___|_| |_|\__,_|_| |_| |_|\___| |_| |_|\___/|___/\__|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for renaming an existing host.                                  |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeBulkRenameHost(WatoMode):
    @classmethod
    def name(cls):
        return "bulk_rename_host"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]


    def __init__(self):
        super(ModeBulkRenameHost, self).__init__()

        if not config.user.may("wato.rename_hosts"):
            raise MKGeneralException(_("You don't have the right to rename hosts"))


    def title(self):
        return _("Bulk renaming of hosts")


    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "back")
        host_renaming_job = RenameHostsBackgroundJob()
        if host_renaming_job.is_available():
            html.context_button(_("Last result"), host_renaming_job.detail_url(), "background_job_details")


    def action(self):
        renaming_config = self._vs_renaming_config().from_html_vars("")
        self._vs_renaming_config().validate_value(renaming_config, "")
        renamings = self._collect_host_renamings(renaming_config)

        if not renamings:
            return None, _("No matching host names")

        warning = self._renaming_collision_error(renamings)
        if warning:
            return None, warning

        message = _("<b>Do you really want to rename to following hosts? This involves a restart of the monitoring core!</b>")
        message += "<table>"
        for _folder, host_name, target_name in renamings:
            message += u"<tr><td>%s</td><td> → %s</td></tr>" % (host_name, target_name)
        message += "</table>"

        c = wato_confirm(_("Confirm renaming of %d hosts") % len(renamings), HTML(message))
        if c:
            title = _("Renaming of %s") % ", ".join(u"%s → %s" % x[1:] for x in renamings)
            host_renaming_job = RenameHostsBackgroundJob(title=title)
            host_renaming_job.set_function(rename_hosts_background_job, renamings)

            try:
                host_renaming_job.start()
            except background_job.BackgroundJobAlreadyRunning, e:
                raise MKGeneralException(_("Another host renaming job is already running: %s") % e)

            html.response.http_redirect(host_renaming_job.detail_url())
        elif c == False: # not yet confirmed
            return ""
        else:
            return None # browser reload


    def _renaming_collision_error(self, renamings):
        name_collisions = set()
        new_names = [ new_name for _folder, _old_name, new_name in renamings ]
        all_host_names = watolib.Host.all().keys()
        for name in new_names:
            if name in all_host_names:
                name_collisions.add(name)
        for name in new_names:
            if new_names.count(name) > 1:
                name_collisions.add(name)

        if name_collisions:
            warning = "<b>%s</b><ul>" % _("You cannot do this renaming since the following host names would collide:")
            for name in sorted(list(name_collisions)):
                warning += "<li>%s</li>" % name
            warning += "</ul>"
            return warning


    def _collect_host_renamings(self, renaming_config):
        return self._recurse_hosts_for_renaming(watolib.Folder.current(), renaming_config)


    def _recurse_hosts_for_renaming(self, folder, renaming_config):
        entries = []
        for host_name, host in folder.hosts().items():
            target_name = self._host_renamed_into(host_name, renaming_config)
            if target_name and host.may("write"):
                entries.append((folder, host_name, target_name))
        if renaming_config["recurse"]:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts_for_renaming(subfolder, renaming_config)
        return entries


    def _host_renamed_into(self, hostname, renaming_config):
        prefix_regex = regex(renaming_config["match_hostname"])
        if not prefix_regex.match(hostname):
            return None

        new_hostname = hostname
        for operation in renaming_config["renamings"]:
            new_hostname = self._host_renaming_operation(operation, new_hostname)

        if new_hostname != hostname:
            return new_hostname
        return None


    def _host_renaming_operation(self, operation, hostname):
        if operation == "drop_domain":
            return hostname.split(".", 1)[0]
        elif operation == "reverse_dns":
            try:
                reverse_dns = socket.gethostbyaddr(hostname)[0]
                return reverse_dns
            except:
                return hostname

        elif operation == ('case', 'upper'):
            return hostname.upper()
        elif operation == ('case', 'lower'):
            return hostname.lower()
        elif operation[0] == 'add_suffix':
            return hostname + operation[1]
        elif operation[0] == 'add_prefix':
            return  operation[1] + hostname
        elif operation[0] == 'explicit':
            old_name, new_name = operation[1]
            if old_name == hostname:
                return new_name
            return hostname
        elif operation[0] == 'regex':
            match_regex, new_name = operation[1]
            match = regex(match_regex).match(hostname)
            if match:
                for nr, group in enumerate(match.groups()):
                    new_name = new_name.replace("\\%d" % (nr+1), group)
                new_name = new_name.replace("\\0", hostname)
                return new_name
            return hostname


    def page(self):
        html.begin_form("bulk_rename_host", method = "POST")
        self._vs_renaming_config().render_input("", {})
        html.button("_start", _("Bulk Rename"))
        html.hidden_fields()
        html.end_form()


    def _vs_renaming_config(self):
        return Dictionary(
            title = _("Bulk Renaming"),
            render = "form",
            elements = [
                ( "recurse",
                  Checkbox(
                      title = _("Folder Selection"),
                      label = _("Include all subfolders"),
                      default_value = True,
                )),
                ( "match_hostname",
                  RegExp(
                      title = _("Hostname matching"),
                      help = _("Only rename hostnames whose names <i>begin</i> with the regular expression entered here."),
                      mode = RegExp.complete,
                )),
                ( "renamings",
                  ListOf(
                      self._vs_host_renaming(),
                      title = _("Renaming Operations"),
                      add_label = _("Add renaming"),
                      allow_empty = False,
                )),
            ],
            optional_keys = [],
        )


    def _vs_host_renaming(self):
        return CascadingDropdown(
            orientation = "horizontal",
            choices = [
                ( "case",
                  _("Case translation"),
                  DropdownChoice(
                      choices = [
                           ( "upper", _("Convert hostnames to upper case") ),
                           ( "lower", _("Convert hostnames to lower case") ),
                      ]
                )),
                ( "add_suffix",
                  _("Add Suffix"),
                  Hostname()),
                ( "add_prefix",
                  _("Add Prefix"),
                  Hostname()),
                ( "drop_domain",
                  _("Drop Domain Suffix")
                ),
                ( "reverse_dns",
                  _("Convert IP addresses of hosts into host their DNS names")
                ),
                ( "regex",
                  _("Regular expression substitution"),
                  Tuple(
                      help = _("Please specify a regular expression in the first field. This expression should at "
                               "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                               "In the second field you specify the translated host name and can refer to the first matched "
                               "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>"),
                      elements = [
                          RegExpUnicode(
                              title = _("Regular expression for the beginning of the host name"),
                              help = _("Must contain at least one subgroup <tt>(...)</tt>"),
                              mingroups = 0,
                              maxgroups = 9,
                              size = 30,
                              allow_empty = False,
                              mode = RegExpUnicode.prefix,
                          ),
                          TextUnicode(
                              title = _("Replacement"),
                              help = _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups, <tt>\\0</tt> to insert to original host name"),
                              size = 30,
                              allow_empty = False,
                          )
                     ]
                )),
                ( "explicit",
                  _("Explicit renaming"),
                  Tuple(
                      orientation = "horizontal",
                      elements = [
                          Hostname(title = _("current host name"), allow_empty = False),
                          Hostname(title = _("new host name"), allow_empty = False),
                      ]
                )),
            ])



def rename_hosts_background_job(renamings, job_interface=None):
    actions, auth_problems = rename_hosts(renamings, job_interface=job_interface) # Already activates the changes!
    watolib.confirm_all_local_changes() # All activated by the underlying rename automation
    action_txt =  "".join([ "<li>%s</li>" % a for a in actions ])
    message = _("Renamed %d hosts at the following places:<br><ul>%s</ul>") % (len(renamings), action_txt)
    if auth_problems:
        message += _("The following hosts could not be renamed because of missing permissions: %s") % ", ".join([
            "%s (%s)" % (host_name, reason) for (host_name, reason) in auth_problems
        ])
    job_interface.send_result_message(message)



@mode_registry.register
class ModeRenameHost(WatoMode):
    @classmethod
    def name(cls):
        return "rename_host"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]


    def _from_vars(self):
        host_name = html.var("host")

        if not watolib.Folder.current().has_host(host_name):
            raise MKGeneralException(_("You called this page with an invalid host name."))

        if not config.user.may("wato.rename_hosts"):
            raise MKGeneralException(_("You don't have the right to rename hosts"))

        self._host = watolib.Folder.current().host(host_name)
        self._host.need_permission("write")


    def title(self):
        return _("Rename %s %s") % (_("Cluster") if self._host.is_cluster() else _("Host"), self._host.name())


    def buttons(self):
        global_buttons()
        html.context_button(_("Host Properties"), self._host.edit_url(), "back")

        host_renaming_job = RenameHostBackgroundJob(self._host)
        if host_renaming_job.is_available():
            html.context_button(_("Last result"), host_renaming_job.detail_url(), "background_job_details")


    def action(self):
        if watolib.get_number_of_pending_changes():
            raise MKUserError("newname", _("You cannot rename a host while you have pending changes."))

        newname = html.var("newname")
        self._check_new_host_name("newname", newname)
        c = wato_confirm(_("Confirm renaming of host"),
                         _("Are you sure you want to rename the host <b>%s</b> into <b>%s</b>? "
                           "This involves a restart of the monitoring core!") %
                         (self._host.name(), newname))
        if c:
            # Creating pending entry. That makes the site dirty and that will force a sync of
            # the config to that site before the automation is being done.
            host_renaming_job = RenameHostBackgroundJob(self._host, title=_("Renaming of %s -> %s") % (self._host.name(), newname))
            renamings = [(watolib.Folder.current(), self._host.name(), newname)]
            host_renaming_job.set_function(rename_hosts_background_job, renamings)

            try:
                host_renaming_job.start()
            except background_job.BackgroundJobAlreadyRunning, e:
                raise MKGeneralException(_("Another host renaming job is already running: %s") % e)

            html.response.http_redirect(host_renaming_job.detail_url())

        elif c == False: # not yet confirmed
            return ""


    def _check_new_host_name(self, varname, host_name):
        if not host_name:
            raise MKUserError(varname, _("Please specify a host name."))
        elif watolib.Folder.current().has_host(host_name):
            raise MKUserError(varname, _("A host with this name already exists in this folder."))
        watolib.validate_host_uniqueness(varname, host_name)
        Hostname().validate_value(host_name, varname)


    def page(self):
        html.help(_("The renaming of hosts is a complex operation since a host's name is being "
                   "used as a unique key in various places. It also involves stopping and starting "
                   "of the monitoring core. You cannot rename a host while you have pending changes."))

        html.begin_form("rename_host", method="POST")
        forms.header(_("Rename host %s") % self._host.name())
        forms.section(_("Current name"))
        html.write_text(self._host.name())
        forms.section(_("New name"))
        html.text_input("newname", "")
        forms.end()
        html.set_focus("newname")
        html.button("rename", _("Rename host!"), "submit")
        html.hidden_fields()
        html.end_form()


def rename_host_in_folder(folder, oldname, newname):
    folder.rename_host(oldname, newname)
    return [ "folder" ]


def rename_host_as_cluster_node(all_hosts, oldname, newname):
    clusters = []
    for somehost in all_hosts.values():
        if somehost.is_cluster():
            if somehost.rename_cluster_node(oldname, newname):
                clusters.append(somehost.name())
    if clusters:
        return [ "cluster_nodes" ] * len(clusters)
    return []


def rename_host_in_parents(oldname, newname):
    parents = rename_host_as_parent(oldname, newname)
    return [ "parents" ] * len(parents)


def rename_host_as_parent(oldname, newname, in_folder=None):
    if in_folder == None:
        in_folder = watolib.Folder.root_folder()

    parents = []
    for somehost in in_folder.hosts().values():
        if somehost.has_explicit_attribute("parents"):
            if somehost.rename_parent(oldname, newname):
                parents.append(somehost.name())

    if in_folder.has_explicit_attribute("parents"):
        if in_folder.rename_parent(oldname, newname):
            parents.append(in_folder.name())

    for subfolder in in_folder.all_subfolders().values():
        parents += rename_host_as_parent(oldname, newname, subfolder)

    return parents


def rename_host_in_rulesets(folder, oldname, newname):
    # Rules that explicitely name that host (no regexes)
    changed_rulesets = []

    def rename_host_in_folder_rules(folder):
        rulesets = watolib.FolderRulesets(folder)
        rulesets.load()

        changed = False
        for varname, ruleset in rulesets.get_rulesets().items():
            for _rule_folder, _rulenr, rule in ruleset.get_rules():
                # TODO: Move to rule?
                if watolib.rename_host_in_list(rule.host_list, oldname, newname):
                    changed_rulesets.append(varname)
                    changed = True


        if changed:
            add_change("edit-ruleset", _("Renamed host in %d rulesets of folder %s") %
                                                    (len(changed_rulesets), folder.title),
                obj=folder,
                sites=folder.all_site_ids())
            rulesets.save()

        for subfolder in folder.all_subfolders().values():
            rename_host_in_folder_rules(subfolder)

    rename_host_in_folder_rules(watolib.Folder.root_folder())
    if changed_rulesets:
        actions = []
        unique = set(changed_rulesets)
        for varname in unique:
            actions += [ "wato_rules" ] * changed_rulesets.count(varname)
        return actions
    return []


def rename_host_in_event_rules(oldname, newname):
    actions = []

    def rename_in_event_rules(rules):
        num_changed = 0
        for rule in rules:
            for key in [ "match_hosts", "match_exclude_hosts" ]:
                if rule.get(key):
                    if watolib.rename_host_in_list(rule[key], oldname, newname):
                        num_changed += 1
        return num_changed

    users = userdb.load_users(lock = True)
    some_user_changed = False
    for user in users.itervalues():
        if user.get("notification_rules"):
            rules = user["notification_rules"]
            num_changed = rename_in_event_rules(rules)
            if num_changed:
                actions += [ "notify_user" ] * num_changed
                some_user_changed = True

    rules = watolib.load_notification_rules()
    num_changed = rename_in_event_rules(rules)
    if num_changed:
        actions += [ "notify_global" ] * num_changed
        watolib.save_notification_rules(rules)

    try:
        import cmk.gui.cee.plugins.wato.alert_handling as alert_handling
    except:
        alert_handling = None

    if alert_handling:
        rules = alert_handling.load_alert_handler_rules()
        if rules:
            num_changed = rename_in_event_rules(rules)
            if num_changed:
                actions += [ "alert_rules" ] * num_changed
                alert_handling.save_alert_handler_rules(rules)

    # Notification channels of flexible notifications also can have host conditions
    for user in users.itervalues():
        method = user.get("notification_method")
        if method and type(method) == tuple and method[0] == "flexible":
            channels_changed = 0
            for channel in method[1]:
                if channel.get("only_hosts"):
                    num_changed = watolib.rename_host_in_list(channel["only_hosts"], oldname, newname)
                    if num_changed:
                        channels_changed += 1
                        some_user_changed = True
            if channels_changed:
                actions += [ "notify_flexible" ] * channels_changed

    if some_user_changed:
        userdb.save_users(users)

    return actions


def rename_host_in_multisite(oldname, newname):
    # State of Multisite ---------------------------------------
    # Favorites of users and maybe other settings. We simply walk through
    # all directories rather then through the user database. That way we
    # are sure that also currently non-existant users are being found and
    # also only users that really have a profile.
    users_changed = 0
    total_changed = 0
    for userid in os.listdir(config.config_dir):
        if userid[0] == '.':
            continue
        if not os.path.isdir(config.config_dir + "/" + userid):
            continue

        favpath = config.config_dir + "/" + userid + "/favorites.mk"
        num_changed = 0
        favorites = store.load_data_from_file(favpath, [], lock=True)
        for nr, entry in enumerate(favorites):
            if entry == oldname:
                favorites[nr] = newname
                num_changed += 1
            elif entry.startswith(oldname + ";"):
                favorites[nr] = newname + ";" + entry.split(";")[1]
                num_changed += 1

        if num_changed:
            store.save_data_to_file(favpath, favorites)
            users_changed += 1
            total_changed += num_changed
        store.release_lock(favpath)

    if users_changed:
        return [ "favorites" ] * total_changed
    return []


def rename_host_in_bi(oldname, newname):
    return cmk.gui.plugins.wato.bi.BIHostRenamer().rename_host(oldname, newname)


def rename_hosts_in_check_mk(renamings):
    action_counts = {}
    for site_id, name_pairs in group_renamings_by_site(renamings).items():
        message = _("Renamed host %s") % ", ".join(
            [_("%s into %s") % (oldname, newname) for (oldname, newname) in name_pairs])

        # Restart is done by remote automation (below), so don't do it during rename/sync
        # The sync is automatically done by the remote automation call
        add_change("renamed-hosts", message, sites=[site_id], need_restart=False)

        new_counts = watolib.check_mk_automation(site_id, "rename-hosts", [], name_pairs)

        merge_action_counts(action_counts, new_counts)
    return action_counts


def merge_action_counts(action_counts, new_counts):
    for key, count in new_counts.items():
        action_counts.setdefault(key, 0)
        action_counts[key] += count


def group_renamings_by_site(renamings):
    renamings_per_site = {}
    for folder, oldname, newname in renamings:
        host = folder.host(newname) # already renamed here!
        site_id = host.site_id()
        renamings_per_site.setdefault(site_id, []).append((oldname, newname))
    return renamings_per_site


# renamings is a list of tuples of (folder, oldname, newname)
def rename_hosts(renamings, job_interface=None):
    actions = []
    all_hosts = watolib.Host.all()

    # 1. Fix WATO configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    job_interface.send_progress_update(_("Renaming WATO configuration..."))
    for folder, oldname, newname in renamings:
        try:
            this_host_actions = []
            job_interface.send_progress_update(_("Renaming host(s) in folders..."))
            this_host_actions += rename_host_in_folder(folder, oldname, newname)
            job_interface.send_progress_update(_("Renaming host(s) in cluster nodes..."))
            this_host_actions += rename_host_as_cluster_node(all_hosts, oldname, newname)
            job_interface.send_progress_update(_("Renaming host(s) in parents..."))
            this_host_actions += rename_host_in_parents(oldname, newname)
            job_interface.send_progress_update(_("Renaming host(s) in rulesets..."))
            this_host_actions += rename_host_in_rulesets(folder, oldname, newname)
            job_interface.send_progress_update(_("Renaming host(s) in BI aggregations..."))
            this_host_actions += rename_host_in_bi(oldname, newname)
            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException, e:
            auth_problems.append((oldname, e))

    # 2. Check_MK stuff ------------------------------------------------
    job_interface.send_progress_update(_("Renaming host(s) in base configuration, rrd, history files, etc."))
    job_interface.send_progress_update(_("This might take some time and involves a core restart..."))
    action_counts = rename_hosts_in_check_mk(successful_renamings)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    job_interface.send_progress_update(_("Renaming host(s) in notification rules..."))
    for folder, oldname, newname in successful_renamings:
        actions += rename_host_in_event_rules(oldname, newname)
        actions += rename_host_in_multisite(oldname, newname)

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    job_interface.send_progress_update(_("Calling final hooks"))
    watolib.call_hook_hosts_changed(watolib.Folder.root_folder())

    action_texts = render_renaming_actions(action_counts)
    return action_texts, auth_problems


def render_renaming_actions(action_counts):
    action_titles = {
        "folder"           : _("WATO folder"),
        "notify_user"      : _("Users' notification rule"),
        "notify_global"    : _("Global notification rule"),
        "notify_flexible"  : _("Flexible notification rule"),
        "wato_rules"       : _("Host and service configuration rule"),
        "alert_rules"      : _("Alert handler rule"),
        "parents"          : _("Parent definition"),
        "cluster_nodes"    : _("Cluster node definition"),
        "bi"               : _("BI rule or aggregation"),
        "favorites"        : _("Favorite entry of user"),
        "cache"            : _("Cached output of monitoring agent"),
        "counters"         : _("File with performance counter"),
        "agent"            : _("Baked host specific agent"),
        "agent_deployment" : _("Agent deployment status"),
        "piggyback-load"   : _("Piggyback information from other host"),
        "piggyback-pig"    : _("Piggyback information for other hosts"),
        "autochecks"       : _("Auto-disovered services of the host"),
        "logwatch"         : _("Logfile information of logwatch plugin"),
        "snmpwalk"         : _("A stored SNMP walk"),
        "rrd"              : _("RRD databases with performance data"),
        "rrdcached"        : _("RRD updates in journal of RRD Cache"),
        "pnpspool"         : _("Spool files of PNP4Nagios"),
        "nagvis"           : _("NagVis map"),
        "history"          : _("Monitoring history entries (events and availability)"),
        "retention"        : _("The current monitoring state (including acknowledgements and downtimes)"),
        "inv"              : _("Recent hardware/software inventory"),
        "invarch"          : _("History of hardware/software inventory"),
    }

    texts = []
    for what, count in sorted(action_counts.items()):
        if what.startswith("dnsfail-"):
            text = _("<b>WARNING: </b> the IP address lookup of <b>%s</b> has failed. The core has been "
                                 "started by using the address <tt>0.0.0.0</tt> for the while. "
                                 "Please update your DNS or configure an IP address for the affected host.") % what.split("-", 1)[1]
        else:
            text = action_titles.get(what, what)

        if count > 1:
            text += _(" (%d times)") % count
        texts.append(text)

    return texts


#.
#   .--Host & Services Parameters Overview pages---------------------------.
#   |        ____                                _                         |
#   |       |  _ \ __ _ _ __ __ _ _ __ ___   ___| |_ ___ _ __ ___          |
#   |       | |_) / _` | '__/ _` | '_ ` _ \ / _ \ __/ _ \ '__/ __|         |
#   |       |  __/ (_| | | | (_| | | | | | |  __/ ||  __/ |  \__ \         |
#   |       |_|   \__,_|_|  \__,_|_| |_| |_|\___|\__\___|_|  |___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for displaying and modifying the rule based host and service    |
#   | parameters. This is a host/service overview page over all things     |
#   | that can be modified via rules.                                      |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeObjectParameters(WatoMode):
    _PARAMETERS_UNKNOWN = []
    _PARAMETERS_OMIT = []

    @classmethod
    def name(cls):
        return "object_parameters"


    @classmethod
    def permissions(cls):
        return ["hosts", "rulesets"]


    def _from_vars(self):
        self._hostname = html.var("host") # may be empty in new/clone mode
        self._host = watolib.Folder.current().host(self._hostname)
        if self._host is None:
            raise MKGeneralException(_('The given host does not exist.'))
        self._host.need_permission("read")

        # TODO: Validate?
        self._service = html.get_unicode_input("service")


    def title(self):
        title = _("Parameters of") + " " + self._hostname
        if self._service:
            title += " / " + self._service
        return title


    def buttons(self):
        if self._service:
            prefix = _("Host-")
        else:
            prefix = u""
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "back")
        if self._service:
            service_status_button(self._hostname, self._service)
        else:
            host_status_button(self._hostname, "hoststatus")
        html.context_button(prefix + _("Properties"), watolib.folder_preserving_link([("mode", "edit_host"), ("host", self._hostname)]), "edit")
        html.context_button(_("Services"), watolib.folder_preserving_link([("mode", "inventory"), ("host", self._hostname)]), "services")
        if not self._host.is_cluster():
            html.context_button(prefix + _("Diagnostic"),
              watolib.folder_preserving_link([("mode", "diag_host"), ("host", self._hostname)]), "diagnose")


    def page(self):
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()

        # For services we make a special handling the for origin and parameters
        # of that service!
        if self._service:
            self._show_service_rules(all_rulesets)


        last_maingroup = None
        for groupname in sorted(watolib.g_rulespecs.get_host_groups()):
            maingroup = groupname.split("/")[0]
            for rulespec in sorted(watolib.g_rulespecs.get_by_group(groupname), key = lambda x: x.title):
                if (rulespec.item_type == 'service') == (not self._service):
                    continue # This rule is not for hosts/services

                # Open form for that group here, if we know that we have at least one rule
                if last_maingroup != maingroup:
                    last_maingroup = maingroup
                    rulegroup = watolib.get_rulegroup(maingroup)
                    forms.header(rulegroup.title, isopen = maingroup == "monconf", narrow=True, css="rulesettings")
                    html.help(rulegroup.help)

                self._output_analysed_ruleset(all_rulesets, rulespec, self._service)

        forms.end()


    def _show_service_rules(self, all_rulesets):
        serviceinfo = watolib.check_mk_automation(self._host.site_id(), "analyse-service", [self._hostname, self._service])
        if not serviceinfo:
            return

        forms.header(_("Check origin and parameters"), isopen = True, narrow=True, css="rulesettings")
        origin = serviceinfo["origin"]
        origin_txt = {
            "active"  : _("Active check"),
            "static"  : _("Manual check"),
            "auto"    : _("Inventorized check"),
            "classic" : _("Classical check"),
        }[origin]
        self._render_rule_reason(_("Type of check"), None, "", "", False, origin_txt)

        # First case: discovered checks. They come from var/check_mk/autochecks/HOST.
        if origin ==  "auto":
            checkgroup = serviceinfo["checkgroup"]
            checktype = serviceinfo["checktype"]
            if not checkgroup:
                self._render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

            # Logwatch needs a special handling, since it is not configured
            # via checkgroup_parameters but via "logwatch_rules" in a special
            # WATO module.
            elif checkgroup == "logwatch":
                rulespec = watolib.g_rulespecs.get("logwatch_rules")
                self._output_analysed_ruleset(all_rulesets, rulespec,
                                        serviceinfo["item"], serviceinfo["parameters"])

            else:
                # Note: some discovered checks have a check group but
                # *no* ruleset for discovered checks. One example is "ps".
                # That can be configured as a manual check or created by
                # inventory. But in the later case all parameters are set
                # by the inventory. This will be changed in a later version,
                # but we need to address it anyway.
                grouprule = "checkgroup_parameters:" + checkgroup
                if not watolib.g_rulespecs.exists(grouprule):
                    try:
                        rulespec = watolib.g_rulespecs.get("static_checks:" + checkgroup)
                    except KeyError:
                        rulespec = None

                    if rulespec:
                        url = watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', "static_checks:" + checkgroup), ('host', self._hostname)])
                        self._render_rule_reason(_("Parameters"), url, _("Determined by discovery"), None, False,
                                   rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))
                    else:
                        self._render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

                else:
                    rulespec = watolib.g_rulespecs.get(grouprule)
                    self._output_analysed_ruleset(all_rulesets, rulespec,
                                            serviceinfo["item"], serviceinfo["parameters"])

        elif origin == "static":
            checkgroup = serviceinfo["checkgroup"]
            checktype = serviceinfo["checktype"]
            if not checkgroup:
                html.write_text(_("This check is not configurable via WATO"))
            else:
                rulespec = watolib.g_rulespecs.get("static_checks:" + checkgroup)
                itemspec = rulespec.item_spec
                if itemspec:
                    item_text = itemspec.value_to_text(serviceinfo["item"])
                    title = rulespec.item_spec.title()
                else:
                    item_text = serviceinfo["item"]
                    title = _("Item")
                self._render_rule_reason(title, None, "", "", False, item_text)
                self._output_analysed_ruleset(all_rulesets, rulespec,
                                        serviceinfo["item"], self._PARAMETERS_OMIT)
                html.write(rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))
                html.close_td()
                html.close_tr()
                html.close_table()


        elif origin == "active":
            checktype = serviceinfo["checktype"]
            rulespec = watolib.g_rulespecs.get("active_checks:" + checktype)
            self._output_analysed_ruleset(all_rulesets, rulespec, None, serviceinfo["parameters"])

        elif origin == "classic":
            rule_nr  = serviceinfo["rule_nr"]
            rules    = all_rulesets.get("custom_checks").get_rules()
            rule_folder, rule_index, _rule = rules[rule_nr]

            url = watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', "custom_checks"), ('host', self._hostname)])
            forms.section(html.render_a(_("Command Line"), href=url))
            url = watolib.folder_preserving_link([
                ('mode', 'edit_rule'),
                ('varname', "custom_checks"),
                ('rule_folder', rule_folder.path()),
                ('rulenr', rule_index),
                ('host', self._hostname)])

            html.open_table(class_="setting")
            html.open_tr()

            html.open_td(class_="reason")
            html.a("%s %d %s %s" % (_("Rule"), rule_index + 1, _("in"), rule_folder.title()), href=url)
            html.close_td()
            html.open_td(class_=["settingvalue", "used"])
            if "command_line" in serviceinfo:
                html.tt(serviceinfo["command_line"])
            else:
                html.write_text(_("(no command line, passive check)"))
            html.close_td()

            html.close_tr()
            html.close_table()


    def _render_rule_reason(self, title, title_url, reason, reason_url, is_default, setting):
        if title_url:
            title = html.render_a(title, href=title_url)
        forms.section(title)

        if reason:
            reason = html.render_a(reason, href=reason_url)

        html.open_table(class_="setting")
        html.open_tr()
        if is_default:
            html.td(html.render_i(reason), class_="reason")
            html.td(setting, class_=["settingvalue", "unused"])
        else:
            html.td(reason, class_="reason")
            html.td(setting, class_=["settingvalue", "used"])
        html.close_tr()
        html.close_table()


    def _output_analysed_ruleset(self, all_rulesets, rulespec, service, known_settings=None):
        if known_settings is None:
            known_settings = self._PARAMETERS_UNKNOWN

        def rule_url(rule):
            return watolib.folder_preserving_link([
                ('mode',        'edit_rule'),
                ('varname',     varname),
                ('rule_folder', rule.folder.path()),
                ('rulenr',      rule.index()),
                ('host',        self._hostname),
                ('item',        watolib.mk_repr(service) if service else ''),
            ])

        varname = rulespec.name
        valuespec = rulespec.valuespec

        url = watolib.folder_preserving_link([
            ('mode', 'edit_ruleset'),
            ('varname', varname),
            ('host', self._hostname),
            ('item', watolib.mk_repr(service)),
        ])

        forms.section(html.render_a(rulespec.title, url))

        ruleset = all_rulesets.get(varname)
        setting, rules = ruleset.analyse_ruleset(self._hostname, service)

        html.open_table(class_="setting")
        html.open_tr()
        html.open_td(class_="reason")

        # Show reason for the determined value
        if len(rules) == 1:
            rule_folder, rule_index, rule = rules[0]
            url = rule_url(rule)
            html.a(_("Rule %d in %s") % (rule_index + 1, rule_folder.title()), href=rule_url(rule))

        elif len(rules) > 1:
            html.a("%d %s" % (len(rules), _("Rules")), href=url)

        else:
            html.i(_("Default Value"))
        html.close_td()

        # Show the resulting value or factory setting
        html.open_td(class_=["settingvalue", "used" if len(rules) > 0 else "unused"])

        # In some cases we now the settings from a check_mk automation
        if known_settings is self._PARAMETERS_OMIT:
            return

        # Special handling for logwatch: The check parameter is always None. The actual
        # patterns are configured in logwatch_rules. We do not have access to the actual
        # patterns here but just to the useless "None". In order not to complicate things
        # we simply display nothing here.
        elif varname == "logwatch_rules":
            pass

        elif known_settings is not self._PARAMETERS_UNKNOWN:
            try:
                html.write(valuespec.value_to_text(known_settings))
            except Exception, e:
                if config.debug:
                    raise
                html.write_text(_("Invalid parameter %r: %s") % (known_settings, e))

        else:
            # For match type "dict" it can be the case the rule define some of the keys
            # while other keys are taken from the factory defaults. We need to show the
            # complete outcoming value here.
            if rules and ruleset.match_type() == "dict":
                if rulespec.factory_default is not watolib.Rulespec.NO_FACTORY_DEFAULT \
                    and rulespec.factory_default is not watolib.Rulespec.FACTORY_DEFAULT_UNUSED:
                    fd = rulespec.factory_default.copy()
                    fd.update(setting)
                    setting = fd

            if valuespec and not rules: # show the default value
                if rulespec.factory_default is watolib.Rulespec.FACTORY_DEFAULT_UNUSED:
                    # Some rulesets are ineffective if they are empty
                    html.write_text(_("(unused)"))

                elif rulespec.factory_default is not watolib.Rulespec.NO_FACTORY_DEFAULT:
                    # If there is a factory default then show that one
                    setting = rulespec.factory_default
                    html.write(valuespec.value_to_text(setting))

                elif ruleset.match_type() in ("all", "list"):
                    # Rulesets that build lists are empty if no rule matches
                    html.write_text(_("(no entry)"))

                else:
                    # Else we use the default value of the valuespec
                    html.write(valuespec.value_to_text(valuespec.default_value()))

            # We have a setting
            elif valuespec:
                if ruleset.match_type() == "all":
                    html.write(", ".join([valuespec.value_to_text(e) for e in setting]))
                else:
                    html.write(valuespec.value_to_text(setting))

            # Binary rule, no valuespec, outcome is True or False
            else:
                html.img("images/rule_%s%s.png" % ("yes" if setting else "no", "_off" if not rules else ''),
                         class_="icon", align="absmiddle", title=_("yes") if setting else _("no"))
        html.close_td()
        html.close_tr()
        html.close_table()


#.
#   .--Discovery & Services------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for doing the discovery on a single host and/or showing and     |
#   | editing the current services of a host.                              |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeDiscovery(WatoMode):
    #TODO In the future cleanup check_source (passive/active/custom/legacy) and
    # check_state:
    # - passive: new/vanished/old/ignored/removed
    # - active/custom/legacy: old/ignored
    SERVICE_UNDECIDED = "new"
    SERVICE_VANISHED  = "vanished"
    SERVICE_MONITORED = "old"
    SERVICE_IGNORED   = "ignored"
    SERVICE_REMOVED   = "removed"

    SERVICE_MANUAL         = "manual"
    SERVICE_ACTIVE         = "active"
    SERVICE_CUSTOM         = "custom"
    SERVICE_LEGACY         = "legacy"
    SERVICE_CLUSTERED_OLD  = "clustered_old"
    SERVICE_CLUSTERED_NEW  = "clustered_new"
    SERVICE_ACTIVE_IGNORED = "active_ignored"
    SERVICE_CUSTOM_IGNORED = "custom_ignored"
    SERVICE_LEGACY_IGNORED = "legacy_ignored"

    @classmethod
    def name(cls):
        return "inventory"


    @classmethod
    def permissions(cls):
        return ["hosts"]


    def _from_vars(self):
        self._host_name = html.var("host")
        self._host = watolib.Folder.current().host(self._host_name)
        if not self._host:
            raise MKGeneralException(_("You called this page with an invalid host name."))

        self._host.need_permission("read")
        self._do_scan = html.has_var("_scan")
        self._already_scanned = False
        if config.user.may("wato.services"):
            if html.has_var("_show_checkboxes"):
                config.user.save_file("discovery_checkboxes", html.var("_show_checkboxes") == "1")
            cache_options = ["@scan"] if self._do_scan else ["@noscan"]
            self._show_checkboxes = config.user.load_file("discovery_checkboxes", False)
        else:
            cache_options = ["@noscan"]
            self._show_checkboxes = False

        if html.has_var("_hide_parameters"):
            config.user.save_file("parameter_column", html.var("_hide_parameters") == "no")

        # Read current check configuration
        if html.var("ignoreerrors"):
            error_options = []
        else:
            error_options = ["@raiseerrors"]
        self._options = cache_options + error_options + [self._host_name]
        self._fixall = html.var("_fixall")


    def title(self):
        title = _("Services of host %s") % self._host_name
        if self._do_scan:
            title += _(" (live scan)")
        else:
            title += _(" (might be cached data)")
        return title


    def buttons(self):
        global_buttons()
        html.context_button(_("Folder"),
             watolib.folder_preserving_link([("mode", "folder")]), "back")

        host_status_button(self._host_name, "host")

        html.context_button(_("Properties"), watolib.folder_preserving_link([
                                                ("mode", "edit_host"),
                                                ("host", self._host_name)]), "edit")

        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"), watolib.folder_preserving_link([
                                                    ("mode", "object_parameters"),
                                                    ("host", self._host_name)]), "rulesets")
            if self._host.is_cluster():
                html.context_button(_("Clustered services"),
                     watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                             ("varname", "clustered_services")]), "rulesets")

        if not self._host.is_cluster():
            # only display for non cluster hosts
            html.context_button(_("Diagnostic"),
                 watolib.folder_preserving_link([("mode", "diag_host"),
                                         ("host", self._host_name)]), "diagnose")


    def action(self):
        if not html.check_transaction():
            return
        host     = self._host
        hostname = self._host.name()
        config.user.need_permission("wato.services")
        if html.var("_refresh"):
            self._automatic_refresh_discovery(hostname)
        else:
            self._do_discovery(host)
        if not host.locked():
            self._host.clear_discovery_failed()


    def _automatic_refresh_discovery(self, hostname):
        config.user.need_permission("wato.service_discovery_to_undecided")
        config.user.need_permission("wato.service_discovery_to_monitored")
        config.user.need_permission("wato.service_discovery_to_ignored")
        config.user.need_permission("wato.service_discovery_to_removed")

        counts, _failed_hosts = watolib.check_mk_automation(self._host.site_id(), "inventory",
                                                   ["@scan", "refresh", hostname])
        count_added, _count_removed, _count_kept, _count_new = counts[hostname]
        message = _("Refreshed check configuration of host '%s' with %d services") % \
                    (hostname, count_added)
        add_service_change(self._host, "refresh-autochecks", message)
        return message


    def _do_discovery(self, host):
        check_table = self._get_check_table()
        services_to_save, remove_disabled_rule, add_disabled_rule = {}, [], []
        apply_changes = False
        for table_source, check_type, _checkgroup, item, paramstring, _params, \
            descr, _state, _output, _perfdata in check_table:

            table_target = self._get_table_target(table_source, check_type, item)

            if table_source != table_target:
                if table_target == self.SERVICE_UNDECIDED:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target in [self.SERVICE_MONITORED, self.SERVICE_CLUSTERED_NEW,
                                      self.SERVICE_CLUSTERED_OLD]:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target == self.SERVICE_IGNORED:
                    config.user.need_permission("wato.service_discovery_to_ignored")
                elif table_target == self.SERVICE_REMOVED:
                    config.user.need_permission("wato.service_discovery_to_removed")

                if not apply_changes:
                    apply_changes = True

            if table_source == self.SERVICE_UNDECIDED:
                if table_target == self.SERVICE_MONITORED:
                    services_to_save[(check_type, item)] = paramstring
                elif table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_VANISHED:
                if table_target != self.SERVICE_REMOVED:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_MONITORED:
                if table_target in [self.SERVICE_MONITORED, self.SERVICE_IGNORED]:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source == self.SERVICE_IGNORED:
                if table_target in [self.SERVICE_MONITORED, self.SERVICE_UNDECIDED,
                                    self.SERVICE_VANISHED]:
                    remove_disabled_rule.append(descr)
                if table_target in [self.SERVICE_MONITORED, self.SERVICE_IGNORED]:
                    services_to_save[(check_type, item)] = paramstring
                if table_target == self.SERVICE_IGNORED:
                    add_disabled_rule.append(descr)

            elif table_source in [self.SERVICE_CLUSTERED_NEW, self.SERVICE_CLUSTERED_OLD]:
                services_to_save[(check_type, item)] = paramstring

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                self._save_host_service_enable_disable_rules(remove_disabled_rule, add_disabled_rule)
                need_sync = True
            self._save_services(services_to_save, need_sync)


    def page(self):
        try:
            check_table = self._get_check_table()
        except Exception, e:
            logger.exception()
            if config.debug:
                raise
            retry_link = html.render_a(
                content=_("Retry discovery while ignoring this error (Result might be incomplete)."),
                href=html.makeuri([("ignoreerrors", "1"), ("_scan", "")])
            )
            html.show_warning("<b>%s</b>: %s<br><br>%s" %
                              (_("Service discovery failed for this host"), e, retry_link))
            return

        if not check_table and self._host.is_cluster():
            url = watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                  ("varname", "clustered_services")])
            html.show_info(_("Could not find any service for your cluster. You first need to "
                             "specify which services of your nodes shal be added to the "
                             "cluster. This is done using the <a href=\"%s\">%s</a> ruleset.") %
                                (url, _("Clustered services")))
            return

        map_icons = {self.SERVICE_UNDECIDED: "undecided",
                     self.SERVICE_MONITORED: "monitored",
                     self.SERVICE_IGNORED: "disabled"}

        html.begin_form("checks_action", method = "POST")
        self._show_action_buttons(check_table)
        html.hidden_fields()
        html.end_form()

        by_group = {}
        for entry in check_table:
            by_group.setdefault(entry[0], [])
            by_group[entry[0]].append(entry)

        for table_group, show_bulk_actions, header, help_text in self._ordered_table_groups():
            checks = by_group.get(table_group, [])
            if not checks:
                continue

            html.begin_form("checks_%s" % table_group, method = "POST")
            table.begin(css="data", searchable=False, limit=None, sortable=False)
            if table_group in map_icons:
                group_header = "%s %s" % (html.render_icon("%s_service" % map_icons[table_group]), header)
            else:
                group_header = header
            table.groupheader(group_header + html.render_help(help_text))

            if show_bulk_actions and len(checks) > 10:
                self._bulk_actions(table_group, collect_headers=False)

            for check in sorted(checks, key=lambda c: c[6].lower()):
                self._check_row(check, show_bulk_actions)

            if show_bulk_actions:
                self._bulk_actions(table_group, collect_headers="finished")

            table.end()
            html.hidden_fields()
            html.end_form()

    #   .--action helper-------------------------------------------------------.

    def _save_services(self, checks, need_sync):
        host = self._host
        hostname = host.name()
        message = _("Saved check configuration of host '%s' with %d services") % \
                    (hostname, len(checks))
        add_service_change(host, "set-autochecks", message, need_sync=need_sync)
        watolib.check_mk_automation(host.site_id(), "set-autochecks", [hostname], checks)


    def _save_host_service_enable_disable_rules(self, to_enable, to_disable):
        self._save_service_enable_disable_rules(to_enable, value=False)
        self._save_service_enable_disable_rules(to_disable, value=True)


    # Load all disabled services rules from the folder, then check whether or not there is a
    # rule for that host and check whether or not it currently disabled the services in question.
    # if so, remove them and save the rule again.
    # Then check whether or not the services are still disabled (by other rules). If so, search
    # for an existing host dedicated negative rule that enables services. Modify this or create
    # a new rule to override the disabling of other rules.
    #
    # Do the same vice versa for disabling services.
    def _save_service_enable_disable_rules(self, services, value):
        if not services:
            return

        def _compile_patterns(services):
            return ["%s$" % s.replace("\\", "\\\\") for s in services]

        rulesets = watolib.AllRulesets()
        rulesets.load()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = watolib.Ruleset("ignored_services")

        modified_folders = []

        service_patterns = _compile_patterns(services)
        modified_folders += self._remove_from_rule_of_host(ruleset, service_patterns, value=not value)

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        for service in services[:]:
            value_without_host_rule = ruleset.analyse_ruleset(self._host.name(), service)[0]
            if (value == False and value_without_host_rule in [None, False]) \
               or value == value_without_host_rule:
                services.remove(service)

        service_patterns = _compile_patterns(services)
        modified_folders += self._update_rule_of_host(ruleset, service_patterns, value=value)

        for folder in modified_folders:
            rulesets.save_folder(folder)


    def _remove_from_rule_of_host(self, ruleset, service_patterns, value):
        other_rule = self._get_rule_of_host(ruleset, value)
        if other_rule:
            disable_patterns = set(other_rule.item_list).difference(service_patterns)
            other_rule.item_list = sorted(list(disable_patterns))

            if not other_rule.item_list:
                ruleset.delete_rule(other_rule)

            return [ other_rule.folder ]

        return []


    def _update_rule_of_host(self, ruleset, service_patterns, value):
        folder = self._host.folder()
        rule = self._get_rule_of_host(ruleset, value)

        if rule:
            rule.item_list = sorted(list(set(service_patterns).union(rule.item_list)))
            if not rule.item_list:
                ruleset.delete_rule(rule)

        elif service_patterns:
            rule = watolib.Rule.create(folder, ruleset, [self._host.name()],
                               sorted(service_patterns))
            rule.value = value
            ruleset.prepend_rule(folder, rule)

        if rule:
            return [rule.folder]
        return []


    def _get_rule_of_host(self, ruleset, value):
        for _folder, _index, rule in ruleset.get_rules():
            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None


    def _get_table_target(self, table_source, check_type, item):
        if self._fixall:
            if table_source == self.SERVICE_VANISHED:
                return self.SERVICE_REMOVED
            elif table_source == self.SERVICE_IGNORED:
                return self.SERVICE_IGNORED
            #table_source in [self.SERVICE_MONITORED, self.SERVICE_UNDECIDED]
            return self.SERVICE_MONITORED

        bulk_target = None
        for target in [self.SERVICE_MONITORED, self.SERVICE_UNDECIDED,
                       self.SERVICE_IGNORED, self.SERVICE_REMOVED]:
            if html.has_var("_bulk_%s_%s" % (table_source, target)):
                bulk_target = target
                break
        checkbox_var_value = html.var(self._checkbox_name(check_type, item))
        if bulk_target and (checkbox_var_value == "on" or not self._show_checkboxes):
            return bulk_target
        elif checkbox_var_value:
            return checkbox_var_value
        return table_source

    #.
    #   .--page helper---------------------------------------------------------.

    def _show_action_buttons(self, check_table):
        if not config.user.may("wato.services"):
            return

        fixall = 0
        already_has_services = False
        for check in check_table:
            if check[0] in [self.SERVICE_MONITORED, self.SERVICE_VANISHED]:
                already_has_services = True
            if check[0] in [self.SERVICE_UNDECIDED, self.SERVICE_VANISHED]:
                fixall += 1

        if fixall >= 1:
            html.button("_fixall", _("Fix all missing/vanished"))

        if already_has_services:
            html.button("_refresh", _("Automatic refresh (tabula rasa)"))

        html.button("_scan", _("Full scan"))
        if not self._show_checkboxes:
            checkbox_uri = html.makeuri([('_show_checkboxes', '1'),
                                         ('selection', weblib.selection_id())])
            checkbox_title = _('Show checkboxes')
        else:
            checkbox_uri = html.makeuri([('_show_checkboxes', '0')])
            checkbox_title = _('Hide checkboxes')

        html.buttonlink(checkbox_uri, checkbox_title)
        if self._show_parameter_column():
            html.buttonlink(html.makeuri([("_hide_parameters", "yes")]),
                            _("Hide check parameters"))
        else:
            html.buttonlink(html.makeuri([("_hide_parameters", "no")]),
                            _("Show check parameters"))


    def _show_parameter_column(self):
        return config.user.load_file("parameter_column", False)


    def _bulk_actions(self, table_source, collect_headers):
        if not config.user.may("wato.services"):
            return

        def bulk_button(source, target, target_label, label):
            html.button("_bulk_%s_%s" % (source, target), target_label,
                        help_=_("Move %s to %s services") % (label, target))

        table.row(collect_headers=collect_headers, fixed=True)
        table.cell(css="bulkactions service_discovery", colspan=self._bulk_action_colspan())

        if self._show_checkboxes:
            label = _("selected services")
        else:
            label = _("all services")

        if table_source == self.SERVICE_MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                bulk_button(table_source, self.SERVICE_UNDECIDED, _("Undecided"), label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

        elif table_source == self.SERVICE_IGNORED:
            if config.user.may("wato.service_discovery_to_monitored"):
                bulk_button(table_source, self.SERVICE_MONITORED, _("Monitor"), label)
            if config.user.may("wato.service_discovery_to_undecided"):
                bulk_button(table_source, self.SERVICE_UNDECIDED, _("Undecided"), label)

        elif table_source == self.SERVICE_VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                html.button("_bulk_%s_removed" % table_source, _("Remove"),
                            help_=_("Remove %s services") % label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

        elif table_source == self.SERVICE_UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                bulk_button(table_source, self.SERVICE_MONITORED, _("Monitor"), label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)


    def _check_row(self, check, show_bulk_actions):
        table_source, check_type, checkgroup, item, _paramstring, params, \
            descr, state, output, _perfdata = check

        statename = short_service_state_name(state, "")
        if statename == "":
            statename = short_service_state_name(-1)
            stateclass = "state svcstate statep"
            state = 0 # for tr class
        else:
            stateclass = "state svcstate state%s" % state

        table.row(css="data", state=state)

        self._show_bulk_checkbox(check_type, item, show_bulk_actions)
        self._show_actions(check)

        table.cell(_("State"), statename, css=stateclass)
        table.cell(_("Service"), html.attrencode(descr))
        table.cell(_("Status detail"))
        if table_source in [self.SERVICE_CUSTOM, self.SERVICE_ACTIVE,
                            self.SERVICE_CUSTOM_IGNORED, self.SERVICE_ACTIVE_IGNORED]:
            div_id = "activecheck_%s" % descr
            html.div(html.render_icon("reload", cssclass="reloading"), id_=div_id)
            html.final_javascript("execute_active_check(%s, %s, %s, %s, %s);" % (
                json.dumps(self._host.site_id() or ''),
                json.dumps(self._host_name),
                json.dumps(check_type),
                json.dumps(item),
                json.dumps(div_id)
            ))
        else:
            html.write_text(output)

        if table_source in [self.SERVICE_ACTIVE, self.SERVICE_ACTIVE_IGNORED]:
            ctype = "check_" + check_type
        else:
            ctype = check_type
        manpage_url = watolib.folder_preserving_link([("mode", "check_manpage"),
                                                      ("check_type", ctype)])
        table.cell(_("Check plugin"), html.render_a(content=ctype, href=manpage_url))

        if self._show_parameter_column():
            table.cell(_("Check parameters"))
            self._show_check_parameters(table_source, check_type, checkgroup, params)


    def _show_bulk_checkbox(self, check_type, item, show_bulk_actions):
        if not self._show_checkboxes or not config.user.may("wato.services"):
            return

        if not show_bulk_actions:
            table.cell(css="checkbox")
            return

        table.cell("<input type=button class=checkgroup name=_toggle_group"
                   " onclick=\"toggle_group_rows(this);\" value=\"X\" />", sortable=False,
                   css="checkbox")
        html.checkbox(self._checkbox_name(check_type, item),
                      True, add_attr = ['title="%s"' % _('Temporarily ignore this service')])


    def _bulk_action_colspan(self):
        colspan = 5
        if self._show_parameter_column():
            colspan += 1
        if self._show_checkboxes:
            colspan += 1
        return colspan


    def _show_actions(self, check):
        def icon_button(table_source, checkbox_name, table_target, descr_target):
            html.icon_button(html.makeactionuri([(checkbox_name, table_target), ]),
                _("Move to %s services") % descr_target, "service_to_%s" % descr_target)

        def icon_button_removed(table_source, checkbox_name):
            html.icon_button(html.makeactionuri([(checkbox_name, self.SERVICE_REMOVED), ]),
                _("Remove service"), "service_to_removed")

        def rulesets_button():
            # Link to list of all rulesets affecting this service
            html.icon_button(watolib.folder_preserving_link(
                             [("mode", "object_parameters"), ("host", self._host_name),
                              ("service", descr), ]),
                _("View and edit the parameters for this service"), "rulesets")

        def check_parameters_button():
            if table_source == self.SERVICE_MANUAL:
                url = watolib.folder_preserving_link(
                             [('mode', 'edit_ruleset'), ('varname', "static_checks:" + checkgroup),
                              ('host', self._host_name)])
            else:
                ruleset_name = self._get_ruleset_name(table_source, check_type, checkgroup)
                if ruleset_name is None:
                    return

                url = watolib.folder_preserving_link(
                             [("mode", "edit_ruleset"), ("varname", ruleset_name),
                              ("host", self._host_name), ("item", watolib.mk_repr(item)), ]),

            html.icon_button(url,
                _("Edit and analyze the check parameters of this service"), "check_parameters")

        def disabled_services_button():
            html.icon_button(watolib.folder_preserving_link(
                             [("mode", "edit_ruleset"), ("varname", "ignored_services"),
                              ("host", self._host_name), ("item", watolib.mk_repr(descr)), ]),
                _("Edit and analyze the disabled services rules"), "rulesets")

        table.cell(css="buttons")
        if not config.user.may("wato.services"):
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            return

        table_source, check_type, checkgroup, item, _paramstring, _params, \
            descr, _state, _output, _perfdata = check
        checkbox_name = self._checkbox_name(check_type, item)

        num_buttons = 0
        if table_source == self.SERVICE_MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                icon_button(table_source, checkbox_name, self.SERVICE_UNDECIDED, "undecided")
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        elif table_source == self.SERVICE_IGNORED:
            if may_edit_ruleset("ignored_services"):
                if config.user.may("wato.service_discovery_to_monitored"):
                    icon_button(table_source, checkbox_name, self.SERVICE_MONITORED, "monitored")
                    num_buttons += 1
                if config.user.may("wato.service_discovery_to_ignored"):
                    icon_button(table_source, checkbox_name, self.SERVICE_UNDECIDED, "undecided")
                    num_buttons += 1
                disabled_services_button()
                num_buttons += 1

        elif table_source == self.SERVICE_VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                icon_button_removed(table_source, checkbox_name)
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        elif table_source == self.SERVICE_UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                icon_button(table_source, checkbox_name, self.SERVICE_MONITORED, "monitored")
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                icon_button(table_source, checkbox_name, self.SERVICE_IGNORED, "disabled")
                num_buttons += 1

        while num_buttons < 2:
            html.empty_icon()
            num_buttons += 1

        if table_source not in [self.SERVICE_UNDECIDED,
                                self.SERVICE_IGNORED] \
           and config.user.may('wato.rulesets'):
            rulesets_button()
            check_parameters_button()
            num_buttons += 2

        while num_buttons < 4:
            html.empty_icon()
            num_buttons += 1


    def _get_ruleset_name(self, table_source, check_type, checkgroup):
        if checkgroup == "logwatch":
            return "logwatch_rules"
        elif checkgroup:
            return "checkgroup_parameters:" + checkgroup
        elif table_source in [self.SERVICE_ACTIVE, self.SERVICE_ACTIVE_IGNORED]:
            return "active_checks:" + check_type
        return None


    def _show_check_parameters(self, table_source, check_type, checkgroup, params):
        varname = self._get_ruleset_name(table_source, check_type, checkgroup)
        if varname and watolib.g_rulespecs.exists(varname):
            rulespec = watolib.g_rulespecs.get(varname)
            try:
                if isinstance(params, dict) and "tp_computed_params" in params:
                    html.write_text(_("Timespecific parameters computed at %s") % cmk.render.date_and_time(params["tp_computed_params"]["computed_at"]))
                    html.br()
                    params = params["tp_computed_params"]["params"]
                rulespec.valuespec.validate_datatype(params, "")
                rulespec.valuespec.validate_value(params, "")
                paramtext = rulespec.valuespec.value_to_text(params)
                html.write_html(paramtext)
            except Exception, e:
                if config.debug:
                    err = traceback.format_exc()
                else:
                    err = e
                paramtext = _("Invalid check parameter: %s!") % err
                paramtext += _(" The parameter is: %r") % (params,)
                paramtext += _(" The variable name is: %s") % varname
                html.write_text(paramtext)

    #.
    #   .--common helper-------------------------------------------------------.

    def _get_check_table(self):
        options = self._options[:]
        if self._do_scan and self._already_scanned and "@scan" in options:
            options.remove("@scan")
            options = ["@noscan"] + options
        if options.count("@scan"):
            self._already_scanned = True
        return watolib.check_mk_automation(self._host.site_id(), "try-inventory", options)


    def _ordered_table_groups(self):
        return [
            # table group, show bulk actions, title, help
            (self.SERVICE_UNDECIDED,      True, _("Undecided services (currently not monitored)"),
            _("These services have been found by the service discovery but are not yet added "
              "to the monitoring. You should either decide to monitor them or to permanently "
              "disable them. If you are sure that they are just transitional, just leave them "
              "until they vanish.")), # undecided
            (self.SERVICE_VANISHED,       True, _("Vanished services (monitored, but no longer exist)"),
            _("These services had been added to the monitoring by a previous discovery "
              "but the actual items that are monitored are not present anymore. This might "
              "be due to a real failure. In that case you should leave them in the monitoring. "
              "If the actually monitored things are really not relevant for the monitoring "
              "anymore then you should remove them in order to avoid UNKNOWN services in the "
              "monitoring.")),
            (self.SERVICE_MONITORED,      True, _("Monitored services"),
            _("These services had been found by a discovery and are currently configured "
              "to be monitored.")),
            (self.SERVICE_IGNORED,        True, _("Disabled services"),
            _("These services are being discovered but have been disabled by creating a rule "
              "in the rule set <i>Disabled services</i> or <i>Disabled checks</i>.")),
            (self.SERVICE_ACTIVE,         False, _("Active checks"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call classical check plugins. They have been added by a rule in the section "
              "<i>Active checks</i> or implicitely by Check_MK.")),
            (self.SERVICE_MANUAL,         False, _("Manual checks"),
            _("These services have not been found by the discovery but have been added "
              "manually by a rule in the WATO module <i>Manual checks</i>.")),
            (self.SERVICE_LEGACY,         False, _("Legacy services (defined in main.mk)"),
            _("These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
              "in <tt>main.mk</tt> or a similar configuration file.")),
            (self.SERVICE_CUSTOM,         False, _("Custom checks (defined via rule)"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call a classical check plugin, that you have installed yourself.")),
            (self.SERVICE_CLUSTERED_OLD,  False, _("Monitored clustered services (located on cluster host)"),
            _("These services have been found on this host but have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>.")),
            (self.SERVICE_CLUSTERED_NEW,  False, _("Undecided clustered services"),
            _("These services have been found on this host and have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>, but are not "
              "yet added to the active monitoring. Please either add them or permanently disable "
              "them.")),
            (self.SERVICE_ACTIVE_IGNORED, False, _("Disabled active checks"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call classical check plugins. They have been added by a rule in the section "
              "<i>Active checks</i> or implicitely by Check_MK. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
            (self.SERVICE_CUSTOM_IGNORED, False, _("Disabled custom checks (defined via rule)"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call a classical check plugin, that you have installed yourself. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
            (self.SERVICE_LEGACY_IGNORED, False, _("Disabled legacy services (defined in main.mk)"),
            _("These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
              "in <tt>main.mk</tt> or a similar configuration file. "
              "These services have been disabled by creating a rule in the rule set "
              "<i>Disabled services</i> oder <i>Disabled checks</i>.")),
        ]


    # This function returns the HTTP variable name to use for a service. This needs to be unique
    # for each host. Since this text is used as variable name, it must not contain any umlauts
    # or other special characters that are disallowed by html.parse_field_storage(). Since item
    # may contain such chars, we need to use some encoded form of it. Simple escaping/encoding
    # like we use for values of variables is not enough here.
    def _checkbox_name(self, check_type, item):
        key = u"%s_%s" % (check_type, item)
        return "_move_%s" % sha256(key.encode('utf-8')).hexdigest()

    #.



class ModeFirstDiscovery(ModeDiscovery):
    pass



class ModeAjaxExecuteCheck(WatoWebApiMode):
    def _from_vars(self):
        # TODO: Validate the site
        self._site      = html.var("site")

        self._host_name = html.var("host")
        self._host      = watolib.Folder.current().host(self._host_name)
        if not self._host:
            raise MKGeneralException(_("You called this page with an invalid host name."))

        # TODO: Validate
        self._check_type = html.var("checktype")
        # TODO: Validate
        self._item       = html.var("item")

        self._host.need_permission("read")


    def page(self):
        init_wato_datastructures(with_wato_lock=True)
        try:
            state, output = watolib.check_mk_automation(self._site, "active-check",
                                [ self._host_name, self._check_type, self._item ], sync=False)
        except Exception, e:
            state  = 3
            output = "%s" % e

        return {
            "state"      : state,
            "state_name" : short_service_state_name(state, "UNKN"),
            "output"     : output,
        }


#.
#   .--Search--------------------------------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___|  ___  __ _ _ __ ___| |__                     |
#   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
#   |                   ___) |  __/ (_| | | | (__| | | |                   |
#   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Dialog for searching for hosts                                       |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeSearch(WatoMode):
    @classmethod
    def name(cls):
        return "search"


    @classmethod
    def permissions(cls):
        return ["hosts"]


    def __init__(self):
        super(ModeSearch, self).__init__()
        self._folder = watolib.Folder.current()


    def title(self):
        return _("Search for hosts below %s") % self._folder.title()


    def buttons(self):
        global_buttons()
        html.context_button(_("Folder"), self._folder.url(), "back")


    def action(self):
        return "folder"


    def page(self):
        self._folder.show_breadcrump()

        # Show search form
        html.begin_form("edit_host", method="GET")
        html.prevent_password_auto_completion()
        forms.header(_("General Properties"))
        forms.section(_("Hostname"))
        html.text_input("host_search_host")
        html.set_focus("host_search_host")

        # Attributes
        configure_attributes(False, {}, "host_search",
                             parent=None,
                             varprefix="host_search_")

        # Button
        forms.end()
        html.button("_local", _("Search in %s") % self._folder.title(), "submit")
        html.hidden_field("host_search", "1")
        html.hidden_fields()
        html.end_form()


#.
#   .--Bulk Import---------------------------------------------------------.
#   |       ____        _ _      ___                            _          |
#   |      | __ ) _   _| | | __ |_ _|_ __ ___  _ __   ___  _ __| |_        |
#   |      |  _ \| | | | | |/ /  | || '_ ` _ \| '_ \ / _ \| '__| __|       |
#   |      | |_) | |_| | |   <   | || | | | | | |_) | (_) | |  | |_        |
#   |      |____/ \__,_|_|_|\_\ |___|_| |_| |_| .__/ \___/|_|   \__|       |
#   |                                         |_|                          |
#   +----------------------------------------------------------------------+
#   | The bulk import for hosts can be used to import multiple new hosts   |
#   | into a single WATO folder. The hosts can either be provided by       |
#   | uploading a CSV file or by pasting the contents of a CSV file into   |
#   | a textbox.                                                           |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeBulkImport(WatoMode):
    _upload_tmp_path = cmk.paths.tmp_dir + "/host-import"

    @classmethod
    def name(cls):
        return "bulk_import"


    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]


    def __init__(self):
        super(ModeBulkImport, self).__init__()
        self._csv_reader = None
        self._params = None


    def title(self):
        return _("Bulk host import")


    def buttons(self):
        html.context_button(_("Abort"), watolib.folder_preserving_link([("mode", "folder")]), "abort")
        if html.has_var("file_id"):
            html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "bulk_import")]), "back")


    def action(self):
        if html.transaction_valid():
            if html.has_var("_do_upload"):
                self._upload_csv_file()

            self._read_csv_file()

            if html.var("_do_import"):
                return self._import()


    def _file_path(self):
        file_id = html.var("file_id", "%s-%d" % (config.user.id, int(time.time())))
        return self._upload_tmp_path + "/%s.csv" % file_id


    # Upload the CSV file into a temporary directoy to make it available not only
    # for this request. It needs to be available during several potential "confirm"
    # steps and then through the upload step.
    def _upload_csv_file(self):
        store.makedirs(self._upload_tmp_path)

        self._cleanup_old_files()

        upload_info = self._vs_upload().from_html_vars("_upload")
        self._vs_upload().validate_value(upload_info, "_upload")
        _file_name, _mime_type, content = upload_info["file"]

        file_id = "%s-%d" % (config.user.id, int(time.time()))

        store.save_file(self._file_path(), content.encode("utf-8"))

        # make selections available to next page
        html.set_var("file_id", file_id)

        if upload_info["do_service_detection"]:
            html.set_var("do_service_detection", "1")


    def _cleanup_old_files(self):
        for f in os.listdir(self._upload_tmp_path):
            path = self._upload_tmp_path + "/" + f
            mtime = os.stat(path).st_mtime
            if mtime < time.time() - 3600:
                os.unlink(path)


    def _get_custom_csv_dialect(self, delim):
        class CustomCSVDialect(csv.excel):
            delimiter = delim

        return CustomCSVDialect()


    def _read_csv_file(self):
        try:
            csv_file = file(self._file_path())
        except IOError:
            raise MKUserError(None, _("Failed to read the previously uploaded CSV file. Please upload it again."))

        params = self._vs_parse_params().from_html_vars("_preview")
        self._vs_parse_params().validate_value(params, "_preview")
        self._params = params

        # try to detect the CSV format to be parsed
        if "field_delimiter" in params:
            csv_dialect = self._get_custom_csv_dialect(params["field_delimiter"])
        else:
            try:
                csv_dialect = csv.Sniffer().sniff(csv_file.read(2048), delimiters=",;\t:")
                csv_file.seek(0)
            except csv.Error, e:
                if "Could not determine delimiter" in str(e):
                    # Failed to detect the CSV files field delimiter character. Using ";" now. If
                    # you need another one, please specify it manually.
                    csv_dialect = self._get_custom_csv_dialect(";")
                    csv_file.seek(0)
                else:
                    raise


        # Save for preview in self.page()
        self._csv_reader = csv.reader(csv_file, csv_dialect)


    def _import(self):
        if self._params.get("has_title_line"):
            try:
                self._csv_reader.next() # skip header
            except StopIteration:
                pass

        num_succeeded, num_failed = 0, 0
        fail_messages = []
        selected = []

        for row in self._csv_reader:
            if not row:
                continue # skip empty lines

            host_name, attributes = self._get_host_info_from_row(row)
            try:
                watolib.Folder.current().create_hosts([(host_name, attributes, None)])
                selected.append('_c_%s' % host_name)
                num_succeeded += 1
            except Exception, e:
                fail_messages.append(_("Failed to create a host from line %d: %s") % (self._csv_reader.line_num, e))
                num_failed += 1

        self._delete_csv_file()

        msg = _("Imported %d hosts into the current folder.") % num_succeeded
        if num_failed:
            msg += "<br><br>" + (_("%d errors occured:") % num_failed)
            msg += "<ul>"
            for fail_msg in fail_messages:
                msg += "<li>%s</li>" % fail_msg
            msg += "</ul>"


        if num_succeeded > 0 and html.var("do_service_detection") == "1":
            # Create a new selection for performing the bulk discovery
            weblib.set_rowselection('wato-folder-/' + watolib.Folder.current().path(), selected, 'set')
            html.set_var('mode', 'bulkinventory')
            html.set_var('_bulk_inventory', '1')
            html.set_var('show_checkboxes', '1')
            return "bulkinventory"
        return "folder", msg


    def _delete_csv_file(self):
        os.unlink(self._file_path())


    def _get_host_info_from_row(self, row):
        host_name = None
        attributes = {}
        for col_num, value in enumerate(row):
            attribute = html.var("attribute_%d" % col_num)
            if attribute == "host_name":
                Hostname().validate_value(value, "host")
                host_name = value

            elif attribute and attribute != "-":
                if attribute in attributes:
                    raise MKUserError(None, _("The attribute \"%s\" is assigned to multiple columns. "
                                              "You can not populate one attribute from multiple columns. "
                                              "The column to attribute associations need to be unique.") % attribute)

                # FIXME: Couldn't we decode all attributes?
                if attribute == "alias":
                    attributes[attribute] = value.decode("utf-8")
                else:
                    try:
                        unicode(value)
                    except:
                        raise MKUserError(None, _("Non-ASCII characters are not allowed in the "
                                                  "attribute \"%s\".") % attribute)
                    attributes[attribute] = value

        if host_name == None:
            raise MKUserError(None, _("The host name attribute needs to be assigned to a column."))

        return host_name, attributes


    def page(self):
        if not html.has_var("file_id"):
            self._upload_form()
        else:
            self._preview()


    def _upload_form(self):
        html.begin_form("upload", method="POST")
        html.p(_("Using this page you can import several hosts at once into the choosen folder. You can "
                 "choose a CSV file from your workstation to be uploaded, paste a CSV files contents "
                 "into the textarea or simply enter a list of hostnames (one per line) to the textarea."))

        self._vs_upload().render_input("_upload", None)
        html.hidden_fields()
        html.button("_do_upload", _("Upload"))
        html.end_form()


    def _vs_upload(self):
        return Dictionary(
            elements = [
                ("file", UploadOrPasteTextFile(
                    title = _("Import Hosts"),
                    file_title = _("CSV File"),
                    allow_empty = False,
                    default_mode = "upload",
                )),
                ("do_service_detection", Checkbox(
                    title = _("Perform automatic service discovery"),
                )),
            ],
            render = "form",
            title = _("Import Hosts"),
            optional_keys = [],
        )


    def _preview(self):
        html.begin_form("preview", method="POST")
        self._preview_form()

        attributes = self._attribute_choices()

        self._read_csv_file() # first line could be missing in situation of import error
        if not self._csv_reader:
            return # don't try to show preview when CSV could not be read

        html.h2(_("Preview"))
        attribute_list = "<ul>%s</ul>" % "".join([ "<li>%s (%s)</li>" % a for a in attributes if a[0] != None ])
        html.help(
            _("This list shows you the first 10 rows from your CSV file in the way the import is "
              "currently parsing it. If the lines are not splitted correctly or the title line is "
              "not shown as title of the table, you may change the import settings above and try "
              "again.") + "<br><br>" +
             _("The first row below the titles contains fields to specify which column of the "
               "CSV file should be imported to which attribute of the created hosts. The import "
               "progress is trying to match the columns to attributes automatically by using the "
               "titles found in the title row (if you have some). "
               "If you use the correct titles, the attributes can be mapped automatically. The "
               "currently available attributes are:") + attribute_list +
             _("You can change these assignments according to your needs and then start the "
               "import by clicking on the <i>Import</i> button above."))

        # Wenn bei einem Host ein Fehler passiert, dann wird die Fehlermeldung zu dem Host angezeigt, so dass man sehen kann, was man anpassen muss.
        # Die problematischen Zeilen sollen angezeigt werden, so dass man diese als Block in ein neues CSV-File eintragen kann und dann diese Datei
        # erneut importieren kann.
        if self._params.get("has_title_line"):
            try:
                headers = list(self._csv_reader.next())
            except StopIteration:
                headers = [] # nope, there is no header
        else:
            headers = []

        rows = list(self._csv_reader)

        # Determine how many columns should be rendered by using the longest column
        num_columns = max([ len(r) for r in [headers] + rows ])

        table.begin(sortable=False, searchable=False, omit_headers = not self._params.get("has_title_line"))

        # Render attribute selection fields
        table.row()
        for col_num in range(num_columns):
            header = headers[col_num] if len(headers) > col_num else None
            table.cell(html.render_text(header))
            attribute_varname = "attribute_%d" % col_num
            if html.var(attribute_varname):
                attribute_method = html.var("attribute_varname")
            else:
                attribute_method = self._try_detect_default_attribute(attributes, header)
                html.del_var(attribute_varname)

            html.dropdown("attribute_%d" % col_num, attributes, deflt=attribute_method, autocomplete="off")

        # Render sample rows
        for row in rows:
            table.row()
            for cell in row:
                table.cell(None, html.render_text(cell))

        table.end()
        html.end_form()


    def _preview_form(self):
        if self._params != None:
            params = self._params
        else:
            params = self._vs_parse_params().default_value()
        self._vs_parse_params().render_input("_preview", params)
        html.hidden_fields()
        html.button("_do_preview", _("Update preview"))
        html.button("_do_import", _("Import"))


    def _vs_parse_params(self):
        return Dictionary(
            elements = [
                ("field_delimiter", TextAscii(
                    title = _("Set field delimiter"),
                    default_value = ";",
                    size = 1,
                    allow_empty = False,
                )),
                ("has_title_line", FixedValue(True,
                    title = _("Has title line"),
                    totext = _("The first line in the file contains titles."),
                )),
            ],
            render = "form",
            title = _("File Parsing Settings"),
            default_keys = ["has_title_line"],
        )


    def _attribute_choices(self):
        attributes = [
            (None,              _("(please select)")),
            ("-",               _("Don't import")),
            ("host_name",       _("Hostname")),
            ("alias",           _("Alias")),
            ("site",            _("Monitored on site")),
            ("ipaddress",       _("IPv4 Address")),
            ("ipv6address",     _("IPv6 Address")),
            ("snmp_community",  _("SNMP Community")),
        ]

        # Add tag groups
        for entry in config.host_tag_groups():
            attributes.append(("tag_" + entry[0], _("Tag: %s") % entry[1]))

        # Add custom attributes
        for entry in ModeCustomHostAttrs().get_attributes():
            name = entry['name']
            attributes.append((name, _("Custom variable: %s") % name))

        return attributes


    # Try to detect the host attribute to choose for this column based on the header
    # of this column (if there is some).
    def _try_detect_default_attribute(self, attributes, header):
        if header == None:
            return ""

        from difflib import SequenceMatcher
        def similarity(a, b):
            return SequenceMatcher(None, a, b).ratio()

        highscore = 0.0
        best_key = ""
        for key, title in attributes:
            if key != None:
                key_match_score = similarity(key, header)
                title_match_score = similarity(title, header)
                score = key_match_score if key_match_score > title_match_score else title_match_score

                if score > 0.6 and score > highscore:
                    best_key = key
                    highscore = score

        return best_key


#.
#   .--Bulk-Edit-----------------------------------------------------------.
#   |                ____        _ _      _____    _ _ _                   |
#   |               | __ ) _   _| | | __ | ____|__| (_) |_                 |
#   |               |  _ \| | | | | |/ / |  _| / _` | | __|                |
#   |               | |_) | |_| | |   <  | |__| (_| | | |_                 |
#   |               |____/ \__,_|_|_|\_\ |_____\__,_|_|\__|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Change the attributes of a number of selected host at once. Also the |
#   | cleanup is implemented here: the bulk removal of explicit attribute  |
#   | values.                                                              |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeBulkEdit(WatoMode):
    @classmethod
    def name(cls):
        return "bulkedit"


    @classmethod
    def permissions(cls):
        return ["hosts", "edit_hosts"]


    def title(self):
        return _("Bulk edit hosts")


    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "back")


    def action(self):
        if not html.check_transaction():
            return

        config.user.need_permission("wato.edit_hosts")

        changed_attributes = watolib.collect_attributes("bulk")
        host_names = get_hostnames_from_checkboxes()
        for host_name in host_names:
            host = watolib.Folder.current().host(host_name)
            host.update_attributes(changed_attributes)
            # call_hook_hosts_changed() is called too often.
            # Either offer API in class Host for bulk change or
            # delay saving until end somehow

        return "folder", _("Edited %d hosts") % len(host_names)


    def page(self):
        host_names = get_hostnames_from_checkboxes()
        hosts = dict([(host_name, watolib.Folder.current().host(host_name)) for host_name in host_names])
        current_host_hash = sha256(repr(hosts))

        # When bulk edit has been made with some hosts, then other hosts have been selected
        # and then another bulk edit has made, the attributes need to be reset before
        # rendering the form. Otherwise the second edit will have the attributes of the
        # first set.
        host_hash = html.var("host_hash")
        if not host_hash or host_hash != current_host_hash:
            html.del_all_vars(prefix="attr_")
            html.del_all_vars(prefix="bulk_change_")

        html.p("%s%s %s" % (
            _("You have selected <b>%d</b> hosts for bulk edit. You can now change "
              "host attributes for all selected hosts at once. ") % len(hosts),
            _("If a select is set to <i>don't change</i> then currenty not all selected "
              "hosts share the same setting for this attribute. "
              "If you leave that selection, all hosts will keep their individual settings."),
            _("In case you want to <i>unset</i> attributes on multiple hosts, you need to "
              "use the <i>bulk cleanup</i> action instead of bulk edit.")))

        html.begin_form("edit_host", method = "POST")
        html.prevent_password_auto_completion()
        html.hidden_field("host_hash", current_host_hash)
        configure_attributes(False, hosts, "bulk", parent = watolib.Folder.current())
        forms.end()
        html.button("_save", _("Save & Finish"))
        html.hidden_fields()
        html.end_form()


#.
#   .--Bulk-Cleanup--------------------------------------------------------.
#   |      ____        _ _       ____ _                                    |
#   |     | __ ) _   _| | | __  / ___| | ___  __ _ _ __  _   _ _ __        |
#   |     |  _ \| | | | | |/ / | |   | |/ _ \/ _` | '_ \| | | | '_ \       |
#   |     | |_) | |_| | |   <  | |___| |  __/ (_| | | | | |_| | |_) |      |
#   |     |____/ \__,_|_|_|\_\  \____|_|\___|\__,_|_| |_|\__,_| .__/       |
#   |                                                         |_|          |
#   +----------------------------------------------------------------------+
#   | Mode for removing attributes from host in bulk mode.                 |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeBulkCleanup(WatoMode):
    @classmethod
    def name(cls):
        return "bulkcleanup"


    @classmethod
    def permissions(cls):
        return ["hosts", "edit_hosts"]


    def _from_vars(self):
        self._folder = watolib.Folder.current()


    def title(self):
        return _("Bulk removal of explicit attributes")


    def buttons(self):
        html.context_button(_("Back"), self._folder.url(), "back")


    def action(self):
        if not html.check_transaction():
            return

        config.user.need_permission("wato.edit_hosts")
        to_clean = self._bulk_collect_cleaned_attributes()
        if "contactgroups" in to_clean:
            self._folder.need_permission("write")

        hosts = get_hosts_from_checkboxes()

        # Check all permissions before doing any edit
        for host in hosts:
            host.need_permission("write")

        for host in hosts:
            host.clean_attributes(to_clean)

        return "folder"


    def _bulk_collect_cleaned_attributes(self):
        to_clean = []
        for attr, _topic in watolib.all_host_attributes():
            attrname = attr.name()
            if html.get_checkbox("_clean_" + attrname) == True:
                to_clean.append(attrname)
        return to_clean


    def page(self):
        hosts = get_hosts_from_checkboxes()

        html.p(_("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
                 "explicit attribute values from hosts. The hosts will then inherit attributes "
                 "configured at the host list or folders or simply fall back to the builtin "
                 "default values.") % len(hosts))

        html.begin_form("bulkcleanup", method = "POST")
        forms.header(_("Attributes to remove from hosts"))
        if not self._select_attributes_for_bulk_cleanup(hosts):
            forms.end()
            html.write_text(_("The selected hosts have no explicit attributes"))
        else:
            forms.end()
            html.button("_save", _("Save & Finish"))
        html.hidden_fields()
        html.end_form()


    def _select_attributes_for_bulk_cleanup(self, hosts):
        num_shown = 0
        for attr, _topic in watolib.all_host_attributes():
            attrname = attr.name()

            # only show attributes that at least on host have set
            num_haveit = 0
            for host in hosts:
                if host.has_explicit_attribute(attrname):
                    num_haveit += 1

            if num_haveit == 0:
                continue

            # If the attribute is mandatory and no value is inherited
            # by file or folder, the attribute cannot be cleaned.
            container = self._folder
            is_inherited = False
            while container:
                if container.has_explicit_attribute(attrname):
                    is_inherited = True
                    break
                container = container.parent()

            num_shown += 1

            # Legend and Help
            forms.section(attr.title())

            if attr.is_mandatory() and not is_inherited:
                html.write_text(_("This attribute is mandatory and there is no value "
                                  "defined in the host list or any parent folder."))
            else:
                label = "clean this attribute on <b>%s</b> hosts" % \
                    (num_haveit == len(hosts) and "all selected" or str(num_haveit))
                html.checkbox("_clean_%s" % attrname, False, label=label)
            html.help(attr.help())

        return num_shown > 0

#.
#   .--Parentscan----------------------------------------------------------.
#   |          ____                      _                                 |
#   |         |  _ \ __ _ _ __ ___ _ __ | |_ ___  ___ __ _ _ __            |
#   |         | |_) / _` | '__/ _ \ '_ \| __/ __|/ __/ _` | '_ \           |
#   |         |  __/ (_| | | |  __/ | | | |_\__ \ (_| (_| | | | |          |
#   |         |_|   \__,_|_|  \___|_| |_|\__|___/\___\__,_|_| |_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Automatic scan for parents (similar to cmk --scan-parents)           |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeParentScan(WatoMode):
    @classmethod
    def name(cls):
        return "parentscan"


    @classmethod
    def permissions(cls):
        return ["hosts", "parentscan"]


    def title(self):
        return _("Parent scan")


    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")


    def _from_vars(self):
        # Ignored during initial form display
        # TODO: Make dedicated class or class members
        self._settings = {
            "where"          : html.var("where"),
            "alias"          : html.get_unicode_input("alias", "").strip() or None,
            "recurse"        : html.get_checkbox("recurse"),
            "select"         : html.var("select"),
            "timeout"        : utils.saveint(html.var("timeout")) or 8,
            "probes"         : utils.saveint(html.var("probes")) or 2,
            "max_ttl"        : utils.saveint(html.var("max_ttl")) or 10,
            "force_explicit" : html.get_checkbox("force_explicit"),
            "ping_probes"    : utils.saveint(html.var("ping_probes")) or 0,
        }

        if not html.var("all"):
            # 'all' not set -> only scan checked hosts in current folder, no recursion
            self._complete_folder = False
            self._items = []
            for host in get_hosts_from_checkboxes():
                if self._include_host(host, self._settings["select"]):
                    self._items.append("%s|%s" % (host.folder().path(), host.name()))

        else:
            # all host in this folder, maybe recursively
            self._complete_folder = True
            self._items = []
            for host in self._recurse_hosts(watolib.Folder.current(), self._settings["recurse"], self._settings["select"]):
                self._items.append("%s|%s" % (host.folder().path(), host.name()))


    def action(self):
        if not html.var("_item"):
            return

        try:
            folderpath, host_name = html.var("_item").split("|")
            folder = watolib.Folder.folder(folderpath)
            host = folder.host(host_name)
            site_id = host.site_id()
            params = map(str, [ self._settings["timeout"], self._settings["probes"], self._settings["max_ttl"], self._settings["ping_probes"] ])
            gateways = watolib.check_mk_automation(site_id, "scan-parents", params + [host_name])
            gateway, state, skipped_gateways, error = gateways[0]

            if state in [ "direct", "root", "gateway" ]:
                message, pconf, gwcreat = \
                    self._configure_gateway(state, site_id, host, gateway)
            else:
                message = error
                pconf = False
                gwcreat = False

            # Possible values for state are:
            # failed, dnserror, garbled, root, direct, notfound, gateway
            counts = [ 'continue',
                1,                                           # Total hosts
                1 if gateway else 0,                          # Gateways found
                1 if state in [ "direct", "root" ] else 0,    # Directly reachable hosts
                skipped_gateways,                            # number of failed PING probes
                1 if state == "notfound" else 0,              # No gateway found
                1 if pconf else 0,                            # New parents configured
                1 if gwcreat else 0,                          # Gateway hosts created
                1 if state in [ "failed", "dnserror", "garbled" ] else 0, # Errors
            ]
            result = "%s\n%s: %s<br>\n" % (json.dumps(counts), host_name, message)

        except Exception, e:
            result = json.dumps([ 'failed', 1, 0, 0, 0, 0, 0, 1 ]) + "\n"
            if site_id:
                msg = _("Error during parent scan of %s on site %s: %s") % (host_name, site_id, e)
            else:
                msg = _("Error during parent scan of %s: %s") % (host_name, e)
            if config.debug:
                msg += html.render_br()
                msg += html.render_pre(traceback.format_exc().replace("\n", "<br>"))
                msg += html.render_br()
            result += msg
        html.write(result)
        return ""


    def _configure_gateway(self, state, site_id, host, gateway):
        # Settings for configuration and gateway creation
        force_explicit = html.get_checkbox("force_explicit")
        where          = html.var("where")
        alias          = html.var("alias")

        # If we have found a gateway, we need to know a matching
        # host name from our configuration. If there is none,
        # we can create one, if the users wants this. The automation
        # for the parent scan already tries to find such a host
        # within the site.
        gwcreat = False

        if gateway:
            gw_host_name, gw_ip, dns_name = gateway
            if not gw_host_name:
                if where == "nowhere":
                    return _("No host %s configured, parents not set") % gw_ip, \
                        False, False

                # Determine folder where to create the host.
                elif where == "here": # directly in current folder
                    gw_folder = watolib.Folder.current_disk_folder()

                elif where == "subfolder":
                    current = watolib.Folder.current_disk_folder()
                    # Put new gateways in subfolder "Parents" of current
                    # folder. Does this folder already exist?
                    if current.has_subfolder("parents"):
                        gw_folder = current.subfolder("parents")
                    else:
                        # Create new gateway folder
                        gw_folder = current.create_subfolder("parents", _("Parents"), {})

                elif where == "there": # In same folder as host
                    gw_folder = host.folder()

                # Create gateway host
                if dns_name:
                    gw_host_name = dns_name
                elif site_id:
                    gw_host_name = "gw-%s-%s" % (site_id, gw_ip.replace(".", "-"))
                else:
                    gw_host_name = "gw-%s" % (gw_ip.replace(".", "-"))

                new_host_attributes = { "ipaddress" : gw_ip }
                if alias:
                    new_host_attributes["alias"] = alias
                if gw_folder.site_id() != site_id:
                    new_host_attributes["site"] = site_id

                gw_folder.create_hosts([(gw_host_name, new_host_attributes, None)])
                gwcreat = True

            parents = [ gw_host_name ]

        else:
            parents = []

        if host.effective_attribute("parents") == parents:
            return _("Parents unchanged at %s") %  \
                    (",".join(parents) if parents else _("none")), False, gwcreat


        if force_explicit or host.folder().effective_attribute("parents") != parents:
            host.update_attributes({"parents": parents})
        else:
            # Check which parents the host would have inherited
            if host.has_explicit_attribute("parents"):
                host.clean_attributes(["parents"])

        if parents:
            message = _("Set parents to %s") % ",".join(parents)
        else:
            message = _("Removed parents")

        return message, True, gwcreat


    def page(self):
        if html.var("_start"):
            self._show_progress_dialog()
        else:
            self._show_parameter_form()


    def _show_progress_dialog(self):
        # Persist settings
        config.user.save_file("parentscan", self._settings)

        # Start interactive progress
        interactive_progress(
            self._items,
            _("Parent scan"),  # title
            [ (_("Total hosts"),               0),
              (_("Gateways found"),            0),
              (_("Directly reachable hosts"),  0),
              (_("Unreachable gateways"),      0),
              (_("No gateway found"),          0),
              (_("New parents configured"),    0),
              (_("Gateway hosts created"),     0),
              (_("Errors"),                    0),
            ],
            [ ("mode", "folder") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
            fail_stats = [ 1 ],
        )


    def _show_parameter_form(self):
        html.begin_form("parentscan", method = "POST")
        html.hidden_fields()

        # Mode of action
        html.open_p()
        if not self._complete_folder:
            html.write_text(_("You have selected <b>%d</b> hosts for parent scan. ") % len(self._items))
        html.p(_("The parent scan will try to detect the last gateway "
                 "on layer 3 (IP) before a host. This will be done by "
                 "calling <tt>traceroute</tt>. If a gateway is found by "
                 "that way and its IP address belongs to one of your "
                 "monitored hosts, that host will be used as the hosts "
                 "parent. If no such host exists, an artifical ping-only "
                 "gateway host will be created if you have not disabled "
                 "this feature."))

        forms.header(_("Settings for Parent Scan"))

        self._settings = config.user.load_file("parentscan", {
            "where"          : "subfolder",
            "alias"          : _("Created by parent scan"),
            "recurse"        : True,
            "select"         : "noexplicit",
            "timeout"        : 8,
            "probes"         : 2,
            "ping_probes"    : 5,
            "max_ttl"        : 10,
            "force_explicit" : False,
        })

        # Selection
        forms.section(_("Selection"))
        if self._complete_folder:
            html.checkbox("recurse", self._settings["recurse"], label=_("Include all subfolders"))
            html.br()
        html.radiobutton("select", "noexplicit", self._settings["select"] == "noexplicit",
                _("Skip hosts with explicit parent definitions (even if empty)") + "<br>")
        html.radiobutton("select", "no",  self._settings["select"] == "no",
                _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>")
        html.radiobutton("select", "ignore",  self._settings["select"] == "ignore",
                _("Scan all hosts") + "<br>")

        # Performance
        forms.section(_("Performance"))
        html.open_table()
        html.open_tr()
        html.open_td()
        html.write_text(_("Timeout for responses") + ":")
        html.close_td()
        html.open_td()
        html.number_input("timeout", self._settings["timeout"], size=2)
        html.write_text(_("sec"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of probes per hop") + ":")
        html.close_td()
        html.open_td()
        html.number_input("probes", self._settings["probes"], size=2)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Maximum distance (TTL) to gateway") + ":")
        html.close_td()
        html.open_td()
        html.number_input("max_ttl", self._settings["max_ttl"], size=2)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of PING probes") + ":")
        html.help(_("After a gateway has been found, Check_MK checks if it is reachable "
                    "via PING. If not, it is skipped and the next gateway nearer to the "
                    "monitoring core is being tried. You can disable this check by setting "
                    "the number of PING probes to 0."))
        html.close_td()
        html.open_td()
        html.number_input("ping_probes", self._settings.get("ping_probes", 5), size=2)
        html.close_td()
        html.close_tr()
        html.close_table()

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox("force_explicit",
            self._settings["force_explicit"], label=_("Force explicit setting for parents even if setting matches that of the folder"))

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write_text(_("Create gateway hosts in"))
        html.open_ul()

        html.radiobutton("where", "subfolder", self._settings["where"] == "subfolder",
                _("in the subfolder <b>%s/Parents</b>") % watolib.Folder.current_disk_folder().title())

        html.br()
        html.radiobutton("where", "here", self._settings["where"] == "here",
                _("directly in the folder <b>%s</b>") % watolib.Folder.current_disk_folder().title())
        html.br()
        html.radiobutton("where", "there", self._settings["where"] == "there",
                _("in the same folder as the host"))
        html.br()
        html.radiobutton("where", "nowhere", self._settings["where"] == "nowhere",
                _("do not create gateway hosts"))
        html.close_ul()
        html.write_text(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", self._settings["alias"])

        # Start button
        forms.end()
        html.button("_start", _("Start"))


    # select: 'noexplicit' -> no explicit parents
    #         'no'         -> no implicit parents
    #         'ignore'     -> not important
    def _include_host(self, host, select):
        if select == 'noexplicit' and host.has_explicit_attribute("parents"):
            return False
        elif select == 'no':
            if host.effective_attribute("parents"):
                return False
        return True


    def _recurse_hosts(self, folder, recurse, select):
        entries = []
        for host in folder.hosts().values():
            if self._include_host(host, select):
                entries.append(host)

        if recurse:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts(subfolder, recurse, select)
        return entries

#.
#   .--Pending & Replication-----------------------------------------------.
#   |                 ____                _ _                              |
#   |                |  _ \ ___ _ __   __| (_)_ __   __ _                  |
#   |                | |_) / _ \ '_ \ / _` | | '_ \ / _` |                 |
#   |                |  __/  __/ | | | (_| | | | | | (_| |                 |
#   |                |_|   \___|_| |_|\__,_|_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Mode for activating pending changes. Does also replication with      |
#   | remote sites in distributed WATO.                                    |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeActivateChanges(WatoMode, watolib.ActivateChanges):
    @classmethod
    def name(cls):
        return "changelog"


    @classmethod
    def permissions(cls):
        return []


    def __init__(self):
        self._value = {}
        super(ModeActivateChanges, self).__init__()
        super(ModeActivateChanges, self).load()


    def title(self):
        return _("Activate pending changes")


    def buttons(self):
        home_button()

        # TODO: Remove once new changes mechanism has been implemented
        if self._may_discard_changes():
            html.context_button(_("Discard Changes!"),
                html.makeactionuri([("_action", "discard")]),
                "discard", id_="discard_changes_button")

        if config.user.may("wato.sites"):
            html.context_button(_("Site Configuration"), watolib.folder_preserving_link([("mode", "sites")]), "sites")

        if config.user.may("wato.auditlog"):
            html.context_button(_("Audit Log"), watolib.folder_preserving_link([("mode", "auditlog")]), "auditlog")



    def _may_discard_changes(self):
        if not config.user.may("wato.activate"):
            return False

        if not self.has_changes():
            return False

        if not config.user.may("wato.activateforeign") and self._has_foreign_changes_on_any_site():
            return False

        if not self._get_last_wato_snapshot_file():
            return False

        return True


    def action(self):
        if html.var("_action") != "discard":
            return

        if not html.check_transaction():
            return

        if not self._may_discard_changes():
            return

        # TODO: Remove once new changes mechanism has been implemented
        # Now remove all currently pending changes by simply restoring the last automatically
        # taken snapshot. Then activate the configuration. This should revert all pending changes.
        file_to_restore = self._get_last_wato_snapshot_file()

        if not file_to_restore:
            raise MKUserError(None, _('There is no WATO snapshot to be restored.'))

        msg = _("Discarded pending changes (Restored %s)") % file_to_restore

        # All sites and domains can be affected by a restore: Better restart everything.
        add_change("changes-discarded", msg, sites=self.activation_site_ids(),
            domains=watolib.ConfigDomain.enabled_domains(),
            need_restart=True)

        self._extract_snapshot(file_to_restore)
        watolib.execute_activate_changes([ d.ident for d in watolib.ConfigDomain.enabled_domains() ])

        for site_id in self.activation_site_ids():
            self.confirm_site_changes(site_id)

        html.header(self.title(), javascripts=["wato"], stylesheets=wato_styles,
                    show_body_start=display_options.enabled(display_options.H),
                    show_top_heading=display_options.enabled(display_options.T))
        html.open_div(class_="wato")

        html.begin_context_buttons()
        home_button()
        html.end_context_buttons()

        html.message(_("Successfully discarded all pending changes."))
        html.javascript("hide_changes_buttons();")
        html.footer()

        return False


    # TODO: Remove once new changes mechanism has been implemented
    def _extract_snapshot(self, snapshot_file):
        self._extract_from_file(watolib.snapshot_dir + snapshot_file, watolib.backup_domains)


    # TODO: Remove once new changes mechanism has been implemented
    def _extract_from_file(self, filename, elements):
        if type(elements) == list:
            multitar.extract(tarfile.open(filename, "r"), elements)

        elif type(elements) == dict:
            multitar.extract_domains(tarfile.open(filename, "r"), elements)


    # TODO: Remove once new changes mechanism has been implemented
    def _get_last_wato_snapshot_file(self):
        for snapshot_file in self._get_snapshots():
            status = watolib.get_snapshot_status(snapshot_file)
            if status['type'] == 'automatic' and not status['broken']:
                return snapshot_file


    # TODO: Remove once new changes mechanism has been implemented
    def _get_snapshots(self):
        snapshots = []
        try:
            for f in os.listdir(watolib.snapshot_dir):
                if os.path.isfile(watolib.snapshot_dir + f):
                    snapshots.append(f)
            snapshots.sort(reverse=True)
        except OSError:
            pass
        return snapshots


    def page(self):
        self._activation_msg()
        self._activation_form()

        html.h2(_("Activation status"))
        self._activation_status()

        html.h2(_("Pending changes"))
        self._change_table()


    def _activation_msg(self):
        html.open_div(id_="activation_msg", style="display:none")
        html.show_info("")
        html.close_div()


    def _activation_form(self):
        if not config.user.may("wato.activate"):
            html.show_warning(_("You are not permitted to activate configuration changes."))
            return

        if not self._changes:
            html.show_info(_("Currently there are no changes to activate."))
            return

        if not config.user.may("wato.activateforeign") \
           and self._has_foreign_changes_on_any_site():
            html.show_warning(_("Sorry, you are not allowed to activate changes of other users."))
            return

        valuespec = self._vs_activation()

        html.begin_form("activate", method="POST", action="")
        html.hidden_field("activate_until", self._get_last_change_id(), id_="activate_until")
        forms.header(valuespec.title())

        valuespec.render_input("activate", self._value)
        valuespec.set_focus("activate")
        html.help(valuespec.help())

        if self.has_foreign_changes():
            if config.user.may("wato.activateforeign"):
                html.show_warning(
                    _("There are some changes made by your colleagues that you will "
                      "activate if you proceed. You need to enable the checkbox above "
                      "to confirm the activation of these changes."))
            else:
                html.show_warning(
                    _("There are some changes made by your colleagues that you can not "
                      "activate because you are not permitted to. You can only activate "
                      "the changes on the sites that are not affected by these changes. "
                      "<br>"
                      "If you need to activate your changes on all sites, please contact "
                      "a permitted user to do it for you."))

        forms.end()
        html.jsbutton("activate_affected", _("Activate affected"),
                      "activate_changes(\"affected\")", cssclass="hot")
        html.jsbutton("activate_selected", _("Activate selected"),
                      "activate_changes(\"selected\")")

        html.hidden_fields()
        html.end_form()


    def _vs_activation(self):
        if self.has_foreign_changes() and config.user.may("wato.activateforeign"):
            foreign_changes_elements = [
                ("foreign", Checkbox(
                    title = _("Activate foreign changes"),
                    label = _("Activate changes of other users"),
                )),
            ]
        else:
            foreign_changes_elements = []

        return Dictionary(
            title = self.title(),
            elements = [
                ("comment", TextAreaUnicode(
                    title = _("Comment (optional)"),
                    cols = 40,
                    try_max_width = True,
                    rows = 3,
                    help = _("You can provide an optional comment for the current activation. "
                             "This can be useful to document the reason why the changes you "
                             "activate have been made."),
                )),
            ] + foreign_changes_elements,
            optional_keys = [],
            render = "form_part",
        )


    def _change_table(self):
        table.begin("changes", sortable=False, searchable=False, css="changes", limit=None)
        for _change_id, change in reversed(self._changes):
            css = []
            if self._is_foreign(change):
                css.append("foreign")
            if not config.user.may("wato.activateforeign"):
                css.append("not_permitted")

            table.row(css=" ".join(css))

            table.cell(_("Object"), css="narrow nobr")
            rendered = self._render_change_object(change["object"])
            if rendered:
                html.write(rendered)

            table.cell(_("Time"), render.date_and_time(change["time"]), css="narrow nobr")
            table.cell(_("User"), css="narrow nobr")
            html.write_text(change["user_id"] if change["user_id"] else "")
            if self._is_foreign(change):
                html.icon(_("This change has been made by another user"), "foreign_changes")

            table.cell(_("Affected sites"), css="narrow nobr")
            if self._affects_all_sites(change):
                html.write_text("<i>%s</i>" % _("All sites"))
            else:
                html.write_text(", ".join(sorted(change["affected_sites"])))

            table.cell(_("Change"), change["text"])
        table.end()


    def _render_change_object(self, obj):
        if not obj:
            return

        ty, ident = obj
        url, title = None, None

        if ty == "Host":
            host = watolib.Host.host(ident)
            if host:
                url = host.edit_url()
                title = host.name()

        elif ty == "Folder":
            if watolib.Folder.folder_exists(ident):
                folder = watolib.Folder.folder(ident)
                url = folder.url()
                title = folder.title()

        if url and title:
            return html.render_a(title, href=url)


    def _activation_status(self):
        table.begin("site-status", searchable=False, sortable=False, css="activation")

        for site_id, site in sort_sites(self._activation_sites()):
            table.row()

            site_status, status = self._get_site_status(site_id, site)

            is_online        = self._site_is_online(status)
            is_logged_in     = self._site_is_logged_in(site_id, site)
            has_foreign      = self._site_has_foreign_changes(site_id)
            can_activate_all = not has_foreign or config.user.may("wato.activateforeign")

            # Disable actions for offline sites and not logged in sites
            if not is_online or not is_logged_in:
                can_activate_all = False

            need_restart = self._is_activate_needed(site_id)
            need_sync    = self.is_sync_needed(site_id)
            need_action  = need_restart or need_sync

            # Activation checkbox
            table.cell("", css="buttons")
            if can_activate_all and need_action:
                html.checkbox("site_%s" % site_id, cssclass="site_checkbox")

            # Iconbuttons
            table.cell(_("Actions"), css="buttons")

            if config.user.may("wato.sites"):
                edit_url = watolib.folder_preserving_link([("mode", "edit_site"), ("edit", site_id)])
                html.icon_button(edit_url, _("Edit the properties of this site"), "edit")

            # State
            if can_activate_all and need_sync:
                html.icon_button(url="javascript:void(0)",
                    id_="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    title=_("This site is not update and needs a replication. Start it now."),
                    icon="need_replicate",
                    onclick="activate_changes(\"site\", \"%s\")" % site_id)

            if can_activate_all and need_restart:
                html.icon_button(url="javascript:void(0)",
                    id_="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    title=_("This site needs a restart for activating the changes. Start it now."),
                    icon="need_restart",
                    onclick="activate_changes(\"site\", \"%s\")" % site_id)

            if can_activate_all and not need_action:
                html.icon(_("This site is up-to-date."), "siteuptodate")

            site_url = site.get("multisiteurl")
            if site_url:
                html.icon_button(site_url, _("Open this site's local web user interface"), "url", target="_blank")

            table.text_cell(_("Site"), site.get("alias", site_id))

            # Livestatus
            table.cell(_("Status"), css="narrow nobr")
            html.status_label(content=status, status=status, title=_("This site is %s") % status)

            # Livestatus-/Check_MK-Version
            table.cell(_("Version"), site_status.get("livestatus_version", ""), css="narrow nobr")

            table.cell(_("Changes"), "%d" % len(self._changes_of_site(site_id)), css="number narrow nobr")

            table.cell(_("Progress"), css="repprogress")
            html.open_div(id_="site_%s_status" % site_id, class_=["msg"])
            html.close_div()
            html.open_div(id_="site_%s_progress" % site_id, class_=["progress"])
            html.close_div()

            # Hidden on initial rendering and shown on activation start
            table.cell(_("Details"), css="details")
            html.open_div(id_="site_%s_details" % site_id)

            # Shown on initial rendering and hidden on activation start
            table.cell(_("Last result"), css="last_result")
            last_state = self._last_activation_state(site_id)

            if not is_logged_in:
                html.write_text(_("Is not logged in.") + " ")

            if not last_state:
                html.write_text(_("Has never been activated"))
            else:
                html.write_text("%s: %s. " % (_("State"), last_state["_status_text"]))
                if last_state["_status_details"]:
                    html.write(last_state["_status_details"])

        table.end()



class ModeAjaxStartActivation(WatoWebApiMode):
    def page(self):
        init_wato_datastructures(with_wato_lock=True)

        config.user.need_permission("wato.activate")

        request = self.webapi_request()

        activate_until = request.get("activate_until")
        if not activate_until:
            raise MKUserError("activate_until", _("Missing parameter \"%s\".") % "activate_until")

        manager = watolib.ActivateChangesManager()
        manager.load()

        affected_sites = request.get("sites", "").strip()
        if not affected_sites:
            affected_sites = manager.dirty_and_active_activation_sites()
        else:
            affected_sites = affected_sites.split(",")

        comment = request.get("comment", "").strip()
        if comment == "":
            comment = None

        activate_foreign = request.get("activate_foreign", "0") == "1"

        activation_id = manager.start(affected_sites, activate_until, comment, activate_foreign)

        return {
            "activation_id": activation_id,
        }




class ModeAjaxActivationState(WatoWebApiMode):
    def page(self):
        init_wato_datastructures(with_wato_lock=True)

        config.user.need_permission("wato.activate")

        request = self.webapi_request()

        activation_id = request.get("activation_id")
        if not activation_id:
            raise MKUserError("activation_id", _("Missing parameter \"%s\".") % "activation_id")

        manager = watolib.ActivateChangesManager()
        manager.load()
        manager.load_activation(activation_id)

        return manager.get_state()



def do_activate_changes_automation():
    watolib.verify_slave_site_config(html.var("site_id"))

    try:
        domains = ast.literal_eval(html.var("domains"))
    except SyntaxError:
        raise watolib.MKAutomationException(_("Garbled automation response: '%s'") % html.var("domains"))

    return watolib.execute_activate_changes(domains)


watolib.register_automation_command("activate-changes", do_activate_changes_automation)

#.
#   .--Progress------------------------------------------------------------.
#   |               ____                                                   |
#   |              |  _ \ _ __ ___   __ _ _ __ ___  ___ ___                |
#   |              | |_) | '__/ _ \ / _` | '__/ _ \/ __/ __|               |
#   |              |  __/| | | (_) | (_| | | |  __/\__ \__ \               |
#   |              |_|   |_|  \___/ \__, |_|  \___||___/___/               |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Bulk inventory and other longer procedures are separated in single   |
#   | steps and run by an JavaScript scheduler showing a progress bar and  |
#   | buttons for aborting and pausing.                                    |
#   '----------------------------------------------------------------------'

# success_stats: Fields from the stats list to use for checking if something has been found
# fail_stats:    Fields from the stats list to used to count failed elements
def interactive_progress(items, title, stats, finishvars, timewait,
                         success_stats=None, termvars=None, fail_stats=None):
    if success_stats is None:
        success_stats = []

    if termvars is None:
        termvars = []

    if fail_stats is None:
        fail_stats = []

    if not termvars:
        termvars = finishvars

    html.open_center()
    html.open_table(class_="progress")

    html.open_tr()
    html.th(title, colspan=2)
    html.close_tr()

    html.open_tr()
    html.td(html.render_div('', id_="progress_log"), colspan=2, class_="log")
    html.close_tr()

    html.open_tr()
    html.open_td(colspan=2, class_="bar")
    html.open_table(id_="progress_bar")
    html.open_tbody()
    html.open_tr()
    html.td('', class_="left")
    html.td('', class_="right")
    html.close_tr()
    html.close_tbody()
    html.close_table()
    html.div('', id_="progress_title")
    html.img("images/perfometer-bg.png", class_="glass")
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td(class_="stats")
    html.open_table()
    for num, (label, value) in enumerate(stats):
        html.open_tr()
        html.th(label)
        html.td(value, id_="progress_stat%d" % num)
        html.close_tr()
    html.close_table()
    html.close_td()

    html.open_td(class_="buttons")
    html.jsbutton('progress_pause',    _('Pause'),   'javascript:progress_pause()')
    html.jsbutton('progress_proceed',  _('Proceed'), 'javascript:progress_proceed()',  'display:none')
    html.jsbutton('progress_finished', _('Finish'),  'javascript:progress_end()', 'display:none')
    html.jsbutton('progress_retry',    _('Retry Failed Hosts'), 'javascript:progress_retry()', 'display:none')
    html.jsbutton('progress_restart',  _('Restart'), 'javascript:location.reload()')
    html.jsbutton('progress_abort',    _('Abort'),   'javascript:progress_end()')
    html.close_td()
    html.close_tr()

    html.close_table()
    html.close_center()

    # Remove all sel_* variables. We do not need them for our ajax-calls.
    # They are just needed for the Abort/Finish links. Those must be converted
    # to POST.
    base_url = html.makeuri([], remove_prefix = "sel")
    finish_url = watolib.folder_preserving_link([("mode", "folder")] + finishvars)
    term_url = watolib.folder_preserving_link([("mode", "folder")] + termvars)

    html.javascript(('progress_scheduler("%s", "%s", 50, %s, "%s", %s, %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json.dumps(items), finish_url,
                      json.dumps(success_stats), json.dumps(fail_stats), term_url))


#.
#   .--Backups-------------------------------------------------------------.
#   |                ____             _                                    |
#   |               | __ )  __ _  ___| | ___   _ _ __  ___                 |
#   |               |  _ \ / _` |/ __| |/ / | | | '_ \/ __|                |
#   |               | |_) | (_| | (__|   <| |_| | |_) \__ \                |
#   |               |____/ \__,_|\___|_|\_\\__,_| .__/|___/                |
#   |                                           |_|                        |
#   +----------------------------------------------------------------------+
#   | Pages for managing backup and restore of WATO                        |
#   '----------------------------------------------------------------------'


class SiteBackupTargets(backup.Targets):
    def __init__(self):
        super(SiteBackupTargets, self).__init__(backup.site_config_path())



@mode_registry.register
class ModeBackup(backup.PageBackup, WatoMode):
    @classmethod
    def name(cls):
        return "backup"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def title(self):
        return _("Site backup")


    def jobs(self):
        return watolib.SiteBackupJobs()


    def keys(self):
        return SiteBackupKeypairStore()


    def home_button(self):
        home_button()



@mode_registry.register
class ModeBackupTargets(backup.PageBackupTargets, WatoMode):
    @classmethod
    def name(cls):
        return "backup_targets"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def title(self):
        return _("Site backup targets")


    def targets(self):
        return SiteBackupTargets()


    def jobs(self):
        return watolib.SiteBackupJobs()


    def page(self):
        self.targets().show_list()
        backup.SystemBackupTargetsReadOnly().show_list(editable=False, title=_("System global targets"))



@mode_registry.register
class ModeEditBackupTarget(backup.PageEditBackupTarget, WatoMode):
    @classmethod
    def name(cls):
        return "edit_backup_target"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def targets(self):
        return SiteBackupTargets()



@mode_registry.register
class ModeEditBackupJob(backup.PageEditBackupJob, WatoMode):
    @classmethod
    def name(cls):
        return "edit_backup_job"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def jobs(self):
        return watolib.SiteBackupJobs()


    def targets(self):
        return SiteBackupTargets()


    def backup_target_choices(self):
        choices = self.targets().choices()

        # Only add system wide defined targets that don't conflict with
        # the site specific backup targets
        choice_dict = dict(choices)
        for key, title in backup.SystemBackupTargetsReadOnly().choices():
            if key not in choice_dict:
                choices.append((key, _("%s (system wide)") % title))

        return sorted(choices, key=lambda (x, y): y.title())


    def _validate_target(self, value, varprefix):
        targets = self.targets()
        try:
            targets.get(value)
        except KeyError:
            backup.SystemBackupTargetsReadOnly().validate_target(value, varprefix)
            return

        targets.validate_target(value, varprefix)


    def keys(self):
        return SiteBackupKeypairStore()



@mode_registry.register
class ModeBackupJobState(backup.PageBackupJobState, WatoMode):
    @classmethod
    def name(cls):
        return "backup_job_state"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def jobs(self):
        return watolib.SiteBackupJobs()



class ModeAjaxBackupJobState(WatoWebApiMode):
    def page(self):
        config.user.need_permission("wato.backups")
        if html.var("job") == "restore":
            page = backup.PageBackupRestoreState()
        else:
            page = ModeBackupJobState()
        page.show_job_details()



class SiteBackupKeypairStore(backup.BackupKeypairStore):
    def __init__(self):
        super(SiteBackupKeypairStore, self).__init__(
            cmk.paths.default_config_dir + "/backup_keys.mk",
            "keys")



@mode_registry.register
class ModeBackupKeyManagement(SiteBackupKeypairStore, backup.PageBackupKeyManagement, WatoMode):
    @classmethod
    def name(cls):
        return "backup_keys"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def jobs(self):
        return watolib.SiteBackupJobs()



@mode_registry.register
class ModeBackupEditKey(SiteBackupKeypairStore, backup.PageBackupEditKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_edit_key"


    @classmethod
    def permissions(cls):
        return ["backups"]



@mode_registry.register
class ModeBackupUploadKey(SiteBackupKeypairStore, backup.PageBackupUploadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_upload_key"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def _upload_key(self, key_file, value):
        watolib.log_audit(None, "upload-backup-key",
                  _("Uploaded backup key '%s'") % value["alias"])
        super(ModeBackupUploadKey, self)._upload_key(key_file, value)



@mode_registry.register
class ModeBackupDownloadKey(SiteBackupKeypairStore, backup.PageBackupDownloadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_download_key"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def _file_name(self, key_id, key):
        return "Check_MK-%s-%s-backup_key-%s.pem" % (backup.hostname(), config.omd_site(), key_id)



@mode_registry.register
class ModeBackupRestore(backup.PageBackupRestore, WatoMode):
    @classmethod
    def name(cls):
        return "backup_restore"


    @classmethod
    def permissions(cls):
        return ["backups"]


    def title(self):
        if not self._target:
            return _("Site restore")
        return _("Restore from target: %s") % self._target.title()


    def targets(self):
        return SiteBackupTargets()


    def keys(self):
        return SiteBackupKeypairStore()


    def _get_target(self, target_ident):
        try:
            return self.targets().get(target_ident)
        except KeyError:
            return backup.SystemBackupTargetsReadOnly().get(target_ident)


    def _show_target_list(self):
        super(ModeBackupRestore, self)._show_target_list()
        backup.SystemBackupTargetsReadOnly().show_list(
                                editable=False, title=_("System global targets"))


    def _show_backup_list(self):
        self._target.show_backup_list("Check_MK")


#.
#   .--Configuration-------------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   | Main entry page for configuration of global variables, rules, groups,|
#   | timeperiods, users, etc.                                             |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeMain(WatoMode):
    @classmethod
    def name(cls):
        return "main"


    @classmethod
    def permissions(cls):
        return []


    def title(self):
        return _("WATO - Check_MK's Web Administration Tool")


    def buttons(self):
        changelog_button()


    def page(self):
        MainMenu(get_modules()).show()
#.
#   .--Global-Settings-----------------------------------------------------.
#   |          ____ _       _           _  __     __                       |
#   |         / ___| | ___ | |__   __ _| | \ \   / /_ _ _ __ ___           |
#   |        | |  _| |/ _ \| '_ \ / _` | |  \ \ / / _` | '__/ __|          |
#   |        | |_| | | (_) | |_) | (_| | |   \ V / (_| | |  \__ \          |
#   |         \____|_|\___/|_.__/ \__,_|_|    \_/ \__,_|_|  |___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Editor for global settings in main.mk                                |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeEditGlobals(GlobalSettingsMode):
    @classmethod
    def name(cls):
        return "globalvars"


    @classmethod
    def permissions(cls):
        return ["global"]


    def __init__(self):
        super(ModeEditGlobals, self).__init__()

        self._current_settings = watolib.load_configuration_settings()


    def title(self):
        if self._search:
            return _("Global Settings matching '%s'") % html.render_text(self._search)
        return _("Global Settings")


    def buttons(self):
        global_buttons()

        if config.user.may("wato.set_read_only"):
            html.context_button(_("Read only mode"), watolib.folder_preserving_link([("mode", "read_only")]), "read_only")

        if cmk.is_managed_edition():
            cmk.gui.cme.plugins.wato.managed.cme_global_settings_buttons()


    def action(self):
        varname = html.var("_varname")
        if not varname:
            return

        action = html.var("_action")

        domain, valuespec, need_restart, _allow_reset, _in_global_settings = watolib.configvars()[varname]
        def_value = self._default_values[varname]

        if action == "reset" and not is_a_checkbox(valuespec):
            c = wato_confirm(
                _("Resetting configuration variable"),
                _("Do you really want to reset the configuration variable <b>%s</b> "
                  "back to the default value of <b><tt>%s</tt></b>?") %
                   (varname, valuespec.value_to_text(def_value)))
        else:
            if not html.check_transaction():
                return
            c = True # no confirmation for direct toggle

        if c:
            if varname in self._current_settings:
                self._current_settings[varname] = not self._current_settings[varname]
            else:
                self._current_settings[varname] = not def_value
            msg = _("Changed Configuration variable %s to %s.") % (varname,
                     "on" if self._current_settings[varname] else "off")
            watolib.save_global_settings(self._current_settings)

            add_change("edit-configvar", msg, domains=[domain],
                need_restart=need_restart)

            if action == "_reset":
                return "globalvars", msg
            return "globalvars"
        elif c == False:
            return ""

    def page(self):
        self._show_configuration_variables(self._group_names())



@mode_registry.register
class ModeEditGlobalSetting(EditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_configvar"


    @classmethod
    def permissions(cls):
        return ["global"]


    def title(self):
        return _("Global configuration settings for Check_MK")


    def buttons(self):
        html.context_button(_("Abort"), watolib.folder_preserving_link([("mode", "globalvars")]), "abort")


    def _back_mode(self):
        return"globalvars"


    def _affected_sites(self):
        return None # All sites



@mode_registry.register
class ModeEditSiteGlobalSetting(EditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_site_configvar"


    @classmethod
    def permissions(cls):
        return ["global"]


    def _back_mode(self):
        return "edit_site_globals"


    def _from_vars(self):
        super(ModeEditSiteGlobalSetting, self)._from_vars()

        self._site_id = html.var("site")
        if self._site_id:
            self._configured_sites = watolib.SiteManagementFactory().factory().load_sites()
            try:
                site = self._configured_sites[self._site_id]
            except KeyError:
                raise MKUserError("site", _("Invalid site"))

        self._current_settings = site.setdefault("globals", {})
        self._global_settings  = watolib.load_configuration_settings()


    def title(self):
        return _("Site-specific global configuration for %s") % self._site_id


    def buttons(self):
        html.context_button(_("Abort"), watolib.folder_preserving_link([("mode", "edit_site_globals"),
                                                                ("site", self._site_id)]), "abort")


    def _affected_sites(self):
        return [self._site_id]


    def _save(self):
        watolib.SiteManagementFactory().factory().save_sites(self._configured_sites, activate=False)
        if self._site_id == config.omd_site():
            watolib.save_site_global_settings(self._current_settings)


    def _show_global_setting(self):
        forms.section(_("Global setting"))
        html.write_html(self._valuespec.value_to_text(self._global_settings[self._varname]))


#.
#   .--Multisite Connections-----------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing sites.                                             |
#   '----------------------------------------------------------------------'


@mode_registry.register
class ModeEditSiteGlobals(ModeSites, GlobalSettingsMode):
    @classmethod
    def name(cls):
        return "edit_site_globals"


    @classmethod
    def permissions(cls):
        return ["sites"]


    def __init__(self):
        super(ModeEditSiteGlobals, self).__init__()
        self._site_id = html.var("site")
        self._configured_sites = self._site_mgmt.load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

        # 2. Values of global settings
        self._global_settings = watolib.load_configuration_settings()

        # 3. Site specific global settings

        if watolib.is_wato_slave_site():
            self._current_settings = watolib.load_configuration_settings(site_specific=True)
        else:
            self._current_settings = self._site.get("globals", {})


    def title(self):
        return _("Edit site specific global settings of %s") % \
               html.render_tt(self._site_id)


    def buttons(self):
        super(ModeEditSiteGlobals, self).buttons()
        html.context_button(_("All Sites"),
                            watolib.folder_preserving_link([("mode", "sites")]),
                            "back")
        html.context_button(_("Connection"),
                            watolib.folder_preserving_link([("mode", "edit_site"),
                            ("edit", self._site_id)]), "sites")


    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self):
        varname = html.var("_varname")
        action  = html.var("_action")
        if not varname:
            return

        _domain, valuespec, need_restart, _allow_reset, _in_global_settings = watolib.configvars()[varname]
        def_value = self._global_settings.get(varname, self._default_values[varname])

        if action == "reset" and not is_a_checkbox(valuespec):
            c = wato_confirm(
                _("Removing site specific configuration variable"),
                _("Do you really want to remove the configuration variable <b>%s</b> "
                  "of the specific configuration of this site and that way use the global value "
                  "of <b><tt>%s</tt></b>?") %
                  (varname, valuespec.value_to_text(def_value)))

        else:
            if not html.check_transaction():
                return
            # No confirmation for direct toggle
            c = True

        if c:
            if varname in self._current_settings:
                self._current_settings[varname] = not self._current_settings[varname]
            else:
                self._current_settings[varname] = not def_value

            msg = _("Changed site specific configuration variable %s to %s.") % \
                  (varname, _("on") if self._current_settings[varname] else _("off"))

            self._site.setdefault("globals", {})[varname] = self._current_settings[varname]
            self._site_mgmt.save_sites(self._configured_sites, activate=False)

            add_change("edit-configvar", msg, sites=[self._site_id], need_restart=need_restart)

            if action == "_reset":
                return "edit_site_globals", msg
            return "edit_site_globals"

        elif c == False:
            return ""

        else:
            return None


    def _edit_mode(self):
        return "edit_site_configvar"


    def page(self):
        html.help(_("Here you can configure global settings, that should just be applied "
                    "on that site. <b>Note</b>: this only makes sense if the site "
                    "is part of a distributed setup."))

        if not watolib.is_wato_slave_site():
            if not config.has_wato_slave_sites():
               html.show_error(_("You can not configure site specific global settings "
                                 "in non distributed setups."))
               return

            if not self._site.get("replication") and not config.site_is_local(self._site_id):
                html.show_error(_("This site is not the master site nor a replication slave. "
                                  "You cannot configure specific settings for it."))
                return

        group_names = self._group_names(show_all=True)
        self._show_configuration_variables(group_names)




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
#   .--Builtin Agents------------------------------------------------------.
#   |    ____        _ _ _   _            _                    _           |
#   |   | __ ) _   _(_) | |_(_)_ __      / \   __ _  ___ _ __ | |_ ___     |
#   |   |  _ \| | | | | | __| | '_ \    / _ \ / _` |/ _ \ '_ \| __/ __|    |
#   |   | |_) | |_| | | | |_| | | | |  / ___ \ (_| |  __/ | | | |_\__ \    |
#   |   |____/ \__,_|_|_|\__|_|_| |_| /_/   \_\__, |\___|_| |_|\__|___/    |
#   |                                         |___/                        |
#   +----------------------------------------------------------------------+
#   | Simple download page for the builtin agents and plugins              |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeDownloadAgents(WatoMode):
    @classmethod
    def name(cls):
        return "download_agents"


    @classmethod
    def permissions(cls):
        return ["download_agents"]


    def title(self):
        return _("Agents and Plugins")


    def buttons(self):
        global_buttons()
        if watolib.has_agent_bakery():
            html.context_button(_("Baked agents"), watolib.folder_preserving_link([("mode", "agents")]), "download_agents")
        html.context_button(_("Release Notes"), "version.py", "mk")


    def page(self):
        html.open_div(class_="rulesets")
        packed = glob.glob(cmk.paths.agents_dir + "/*.deb") \
                + glob.glob(cmk.paths.agents_dir + "/*.rpm") \
                + glob.glob(cmk.paths.agents_dir + "/windows/c*.msi")

        self._download_table(_("Packaged Agents"), {}, packed)

        titles = {
            ''                         : _('Linux/Unix Agents'),
            '/plugins'                 : _('Linux/Unix Agents - Plugins'),
            '/cfg_examples'            : _('Linux/Unix Agents - Example Configurations'),
            '/cfg_examples/systemd'    : _('Linux Agent - Example configuration using with systemd'),
            '/windows'                 : _('Windows Agent'),
            '/windows/plugins'         : _('Windows Agent - Plugins'),
            '/windows/mrpe'            : _('Windows Agent - MRPE Scripts'),
            '/windows/cfg_examples'    : _('Windows Agent - Example Configurations'),
            '/windows/ohm'             : _('Windows Agent - OpenHardwareMonitor (headless)'),
            '/z_os'                    : _('z/OS'),
            '/sap'                     : _('SAP R/3'),
        }

        banned_paths = [
            '/bakery',
            '/special',
            '/windows/msibuild',
            '/windows/msibuild/patches',
            '/windows/sections',
        ]

        file_titles = {}
        other_sections = []
        for root, _dirs, files in os.walk(cmk.paths.agents_dir):
            file_paths = []
            relpath = root.split('agents')[1]
            if relpath not in banned_paths:
                title = titles.get(relpath, relpath)
                for filename in files:
                    if filename == "CONTENTS":
                        file_titles.update(self._read_agent_contents_file(root))

                    path = root + '/' + filename
                    if path not in packed and 'deprecated' not in path:
                        file_paths.append(path)

                other_sections.append((title, file_paths))

        other_sections.sort()

        for title, file_paths in other_sections:
            useful_file_paths = [
                p for p in file_paths
                if file_titles.get(p, "") != None \
                    and not p.endswith("/CONTENTS")
            ]
            file_titles.update(self._read_plugin_inline_comments(useful_file_paths))
            if useful_file_paths:
                self._download_table(title, file_titles, sorted(useful_file_paths))
        html.close_div()


    def _download_table(self, title, file_titles, paths):
        forms.header(title)
        forms.container()
        for path in paths:
            os_path  = path
            relpath  = path.replace(cmk.paths.agents_dir+'/', '')
            filename = path.split('/')[-1]
            title = file_titles.get(os_path, filename)

            file_size = os.stat(os_path).st_size

            # FIXME: Rename classes etc. to something generic
            html.open_div(class_="ruleset")
            html.open_div(style="width:300px;", class_="text")
            html.a(title, href="agents/%s" % relpath)
            html.span("." * 100, class_="dots")
            html.close_div()
            html.div(render.fmt_bytes(file_size), style="width:60px;", class_="rulecount")
            html.close_div()
            html.close_div()
        forms.end()


    def _read_plugin_inline_comments(self, file_paths):
        comment_prefixes = [ "# ", "REM ", "$!# " ]
        windows_bom = "\xef\xbb\xbf"
        file_titles = {}
        for path in file_paths:
            first_bytes = file(path).read(500)
            if first_bytes.startswith(windows_bom):
                first_bytes = first_bytes[len(windows_bom):]
            first_lines = first_bytes.splitlines()
            for line in first_lines:
                for prefix in comment_prefixes:
                    if line.startswith(prefix) and len(line) > len(prefix) and line[len(prefix)].isalpha():
                        file_titles[path] = line[len(prefix):].strip()
                        break
                if path in file_titles:
                    break
        return file_titles


    def _read_agent_contents_file(self, root):
        file_titles = {}
        for line in file(root + "/CONTENTS"):
            line = line.strip()
            if line and not line.startswith("#"):
                file_name, title = line.split(None, 1)
                if title == "(hide)":
                    file_titles[root + "/" + file_name] = None
                else:
                    file_titles[root + "/" + file_name] = title
        return file_titles
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
#   .--Read-Only-----------------------------------------------------------.
#   |           ____                _        ___        _                  |
#   |          |  _ \ ___  __ _  __| |      / _ \ _ __ | |_   _            |
#   |          | |_) / _ \/ _` |/ _` |_____| | | | '_ \| | | | |           |
#   |          |  _ <  __/ (_| | (_| |_____| |_| | | | | | |_| |           |
#   |          |_| \_\___|\__,_|\__,_|      \___/|_| |_|_|\__, |           |
#   |                                                     |___/            |
#   +----------------------------------------------------------------------+
#   | WATO can be set into read only mode manually.                        |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeManageReadOnly(WatoMode):
    @classmethod
    def name(cls):
        return "read_only"


    @classmethod
    def permissions(cls):
        return ["set_read_only"]


    def __init__(self):
        super(ModeManageReadOnly, self).__init__()
        self._settings = config.wato_read_only


    def title(self):
        return _("Manage configuration read only mode")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "globalvars")]), "back")


    def action(self):
        settings = self._vs().from_html_vars("_read_only")
        self._vs().validate_value(settings, "_read_only")
        self._settings = settings

        self._save()


    def _save(self):
        store.save_to_mk_file(multisite_dir + "read_only.mk",
                          "wato_read_only", self._settings, pprint_value = config.wato_pprint_config)


    def page(self):
        html.p(
            _("The WATO configuration can be set to read only mode for all users that are not "
              "permitted to ignore the read only mode. All users that are permitted to set the "
              "read only can disable it again when another permitted user enabled it before."))
        html.begin_form("read_only", method="POST")
        self._vs().render_input("_read_only", self._settings)
        html.button('_save', _('Save'), 'submit')
        html.hidden_fields()
        html.end_form()


    def _vs(self):
        return Dictionary(
            title = _("Read only mode"),
            optional_keys = False,
            render = "form",
            elements = [
                ("enabled",
                    Alternative(
                        title = _("Enabled"),
                        style = "dropdown",
                        elements = [
                            FixedValue(
                                False,
                                title = _("Disabled "),
                                totext = "Not enabled",
                            ),
                            FixedValue(
                                True,
                                title = _("Enabled permanently"),
                                totext = _("Enabled until disabling"),
                            ),
                            Tuple(
                                title = _("Enabled in time range"),
                                elements = [
                                    AbsoluteDate(
                                        title = _("Start"),
                                        include_time = True,
                                    ),
                                    AbsoluteDate(
                                        title = _("Until"),
                                        include_time = True,
                                        default_value = time.time() + 3600,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                ("rw_users", ListOf(
                    UserSelection(),
                    title = _("Can still edit"),
                    help = _("Users listed here are still allowed to modify things."),
                    movable = False,
                    add_label = _("Add user"),
                    default_value = [config.user.id],
                )),
                ("message", TextAreaUnicode(
                    title = _("Message"),
                    rows = 3,
                )),
            ]
        )


def show_read_only_warning():
    if watolib.is_read_only_mode_enabled():
        html.show_warning(watolib.read_only_message())


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
    "ajax_backup_job_state"     : lambda: ModeAjaxBackupJobState().page(),
}
for path, page_func in _wato_pages.items():
    cmk.gui.pages.register_page_handler(path, page_func)
