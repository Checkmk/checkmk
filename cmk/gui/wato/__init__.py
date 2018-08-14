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
import base64
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
import cmk.man_pages as man_pages
from cmk.regex import escape_regex_chars, regex
from cmk.defines import short_service_state_name
import cmk.render as render

import cmk.gui.utils as utils
import cmk.gui.sites as sites
import cmk.gui.config as config
import cmk.gui.table as table
import cmk.gui.multitar as multitar
import cmk.gui.userdb as userdb
import cmk.gui.weblib as weblib
import cmk.gui.login as login
import cmk.gui.mkeventd as mkeventd
import cmk.gui.forms as forms
import cmk.gui.backup as backup
import cmk.gui.watolib as watolib
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.plugin_registry
import cmk.gui.plugins.wato.utils
import cmk.gui.plugins.wato.utils.base_modes
import cmk.gui.plugins.wato.mkeventd
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

ALL_HOSTS         = watolib.ALL_HOSTS
ALL_SERVICES      = watolib.ALL_SERVICES
NEGATE            = watolib.NEGATE
NO_ITEM           = watolib.NO_ITEM
ENTRY_NEGATE_CHAR = watolib.ENTRY_NEGATE_CHAR

wato_root_dir = watolib.wato_root_dir
multisite_dir = watolib.multisite_dir

# TODO: Kept for old plugin compatibility. Remove this one day
syslog_facilities = mkeventd.syslog_facilities
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

# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock=False):
    watolib.init_watolib_datastructures()
    if os.path.exists(watolib.ConfigDomainCACertificates.trusted_cas_file) and\
        not need_to_create_sample_config():
        return

    if with_wato_lock:
        watolib.lock_exclusive()

    if not os.path.exists(watolib.ConfigDomainCACertificates.trusted_cas_file):
        watolib.ConfigDomainCACertificates().activate()

    create_sample_config()

    if with_wato_lock:
        watolib.unlock_exclusive()


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
        else:
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
            html.img("images/icon_autherr.png", class_=["icon", "autherr"],
                     title=html.strip_tags(subfolder.reason_why_may_not("read")))
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
            id = 'edit_' + subfolder.name(),
            cssclass = 'edit',
            style = 'display:none',
        )


    def _show_subfolder_delete_button(self, subfolder):
        html.icon_button(
            make_action_link([("mode", "folder"), ("_delete_folder", subfolder.name())]),
            _("Delete this folder"),
            "delete",
            id = 'delete_' + subfolder.name(),
            cssclass = 'delete',
            style = 'display:none',
        )


    def _show_subfolder_infos(self, subfolder):
        html.open_div(class_="infos")
        html.open_div(class_="infos_content")
        groups = userdb.load_group_information().get("contact", {})
        permitted_groups, folder_contact_groups, use_for_services = subfolder.groups()
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
            html.render_icon("move", help=_("Move this %s to another folder") % what_title,
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
                help=checkbox_title,
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
        for attr, topic in watolib.all_host_attributes():
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
            for attr, topic in watolib.all_host_attributes():
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
            permitted_groups, host_contact_groups, use_for_services = host.groups()
            table.cell(_("Permissions"), HTML(", ").join(map(render_contact_group, permitted_groups)))
            table.cell(_("Contact Groups"), HTML(", ").join(map(render_contact_group, host_contact_groups)))

            if not config.wato_hide_hosttags:
                # Raw tags
                #
                # Optimize wraps:
                # 1. add <nobr> round the single tags to prevent wrap within tags
                # 2. add "zero width space" (&#8203;)
                tag_title = "|".join([ '%s' % t for t in host.tags() ])
                table.cell(_("Tags"), help=tag_title, css="tag-ellipsis")
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
        else:
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
    else:
        return None # browser reload


# Create list of all hosts that are select with checkboxes in the current file.
# This is needed for bulk operations.
# TODO: Move to mode class
def get_hostnames_from_checkboxes(filterfunc = None):
    show_checkboxes = html.var("show_checkboxes") == "1"
    if show_checkboxes:
        selected = weblib.get_rowselection('wato-folder-/' + watolib.Folder.current().path())
    search_text = html.var("search")

    selected_host_names = []
    for host_name, host in sorted(watolib.Folder.current().hosts().items()):
        if (not search_text or (search_text.lower() in host_name.lower())) \
            and (not show_checkboxes or ('_c_' + host_name) in selected):
                if filterfunc == None or \
                   filterfunc(host):
                    selected_host_names.append(host_name)
    return selected_host_names


# TODO: Move to mode class
def get_hosts_from_checkboxes(filterfunc = None):
    folder = watolib.Folder.current()
    return [ folder.host(host_name) for host_name in get_hostnames_from_checkboxes(filterfunc) ]


# TODO: Split this into one base class and one subclass for folder and hosts
class ModeAjaxPopupMoveToFolder(WatoWebApiMode):
    """Renders the popup menu contents for either moving a host or a folder to another folder"""

    def _from_vars(self):
        self._what = html.var("what")
        if self._what not in [ "host", "folder" ]:
            raise NotImplementedError()

        self._ident = html.var("ident")

        self._back_url = html.var("back_url")
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
        else:
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
            attributes = {}
            parent = watolib.Folder.current()
            myself = None
        else:
            attributes = watolib.Folder.current().attributes()
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
            else:
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
        else:
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
        else:
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
        else:
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
        else:
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
            html.context_button(_("Last result"), html.makeuri([
                ("mode", "background_job_details"),
                ("job_id", host_renaming_job.get_job_id()),
                ("back_url", html.makeuri([])),
            ], filename="wato.py"), "background_job_details")


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
        for folder, host_name, target_name in renamings:
            message += u"<tr><td>%s</td><td> → %s</td></tr>" % (host_name, target_name)
        message += "</table>"

        c = wato_confirm(_("Confirm renaming of %d hosts") % len(renamings), HTML(message))
        if c:
            title = _("Renaming of %s") % ", ".join(u"%s → %s" % x[1:] for x in renamings)
            host_renaming_job = RenameHostsBackgroundJob(title=title)
            host_renaming_job.set_function(rename_hosts_background_job, renamings)
            host_renaming_job.start()

            job_id = host_renaming_job.get_job_id()
            job_details_url = html.makeuri_contextless([
                ("mode", "background_job_details"),
                ("job_id", job_id),
                ("back_url", html.makeuri([])),
            ], filename="wato.py")
            html.response.http_redirect(job_details_url)
        elif c == False: # not yet confirmed
            return ""
        else:
            return None # browser reload


    def _renaming_collision_error(self, renamings):
        name_collisions = set()
        new_names = [ new_name for (folder, old_name, new_name) in renamings ]
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
        else:
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
            else:
                return hostname
        elif operation[0] == 'regex':
            match_regex, new_name = operation[1]
            match = regex(match_regex).match(hostname)
            if match:
                for nr, group in enumerate(match.groups()):
                    new_name = new_name.replace("\\%d" % (nr+1), group)
                new_name = new_name.replace("\\0", hostname)
                return new_name
            else:
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

        host_renaming_job = RenameHostsBackgroundJob()
        if host_renaming_job.is_available():
            html.context_button(_("Last result"), html.makeuri([
                ("mode", "background_job_details"),
                ("job_id", host_renaming_job.get_job_id()),
                ("back_url", html.makeuri([])),
            ], filename="wato.py"), "background_job_details")


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
            host_renaming_job = RenameHostsBackgroundJob(title=_("Renaming of %s -> %s") % (self._host.name(), newname))
            renamings = [(watolib.Folder.current(), self._host.name(), newname)]
            host_renaming_job.set_function(rename_hosts_background_job, renamings)
            host_renaming_job.start()
            job_id = host_renaming_job.get_job_id()

            job_details_url = html.makeuri_contextless([
                ("mode", "background_job_details"),
                ("job_id", job_id),
                ("back_url", self._host.folder().url()),
            ], filename="wato.py")
            html.response.http_redirect(job_details_url)

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
            nodes = somehost.cluster_nodes()
            if somehost.rename_cluster_node(oldname, newname):
                clusters.append(somehost.name())
    if clusters:
        return [ "cluster_nodes" ] * len(clusters)
    else:
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
            for rule_folder, rulenr, rule in ruleset.get_rules():
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
    else:
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
    for userid, user in users.items():
        if user.get("notification_rules"):
            rules = user["notification_rules"]
            num_changed = rename_in_event_rules(rules)
            if num_changed:
                actions += [ "notify_user" ] * num_changed
                some_changed = True

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
    for userid, user in users.items():
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
    else:
        return []


def rename_host_in_bi(oldname, newname):
    return cmk.gui.plugins.wato.bi.BIHostRenamer().rename_host(oldname, newname)


def rename_hosts_in_check_mk(renamings):
    action_counts = {}
    for site_id, name_pairs in group_renamings_by_site(renamings).items():
        site = config.site(site_id)
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
            rule_folder, rule_index, rule = rules[rule_nr]

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
#   .--Host Diag-----------------------------------------------------------.
#   |              _   _           _     ____  _                           |
#   |             | | | | ___  ___| |_  |  _ \(_) __ _  __ _               |
#   |             | |_| |/ _ \/ __| __| | | | | |/ _` |/ _` |              |
#   |             |  _  | (_) \__ \ |_  | |_| | | (_| | (_| |              |
#   |             |_| |_|\___/|___/\__| |____/|_|\__,_|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   | Verify or find out a hosts agent related configuration.              |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeDiagHost(WatoMode):
    @classmethod
    def name(cls):
        return "diag_host"


    @classmethod
    def permissions(cls):
        return ["hosts", "diag_host"]


    @classmethod
    def diag_host_tests(cls):
        return [
            ('ping',          _('Ping')),
            ('agent',         _('Agent')),
            ('snmpv1',        _('SNMPv1')),
            ('snmpv2',        _('SNMPv2c')),
            ('snmpv2_nobulk', _('SNMPv2c (without Bulkwalk)')),
            ('snmpv3',        _('SNMPv3')),
            ('traceroute',    _('Traceroute')),
        ]


    def _from_vars(self):
        self._hostname = html.var("host")
        if not self._hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        self._host = watolib.Folder.current().host(self._hostname)
        self._host.need_permission("read")

        if self._host.is_cluster():
            raise MKGeneralException(_('This page does not support cluster hosts.'))


    def title(self):
        return _('Diagnostic of host') + " " + self._hostname


    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "back")
        host_status_button(self._hostname, "hoststatus")
        html.context_button(_("Properties"), self._host.edit_url(), "edit")
        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"), self._host.params_url(), "rulesets")
        html.context_button(_("Services"), self._host.services_url(), "services")


    def action(self):
        if not html.check_transaction():
            return

        if html.var('_save'):
            # Save the ipaddress and/or community
            vs_host = self._vs_host()
            new = vs_host.from_html_vars('vs_host')
            vs_host.validate_value(new, 'vs_host')

            # If both snmp types have credentials set - snmpv3 takes precedence
            return_message = []
            if "ipaddress" in new:
                return_message.append(_("IP address"))
            if "snmp_v3_credentials" in new:
                if "snmp_community" in new:
                    return_message.append(_("SNMPv3 credentials (SNMPv2 community was discarded)"))
                else:
                    return_message.append(_("SNMPv3 credentials"))
                new["snmp_community"] = new["snmp_v3_credentials"]
            elif "snmp_community" in new:
                return_message.append(_("SNMP credentials"))
            return_message = _("Updated attributes: ") + ", ".join(return_message)

            self._host.update_attributes(new)
            html.del_all_vars()
            html.set_var("host", self._hostname)
            html.set_var("folder", watolib.Folder.current().path())
            return "edit_host", return_message


    def page(self):
        html.open_div(class_="diag_host")
        html.open_table()
        html.open_tr()
        html.open_td()

        html.begin_form('diag_host', method = "POST")
        html.prevent_password_auto_completion()

        forms.header(_('Host Properties'))

        forms.section(legend = False)

        # The diagnose page shows both snmp variants at the same time
        # We need to analyse the preconfigured community and set either the
        # snmp_community or the snmp_v3_credentials
        vs_dict = {}
        for key, value in self._host.attributes().items():
            if key == "snmp_community" and type(value) == tuple:
                vs_dict["snmp_v3_credentials"] = value
                continue
            vs_dict[key] = value

        vs_host = self._vs_host()
        vs_host.render_input("vs_host", vs_dict)
        html.help(vs_host.help())

        forms.end()

        html.open_div(style="margin-bottom:10px")
        html.button("_save", _("Save & Exit"))
        html.close_div()

        forms.header(_('Options'))

        value = {}
        forms.section(legend = False)
        vs_rules = self._vs_rules()
        vs_rules.render_input("vs_rules", value)
        html.help(vs_rules.help())
        forms.end()

        html.button("_try",  _("Test"))

        html.hidden_fields()
        html.end_form()

        html.close_td()
        html.open_td(style="padding-left:10px;")

        if not html.var('_try'):
            html.message(_('You can diagnose the connection to a specific host using this dialog. '
                           'You can either test whether your current configuration is still working '
                           'or investigate in which ways a host can be reached. Simply configure the '
                           'connection options you like to try on the right side of the screen and '
                           'press the "Test" button. The results will be displayed here.'))
        else:
            # TODO: Insert any vs_host valuespec validation
            #       These tests can be called with invalid valuespec settings...
            for ident, title in ModeDiagHost.diag_host_tests():
                html.h3(title)
                html.open_table(class_=["data", "test"])
                html.open_tr(class_=["data", "odd0"])

                html.open_td(class_="icons")
                html.open_div()
                html.img("images/icon_reload.png", class_="icon", id="%s_img" % ident)
                html.open_a(href="javascript:start_host_diag_test(\'%s\', \'%s\');" % (ident, self._hostname))
                html.img("images/icon_reload.png", class_=["icon", "retry"], id_="%s_retry" % ident, title=_('Retry this test'))
                html.close_a()
                html.close_div()
                html.close_td()

                html.open_td()
                html.div('', class_="log", id_="%s_log" % ident)
                html.close_td()

                html.close_tr()
                html.close_table()
                html.javascript('start_host_diag_test("%s", "%s")' % (ident, self._hostname))

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_div()


    def _vs_host(self):
        return Dictionary(
            required_keys = ['hostname'],
            elements = [
                ('hostname', FixedValue(self._hostname,
                    title = _('Hostname'),
                    allow_empty = False
                )),
                ('ipaddress', HostAddress(
                    title = _("IPv4 Address"),
                    allow_empty = False,
                    allow_ipv6_address = False,
                )),
                ('snmp_community', Password(
                    title = _("SNMPv1/2 community"),
                    allow_empty = False
                )),
                ('snmp_v3_credentials',
                    cmk.gui.plugins.wato.SNMPCredentials(default_value = None, only_v3 = True)
                ),
            ]
        )



    def _vs_rules(self):
        if config.user.may('wato.add_or_modify_executables'):
            ds_option = [
                ('datasource_program', TextAscii(
                    title = _("Datasource Program (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'datasource_programs')]),
                    help = _("For agent based checks Check_MK allows you to specify an alternative "
                             "program that should be called by Check_MK instead of connecting the agent "
                             "via TCP. That program must output the agent's data on standard output in "
                             "the same format the agent would do. This is for example useful for monitoring "
                             "via SSH.") + monitoring_macro_help(),
                ))
            ]
        else:
            ds_option = []

        return Dictionary(
            optional_keys = False,
            elements = [
                ('agent_port', Integer(
                    minvalue = 1,
                    maxvalue = 65535,
                    default_value = 6556,
                    title = _("Check_MK Agent Port (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'agent_ports')]),
                    help = _("This variable allows to specify the TCP port to "
                             "be used to connect to the agent on a per-host-basis.")
                )),
                ('tcp_connect_timeout', Float(
                    minvalue = 1.0,
                    default_value = 5.0,
                    unit = _("sec"),
                    display_format = "%.0f",  # show values consistent to
                    size = 2,                 # SNMP-Timeout
                    title = _("TCP Connection Timeout (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'tcp_connect_timeouts')]),
                    help = _("This variable allows to specify a timeout for the "
                            "TCP connection to the Check_MK agent on a per-host-basis."
                            "If the agent does not respond within this time, it is considered to be unreachable.")
                )),
                ('snmp_timeout', Integer(
                    title = _("SNMP-Timeout (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                    help = _("After a request is sent to the remote SNMP agent we will wait up to this "
                             "number of seconds until assuming the answer get lost and retrying."),
                    default_value = 1,
                    minvalue = 1,
                    maxvalue = 60,
                    unit = _("sec"),
                )),
                ('snmp_retries', Integer(
                    title = _("SNMP-Retries (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                    default_value = 5,
                    minvalue = 0,
                    maxvalue = 50,
                )),
            ] + ds_option,
        )



class ModeAjaxDiagHost(WatoWebApiMode):
    def page(self):
        init_wato_datastructures(with_wato_lock=True)

        if not config.user.may('wato.diag_host'):
            raise MKAuthException(_('You are not permitted to perform this action.'))

        request = self.webapi_request()

        hostname = request.get("host")
        if not hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        host = watolib.Host.host(hostname)

        if not host:
            raise MKGeneralException(_('The given host does not exist.'))
        if host.is_cluster():
            raise MKGeneralException(_('This view does not support cluster hosts.'))

        host.need_permission("read")

        _test = request.get('_test')
        if not _test:
            raise MKGeneralException(_('The test is missing.'))

        # Execute a specific test
        if _test not in dict(ModeDiagHost.diag_host_tests()).keys():
            raise MKGeneralException(_('Invalid test.'))

        # TODO: Use ModeDiagHost._vs_rules() for processing/validation?
        args = [""] * 13
        for idx, what in enumerate ([ 'ipaddress',
                                      'snmp_community',
                                      'agent_port',
                                      'snmp_timeout',
                                      'snmp_retries',
                                      'tcp_connect_timeout',
                                      'datasource_program' ]):
            args[idx] = request.get(what, "")

        if request.get("snmpv3_use"):
            snmpv3_use = { "0": "noAuthNoPriv",
                           "1": "authNoPriv",
                           "2": "authPriv",
                         }.get(request.get("snmpv3_use"))
            args[7] = snmpv3_use
            if snmpv3_use != "noAuthNoPriv":
                snmpv3_auth_proto = { DropdownChoice.option_id("md5"): "md5",
                                      DropdownChoice.option_id("sha"): "sha" }.get(request.get("snmpv3_auth_proto"))
                args[8] = snmpv3_auth_proto
                args[9] = request.get("snmpv3_security_name")
                args[10] = request.get("snmpv3_security_password")
                if snmpv3_use == "authPriv":
                    snmpv3_privacy_proto = { DropdownChoice.option_id("DES"): "DES",
                                             DropdownChoice.option_id("AES"): "AES" }.get(request.get("snmpv3_privacy_proto"))
                    args[11] = snmpv3_privacy_proto
                    args[12] = request.get("snmpv3_privacy_password")
            else:
                args[9] = request.get("snmpv3_security_name")

        return watolib.check_mk_automation(host.site_id(), "diag-host", [hostname, _test] + args)


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

        counts, failed_hosts = watolib.check_mk_automation(self._host.site_id(), "inventory",
                                                   ["@scan", "refresh", hostname])
        count_added, count_removed, count_kept, count_new = counts[hostname]
        message = _("Refreshed check configuration of host '%s' with %d services") % \
                    (hostname, count_added)
        add_service_change(self._host, "refresh-autochecks", message)
        return message


    def _do_discovery(self, host):
        check_table = self._get_check_table()
        services_to_save, remove_disabled_rule, add_disabled_rule = {}, [], []
        apply_changes = False
        for table_source, check_type, checkgroup, item, paramstring, params, \
            descr, state, output, perfdata in check_table:

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
        else:
            return []


    def _get_rule_of_host(self, ruleset, value):
        for folder, index, rule in ruleset.get_rules():
            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None


    def _get_table_target(self, table_source, check_type, item):
        if self._fixall:
            if table_source == self.SERVICE_VANISHED:
                return self.SERVICE_REMOVED
            elif table_source == self.SERVICE_IGNORED:
                return self.SERVICE_IGNORED
            else: #table_source in [self.SERVICE_MONITORED, self.SERVICE_UNDECIDED]
                return self.SERVICE_MONITORED
        else:
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
            else:
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
                        help=_("Move %s to %s services") % (label, target))

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
                            help=_("Remove %s services") % label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)

        elif table_source == self.SERVICE_UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                bulk_button(table_source, self.SERVICE_MONITORED, _("Monitor"), label)
            if config.user.may("wato.service_discovery_to_ignored"):
                bulk_button(table_source, self.SERVICE_IGNORED, _("Disable"), label)


    def _check_row(self, check, show_bulk_actions):
        table_source, check_type, checkgroup, item, paramstring, params, \
            descr, state, output, perfdata = check

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
            ruleset_name = self._get_ruleset_name(table_source, check_type, checkgroup)
            if ruleset_name is None:
                return
            html.icon_button(watolib.folder_preserving_link(
                             [("mode", "edit_ruleset"), ("varname", ruleset_name),
                              ("host", self._host_name), ("item", watolib.mk_repr(item)), ]),
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

        table_source, check_type, checkgroup, item, paramstring, params, \
            descr, state, output, perfdata = check
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
        else:
            return None


    def _show_check_parameters(self, table_source, check_type, checkgroup, params):
        varname = self._get_ruleset_name(table_source, check_type, checkgroup)
        if varname and watolib.g_rulespecs.exists(varname):
            rulespec = watolib.g_rulespecs.get(varname)
            try:
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
        file_name, mime_type, content = upload_info["file"]

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
        else:
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
#   .--Bulk Discovery------------------------------------------------------.
#   |   ____        _ _      ____  _                                       |
#   |  | __ ) _   _| | | __ |  _ \(_)___  ___ _____   _____ _ __ _   _     |
#   |  |  _ \| | | | | |/ / | | | | / __|/ __/ _ \ \ / / _ \ '__| | | |    |
#   |  | |_) | |_| | |   <  | |_| | \__ \ (_| (_) \ V /  __/ |  | |_| |    |
#   |  |____/ \__,_|_|_|\_\ |____/|_|___/\___\___/ \_/ \___|_|   \__, |    |
#   |                                                            |___/     |
#   +----------------------------------------------------------------------+
#   | When the user wants to scan the services of multiple hosts at once   |
#   | this function is used. There is no fine-tuning possibility. We       |
#   | simply do something like -I or -II on the list of hosts.             |
#   '----------------------------------------------------------------------'



@mode_registry.register
class ModeBulkDiscovery(WatoMode):
    @classmethod
    def name(cls):
        return "bulkinventory"


    @classmethod
    def permissions(cls):
        return ["hosts", "services"]


    def _from_vars(self):
        self._start = bool(html.var("_start"))
        self._all =  bool(html.var("all"))
        self._item = html.var("_item") if html.var("_item") else None

        self._get_bulk_discovery_params()


    def _get_bulk_discovery_params(self):
        self._bulk_discovery_params = copy.deepcopy(config.bulk_discovery_default_settings)

        # start       : Rendering of the progress dialog
        # transaction : Single step processing
        if self._start or (html.is_transaction() and not html.has_var("_bulk_inventory")):
            bulk_discover_params = cmk.gui.plugins.wato.vs_bulk_discovery().from_html_vars("bulkinventory")
            cmk.gui.plugins.wato.vs_bulk_discovery().validate_value(bulk_discover_params, "bulkinventory")
            self._bulk_discovery_params.update(bulk_discover_params)

        self._recurse, self._only_failed, self._only_failed_invcheck, \
            self._only_ok_agent = self._bulk_discovery_params["selection"]
        self._use_cache, self._do_scan, self._bulk_size = \
            self._bulk_discovery_params["performance"]
        self._mode           = self._bulk_discovery_params["mode"]
        self._error_handling = self._bulk_discovery_params["error_handling"]


    def title(self):
        return _("Bulk Service Discovery")


    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")


    def action(self):
        config.user.need_permission("wato.services")
        if not self._item:
            return

        try:
            site_id, folderpath, hostnamesstring = self._item.split("|")
            hostnames         = hostnamesstring.split(";")
            num_hosts         = len(hostnames)
            num_skipped_hosts = 0
            num_failed_hosts  = 0
            folder            = watolib.Folder.folder(folderpath)

            if site_id not in config.sitenames():
                raise MKGeneralException(_("The requested site does not exist"))

            for host_name in hostnames:
                host = folder.host(host_name)
                if host is None:
                    raise MKGeneralException(_("The requested host does not exist"))
                host.need_permission("write")

            arguments         = [self._mode,] + hostnames

            if self._use_cache:
                arguments = [ "@cache" ] + arguments
            if self._do_scan:
                arguments = [ "@scan" ] + arguments
            if not self._error_handling:
                arguments = [ "@raiseerrors" ] + arguments

            timeout = html.request.request_timeout - 2

            watolib.unlock_exclusive() # Avoid freezing WATO when hosts do not respond timely
            counts, failed_hosts = watolib.check_mk_automation(site_id, "inventory",
                                                       arguments, timeout=timeout)
            watolib.lock_exclusive()
            watolib.Folder.invalidate_caches()
            folder = watolib.Folder.folder(folderpath)

            # sum up host individual counts to have a total count
            sum_counts = [ 0, 0, 0, 0 ] # added, removed, kept, new
            result_txt = ''
            for hostname in hostnames:
                sum_counts[0] += counts[hostname][0]
                sum_counts[1] += counts[hostname][1]
                sum_counts[2] += counts[hostname][2]
                sum_counts[3] += counts[hostname][3]
                host           = folder.host(hostname)

                if hostname in failed_hosts:
                    reason = failed_hosts[hostname]
                    if reason == None:
                        num_skipped_hosts += 1
                        result_txt += _("%s: discovery skipped: host not monitored<br>") % hostname
                    else:
                        num_failed_hosts += 1
                        result_txt += _("%s: discovery failed: %s<br>") % (hostname, failed_hosts[hostname])
                        if not host.locked():
                            host.set_discovery_failed()
                else:
                    result_txt += _("%s: discovery successful<br>\n") % hostname

                    add_service_change(host, "bulk-inventory",
                        _("Did service discovery on host %s: %d added, %d removed, %d kept, "
                          "%d total services") % tuple([hostname] + counts[hostname]))

                    if not host.locked():
                        host.clear_discovery_failed()

            result = json.dumps([ 'continue', num_hosts, num_failed_hosts, num_skipped_hosts ] + sum_counts) + "\n" + result_txt

        except Exception, e:
            result = json.dumps([ 'failed', num_hosts, num_hosts, 0, 0, 0, 0, ]) + "\n"
            if site_id:
                msg = _("Error during inventory of %s on site %s") % (", ".join(hostnames), site_id)
            else:
                msg = _("Error during inventory of %s") % (", ".join(hostnames))
            msg += html.render_div(e, class_="exc")
            if config.debug:
                msg += html.render_br() + html.render_pre(traceback.format_exc().replace("\n", "<br>")) + html.render_br()
            result += msg
        html.write(result)
        return ""


    def page(self):
        config.user.need_permission("wato.services")

        items, hosts_to_discover = self._fetch_items_for_interactive_progress()
        if html.var("_start"):
            # Start interactive progress
            interactive_progress(
                items,
                _("Bulk Service Discovery"),  # title
                [ (_("Total hosts"),      0),
                  (_("Failed hosts"),     0),
                  (_("Skipped hosts"),    0),
                  (_("Services added"),   0),
                  (_("Services removed"), 0),
                  (_("Services kept"),    0),
                  (_("Total services"),   0) ], # stats table
                [ ("mode", "folder") ], # URL for "Stop/Finish" button
                50, # ms to sleep between two steps
                fail_stats = [ 1 ],
            )

        else:
            html.begin_form("bulkinventory", method="POST")
            html.hidden_fields()

            vs = cmk.gui.plugins.wato.vs_bulk_discovery(render_form=True)

            msgs = []
            if not self._all:
                msgs.append(_("You have selected <b>%d</b> hosts for bulk discovery.") % len(hosts_to_discover))
                selection = self._bulk_discovery_params["selection"]
                self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

            msgs.append(_("Check_MK service discovery will automatically find and "
                          "configure services to be checked on your hosts."))
            html.open_p()
            html.write_text(" ".join(msgs))
            vs.render_input("bulkinventory", self._bulk_discovery_params)
            forms.end()

            html.button("_start", _("Start"))
            html.end_form()


    def _fetch_items_for_interactive_progress(self):
        if self._only_failed_invcheck:
            restrict_to_hosts = find_hosts_with_failed_inventory_check()
        else:
            restrict_to_hosts = None

        if self._only_ok_agent:
            skip_hosts = find_hosts_with_failed_agent()
        else:
            skip_hosts = []

        # 'all' not set -> only inventorize checked hosts
        hosts_to_discover = []

        if not self._all:
            if self._only_failed:
                filterfunc = lambda host: host.discovery_failed()
            else:
                filterfunc = None

            for host_name in get_hostnames_from_checkboxes(filterfunc):
                if restrict_to_hosts and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = watolib.Folder.current().host(host_name)
                host.need_permission("write")
                hosts_to_discover.append( (host.site_id(), host.folder(), host_name) )

        # all host in this folder, maybe recursively. New: we always group
        # a bunch of subsequent hosts of the same folder into one item.
        # That saves automation calls and speeds up mass inventories.
        else:
            entries                    = self._recurse_hosts(watolib.Folder.current())
            items                      = []
            hostnames                  = []
            current_folder             = None
            num_hosts_in_current_chunk = 0
            for host_name, folder in entries:
                if restrict_to_hosts != None and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = folder.host(host_name)
                host.need_permission("write")
                hosts_to_discover.append( (host.site_id(), host.folder(), host_name) )

        # Create a list of items for the progress bar, where we group
        # subsequent hosts that are in the same folder and site
        hosts_to_discover.sort()

        current_site_and_folder = None
        items                   = []
        hosts_in_this_item      = 0

        for site_id, folder, host_name in hosts_to_discover:
            if not items or (site_id, folder) != current_site_and_folder or \
               hosts_in_this_item >= self._bulk_size:
                items.append("%s|%s|%s" % (site_id, folder.path(), host_name))
                hosts_in_this_item = 1
            else:
                items[-1]          += ";" + host_name
                hosts_in_this_item += 1
            current_site_and_folder = site_id, folder
        return items, hosts_to_discover


    def _recurse_hosts(self, folder):
        entries = []
        for host_name, host in folder.hosts().items():
            if not self._only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if self._recurse:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts(subfolder)
        return entries




def find_hosts_with_failed_inventory_check():
    return sites.live().query_column(
        "GET services\n"
        "Filter: description = Check_MK inventory\n" # FIXME: Remove this one day
        "Filter: description = Check_MK Discovery\n"
        "Or: 2\n"
        "Filter: state > 0\n"
        "Columns: host_name")

def find_hosts_with_failed_agent():
    return sites.live().query_column(
        "GET services\n"
        "Filter: description = Check_MK\n"
        "Filter: state >= 2\n"
        "Columns: host_name")

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
        for attr, topic in watolib.all_host_attributes():
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
        for attr, topic in watolib.all_host_attributes():
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
                    inherited_value = container.attribute(attrname)
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
#   .--Random Hosts--------------------------------------------------------.
#   |  ____                 _                   _   _           _          |
#   | |  _ \ __ _ _ __   __| | ___  _ __ ___   | | | | ___  ___| |_ ___    |
#   | | |_) / _` | '_ \ / _` |/ _ \| '_ ` _ \  | |_| |/ _ \/ __| __/ __|   |
#   | |  _ < (_| | | | | (_| | (_) | | | | | | |  _  | (_) \__ \ |_\__ \   |
#   | |_| \_\__,_|_| |_|\__,_|\___/|_| |_| |_| |_| |_|\___/|___/\__|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This module allows the creation of large numbers of random hosts,    |
#   | for test and development.                                            |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeRandomHosts(WatoMode):
    @classmethod
    def name(cls):
        return "random_hosts"


    @classmethod
    def permissions(cls):
        return ["hosts", "random_hosts"]


    def title(self):
        return _("Random Hosts")


    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")


    def action(self):
        if not html.check_transaction():
            return "folder"

        count = int(html.var("count"))
        folders = int(html.var("folders"))
        levels = int(html.var("levels"))
        created = self._create_random_hosts(watolib.Folder.current(), count, folders, levels)
        return "folder", _("Created %d random hosts.") % created


    def page(self):
        html.begin_form("random")
        forms.header(_("Create Random Hosts"))
        forms.section(_("Number to create"))
        html.write_text("%s: " % _("Hosts to create in each folder"))
        html.number_input("count", 10)
        html.set_focus("count")
        html.br()
        html.write_text("%s: " % _("Number of folders to create in each level"))
        html.number_input("folders", 10)
        html.br()
        html.write_text("%s: " % _("Levels of folders to create"))
        html.number_input("levels", 1)

        forms.end()
        html.button("start", _("Start!"), "submit")
        html.hidden_fields()
        html.end_form()


    def _create_random_hosts(self, folder, count, folders, levels):
        if levels == 0:
            hosts_to_create = []
            while len(hosts_to_create) < count:
                host_name = "random_%010d" % int(random.random() * 10000000000)
                hosts_to_create.append((host_name, {"ipaddress" : "127.0.0.1"}, None))
            folder.create_hosts(hosts_to_create)
            return count

        else:
            total_created = 0
            created = 0
            while created < folders:
                created += 1
                i = 1
                while True:
                    folder_name = "folder_%02d" % i
                    if not folder.has_subfolder(folder_name):
                        break
                    i += 1

                subfolder = folder.create_subfolder(folder_name, "Subfolder %02d" % i, {})
                total_created += self._create_random_hosts(subfolder, count, folders, levels - 1)
            return total_created

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
        if config.user.may("wato.activate") and self.has_changes() and self._get_last_wato_snapshot_file():
            html.context_button(_("Discard Changes!"),
                html.makeactionuri([("_action", "discard")]),
                "discard", id="discard_changes_button")

        if config.user.may("wato.sites"):
            html.context_button(_("Site Configuration"), watolib.folder_preserving_link([("mode", "sites")]), "sites")

        if config.user.may("wato.auditlog"):
            html.context_button(_("Audit Log"), watolib.folder_preserving_link([("mode", "auditlog")]), "auditlog")


    def action(self):
        if html.var("_action") != "discard":
            return

        if not html.check_transaction():
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
        import tarfile
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
           and self._has_foreign_changes_on_all_sites():
            html.show_warning(_("Sorry, you are not allowed to activate changes of other users."))
            return

        valuespec = self._vs_activation()

        html.begin_form("activate", method="POST", action="")
        html.hidden_field("activate_until", self._get_last_change_id(), id="activate_until")
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
        for change_id, change in reversed(self._changes):
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
                    id="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    help=_("This site is not update and needs a replication. Start it now."),
                    icon="need_replicate",
                    onclick="activate_changes(\"site\", \"%s\")" % site_id)

            if can_activate_all and need_restart:
                html.icon_button(url="javascript:void(0)",
                    id="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    help=_("This site needs a restart for activating the changes. Start it now."),
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
            html.status_label(content=status, status=status, help=_("This site is %s") % status)

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
        else:
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
#   .--Value-Editor--------------------------------------------------------.
#   |       __     __    _              _____    _ _ _                     |
#   |       \ \   / /_ _| |_   _  ___  | ____|__| (_) |_ ___  _ __         |
#   |        \ \ / / _` | | | | |/ _ \ |  _| / _` | | __/ _ \| '__|        |
#   |         \ V / (_| | | |_| |  __/ | |__| (_| | | || (_) | |           |
#   |          \_/ \__,_|_|\__,_|\___| |_____\__,_|_|\__\___/|_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The value editor is used in the configuration and rules module for   |
#   | editing single values (e.g. configuration parameter for main.mk or   |
#   | check parameters).                                                   |
#   '----------------------------------------------------------------------'


def edit_value(valuespec, value, title=""):
    if title:
        title = title + "<br>"
    help_text = valuespec.help() or ""

    html.open_tr()
    html.open_td(class_="legend")
    html.write_text(title)
    html.help(help_text)
    html.close_td()
    html.open_td(class_="content")
    valuespec.render_input("ve", value)
    html.close_td()
    html.close_tr()


def get_edited_value(valuespec):
    value = valuespec.from_html_vars("ve")
    valuespec.validate_value(value, "ve")
    return value


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
#   .--LDAP Config---------------------------------------------------------.
#   |       _     ____    _    ____     ____             __ _              |
#   |      | |   |  _ \  / \  |  _ \   / ___|___  _ __  / _(_) __ _        |
#   |      | |   | | | |/ _ \ | |_) | | |   / _ \| '_ \| |_| |/ _` |       |
#   |      | |___| |_| / ___ \|  __/  | |__| (_) | | | |  _| | (_| |       |
#   |      |_____|____/_/   \_\_|      \____\___/|_| |_|_| |_|\__, |       |
#   |                                                         |___/        |
#   +----------------------------------------------------------------------+
#   | LDAP configuration and diagnose page                                 |
#   '----------------------------------------------------------------------'

class LDAPMode(WatoMode):
    def _add_change(self, action_name, text):
        add_change(action_name, text, domains=[watolib.ConfigDomainGUI],
            sites=config.get_login_sites())



@mode_registry.register
class ModeLDAPConfig(LDAPMode):
    @classmethod
    def name(cls):
        return "ldap_config"


    @classmethod
    def permissions(cls):
        return ["global"]


    def title(self):
        return _("LDAP connections")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "users")]), "back")
        html.context_button(_("New connection"), watolib.folder_preserving_link([("mode", "edit_ldap_connection")]), "new")


    def action(self):
        connections = userdb.load_connection_config(lock=True)
        if html.has_var("_delete"):
            index = int(html.var("_delete"))
            connection = connections[index]
            c = wato_confirm(_("Confirm deletion of LDAP connection"),
                             _("Do you really want to delete the LDAP connection <b>%s</b>?") %
                               (connection["id"]))
            if c:
                self._add_change("delete-ldap-connection",
                    _("Deleted LDAP connection %s") % (connection["id"]))
                del connections[index]
                userdb.save_connection_config(connections)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if not html.check_transaction():
                return

            from_pos = html.get_integer_input("_move")
            to_pos = html.get_integer_input("_index")
            connection = connections[from_pos]
            self._add_change("move-ldap-connection",
                _("Changed position of LDAP connection %s to %d") % (connection["id"], to_pos))
            del connections[from_pos] # make to_pos now match!
            connections[to_pos:to_pos] = [connection]
            userdb.save_connection_config(connections)


    def page(self):
        cmk.gui.plugins.userdb.ldap_connector.ldap_test_module()

        table.begin()
        for index, connection in enumerate(userdb.load_connection_config()):
            table.row()

            table.cell(_("Actions"), css="buttons")
            edit_url   = watolib.folder_preserving_link([("mode", "edit_ldap_connection"), ("id", connection["id"])])
            delete_url = make_action_link([("mode", "ldap_config"), ("_delete", index)])
            drag_url   = make_action_link([("mode", "ldap_config"), ("_move", index)])
            clone_url  = watolib.folder_preserving_link([("mode", "edit_ldap_connection"), ("clone", connection["id"])])

            html.icon_button(edit_url, _("Edit this LDAP connection"), "edit")
            html.icon_button(clone_url, _("Create a copy of this LDAP connection"), "clone")
            html.element_dragger_url("tr", base_url=drag_url)
            html.icon_button(delete_url, _("Delete this LDAP connection"), "delete")

            table.cell("", css="narrow")
            if connection.get("disabled"):
                html.icon(_("This connection is currently not being used for synchronization."), "disabled")
            else:
                html.empty_icon_button()

            table.cell(_("ID"), connection["id"])

            if cmk.is_managed_edition():
                table.cell(_("Customer"), managed.get_customer_name(connection))

            table.cell(_("Description"))
            url = connection.get("docu_url")
            if url:
                html.icon_button(url, _("Context information about this connection"), "url", target="_blank")
                html.write("&nbsp;")
            html.write_text(connection["description"])

        table.end()



@mode_registry.register
class ModeEditLDAPConnection(LDAPMode):
    @classmethod
    def name(cls):
        return "edit_ldap_connection"


    @classmethod
    def permissions(cls):
        return ["global"]


    def _from_vars(self):
        self._connection_id = html.var("id")
        self._connection_cfg = {}
        self._connections = userdb.load_connection_config(lock=html.is_transaction())

        if self._connection_id == None:
            clone_id = html.var("clone")
            if clone_id is not None:
                self._connection_cfg = self._get_connection_cfg_and_index(clone_id)[0]

            self._new = True
            return

        self._new = False
        self._connection_cfg, self._connection_nr = self._get_connection_cfg_and_index(self._connection_id)


    def _get_connection_cfg_and_index(self, connection_id):
        for index, cfg in enumerate(self._connections):
            if cfg['id'] == connection_id:
                return cfg, index

        if not self._connection_cfg:
            raise MKUserError(None, _("The requested connection does not exist."))


    def title(self):
        if self._new:
            return _("Create new LDAP Connection")
        else:
            return _("Edit LDAP Connection: %s") % html.render_text(self._connection_id)


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "ldap_config")]), "back")


    def action(self):
        if not html.check_transaction():
            return

        vs = self._valuespec()
        self._connection_cfg = vs.from_html_vars("connection")
        vs.validate_value(self._connection_cfg, "connection")

        if self._new:
            self._connections.insert(0, self._connection_cfg)
            self._connection_id = self._connection_cfg["id"]
        else:
            self._connection_cfg["id"] = self._connection_id
            self._connections[self._connection_nr] = self._connection_cfg

        if self._new:
            log_what = "new-ldap-connection"
            log_text = _("Created new LDAP connection")
        else:
            log_what = "edit-ldap-connection"
            log_text = _("Changed LDAP connection %s") % self._connection_id
        self._add_change(log_what, log_text)

        userdb.save_connection_config(self._connections)
        config.user_connections = self._connections # make directly available on current page
        if html.var("_save"):
            return "ldap_config"
        else:
            # Fix the case where a user hit "Save & Test" during creation
            html.set_var('id', self._connection_id)


    def page(self):
        html.open_div(id_="ldap")
        html.open_table()
        html.open_tr()

        html.open_td()
        html.begin_form("connection", method="POST")
        html.prevent_password_auto_completion()
        vs = self._valuespec()
        vs.render_input("connection", self._connection_cfg)
        vs.set_focus("connection")
        html.button("_save", _("Save"))
        html.button("_test", _("Save & Test"))
        html.hidden_fields()
        html.end_form()
        html.close_td()

        html.open_td(style="padding-left:10px;vertical-align:top")
        html.h2(_('Diagnostics'))
        if not html.var('_test') or not self._connection_id:
            html.message(HTML('<p>%s</p><p>%s</p>' %
                        (_('You can verify the single parts of your ldap configuration using this '
                           'dialog. Simply make your configuration in the form on the left side and '
                           'hit the "Save & Test" button to execute the tests. After '
                           'the page reload, you should see the results of the test here.'),
                         _('If you need help during configuration or experience problems, please refer '
                           'to the Multisite <a target="_blank" '
                           'href="https://mathias-kettner.com/checkmk_multisite_ldap_integration.html">'
                           'LDAP Documentation</a>.'))))
        else:
            connection = userdb.get_connection(self._connection_id)
            for address in connection.servers():
                html.h3("%s: %s" % (_('Server'), address))
                table.begin('test', searchable = False)

                for title, test_func in self._tests():
                    table.row()
                    try:
                        state, msg = test_func(connection, address)
                    except Exception, e:
                        state = False
                        msg = _('Exception: %s') % html.render_text(e)
                        logger.exception()

                    if state:
                        img = html.render_icon("success", _('Success'))
                    else:
                        img = html.render_icon("failed", _("Failed"))

                    table.cell(_("Test"),   title)
                    table.cell(_("State"),   img)
                    table.cell(_("Details"), msg)

                table.end()

            connection.disconnect()

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_div()


    def _tests(self):
        return [
            (_('Connection'),          self._test_connect),
            (_('User Base-DN'),        self._test_user_base_dn),
            (_('Count Users'),         self._test_user_count),
            (_('Group Base-DN'),       self._test_group_base_dn),
            (_('Count Groups'),        self._test_group_count),
            (_('Sync-Plugin: Roles'),  self._test_groups_to_roles),
        ]


    def _test_connect(self, connection, address):
        conn, msg = connection.connect_server(address)
        if conn:
            return (True, _('Connection established. The connection settings seem to be ok.'))
        else:
            return (False, msg)


    def _test_user_base_dn(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _('The User Base DN is not configured.'))
        connection.connect(enforce_new = True, enforce_server = address)
        if connection.user_base_dn_exists():
            return (True, _('The User Base DN could be found.'))
        elif connection.has_bind_credentials_configured():
            return (False, _('The User Base DN could not be found. Maybe the provided '
                             'user (provided via bind credentials) has no permission to '
                             'access the Base DN or the credentials are wrong.'))
        else:
            return (False, _('The User Base DN could not be found. Seems you need '
                             'to configure proper bind credentials.'))


    def _test_user_count(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _('The User Base DN is not configured.'))
        connection.connect(enforce_new = True, enforce_server = address)
        try:
            ldap_users = connection.get_users()
            msg = _('Found no user object for synchronization. Please check your filter settings.')
        except Exception, e:
            ldap_users = None
            msg = "%s" % e
            if 'successful bind must be completed' in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _('Please configure proper bind credentials.'))
                else:
                    return (False, _('Maybe the provided user (provided via bind credentials) has not '
                                     'enough permissions or the credentials are wrong.'))

        if ldap_users and len(ldap_users) > 0:
            return (True, _('Found %d users for synchronization.') % len(ldap_users))
        else:
            return (False, msg)


    def _test_group_base_dn(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _('The Group Base DN is not configured, not fetching any groups.'))
        connection.connect(enforce_new = True, enforce_server = address)
        if connection.group_base_dn_exists():
            return (True, _('The Group Base DN could be found.'))
        else:
            return (False, _('The Group Base DN could not be found.'))


    def _test_group_count(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _('The Group Base DN is not configured, not fetching any groups.'))
        connection.connect(enforce_new = True, enforce_server = address)
        try:
            ldap_groups = connection.get_groups()
            msg = _('Found no group object for synchronization. Please check your filter settings.')
        except Exception, e:
            ldap_groups = None
            msg = "%s" % e
            if 'successful bind must be completed' in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _('Please configure proper bind credentials.'))
                else:
                    return (False, _('Maybe the provided user (provided via bind credentials) has not '
                                     'enough permissions or the credentials are wrong.'))
        if ldap_groups and len(ldap_groups) > 0:
            return (True, _('Found %d groups for synchronization.') % len(ldap_groups))
        else:
            return (False, msg)


    def _test_groups_to_roles(self, connection, address):
        active_plugins = connection.active_plugins()
        if 'groups_to_roles' not in active_plugins:
            return True, _('Skipping this test (Plugin is not enabled)')

        connection.connect(enforce_new = True, enforce_server = address)
        num = 0
        for role_id, group_distinguished_names in active_plugins['groups_to_roles'].items():
            if type(group_distinguished_names) != list:
                group_distinguished_names = [group_distinguished_names]

            for dn in group_distinguished_names:
                if type(dn) in [ str, unicode ]:
                    num += 1
                    try:
                        ldap_groups = connection.get_groups(dn)
                        if not ldap_groups:
                            return False, _('Could not find the group specified for role %s') % role_id
                    except Exception, e:
                        return False, _('Error while fetching group for role %s: %s') % (role_id, e)
        return True, _('Found all %d groups.') % num


    def _valuespec(self):
        general_elements = []

        if self._new:
            id_element = ("id", TextAscii(
                title = _("ID"),
                help = _("The ID of the connection must be a unique text. It will be used as an internal key "
                         "when objects refer to the connection."),
                allow_empty = False,
                size = 12,
                validate = self._validate_ldap_connection_id,
            ))
        else:
            id_element = ("id", FixedValue(self._connection_id,
                title = _("ID"),
            ))

        general_elements += [ id_element ]

        if cmk.is_managed_edition():
            general_elements += managed.customer_choice_element()

        general_elements += rule_option_elements()

        def vs_directory_options(ty):
            connect_to_choices = [
                ("fixed_list", _("Manually specify list of LDAP servers"), Dictionary(
                    elements = [
                        ("server", TextAscii(
                            title = _("LDAP Server"),
                            help = _("Set the host address of the LDAP server. Might be an IP address or "
                                     "resolvable hostname."),
                            allow_empty = False,
                        )),
                        ("failover_servers", ListOfStrings(
                            title = _('Failover Servers'),
                            help = _('When the connection to the first server fails with connect specific errors '
                                     'like timeouts or some other network related problems, the connect mechanism '
                                     'will try to use this server instead of the server configured above. If you '
                                     'use persistent connections (default), the connection is being used until the '
                                     'LDAP is not reachable or the local webserver is restarted.'),
                            allow_empty = False,
                        )),
                    ],
                    optional_keys = ["failover_servers"],
                )),
            ]

            if ty == "ad":
                connect_to_choices.append(
                    ("discover", _("Automatically discover LDAP server"), Dictionary(
                        elements = [
                            ("domain", TextAscii(
                                title = _("DNS domain name to discover LDAP servers of"),
                                help = _("Configure the DNS domain name of your Active directory domain here, Check_MK "
                                         "will then query this domain for it's closest domain controller to communicate "
                                         "with."),
                                allow_empty = False,
                            )),
                        ],
                        optional_keys = [],
                    )),
                )

            return Dictionary(
                elements = [
                    ("connect_to", CascadingDropdown(
                        title = _("Connect to"),
                        choices = connect_to_choices,
                    )),
                ],
                optional_keys = [],
            )


        connection_elements = [
            ("directory_type", CascadingDropdown(
                title = _("Directory Type"),
                help  = _("Select the software the LDAP directory is based on. Depending on "
                          "the selection e.g. the attribute names used in LDAP queries will "
                          "be altered."),
                choices = [
                    ("ad",                 _("Active Directory"),     vs_directory_options("ad")),
                    ("openldap",           _("OpenLDAP"),             vs_directory_options("openldap")),
                    ("389directoryserver", _("389 Directory Server"), vs_directory_options("389directoryserver")),
                ],
            )),
            ("bind", Tuple(
                title = _("Bind Credentials"),
                help  = _("Set the credentials to be used to connect to the LDAP server. The "
                          "used account must not be allowed to do any changes in the directory "
                          "the whole connection is read only. "
                          "In some environment an anonymous connect/bind is allowed, in this "
                          "case you don't have to configure anything here."
                          "It must be possible to list all needed user and group objects from the "
                          "directory."),
                elements = [
                    LDAPDistinguishedName(
                        title = _("Bind DN"),
                        help  = _("Specify the distinguished name to be used to bind to "
                                  "the LDAP directory, e. g. <tt>CN=ldap,OU=users,DC=example,DC=com</tt>"),
                        size = 63,
                    ),
                    Password(
                        title = _("Bind Password"),
                        help  = _("Specify the password to be used to bind to "
                                  "the LDAP directory."),
                    ),
                ],
            )),
            ("port", Integer(
                title = _("TCP Port"),
                help  = _("This variable allows to specify the TCP port to "
                          "be used to connect to the LDAP server. "),
                minvalue = 1,
                maxvalue = 65535,
                default_value = 389,
            )),
            ("use_ssl", FixedValue(
                title  = _("Use SSL"),
                help   = _("Connect to the LDAP server with a SSL encrypted connection. The "
                           "<a href=\"wato.py?mode=edit_configvar&site=&varname=trusted_certificate_authorities\">trusted "
                           "certificates authorities</a> configured in Check_MK will be used to validate the "
                           "certificate provided by the LDAP server."),
                value  = True,
                totext = _("Encrypt the network connection using SSL."),
            )),
            ("connect_timeout", Float(
                title = _("Connect Timeout"),
                help = _("Timeout for the initial connection to the LDAP server in seconds."),
                unit = _("Seconds"),
                minvalue = 1.0,
                default_value = 2.0,
            )),
            ("version", DropdownChoice(
                title = _("LDAP Version"),
                help  = _("Select the LDAP version the LDAP server is serving. Most modern "
                          "servers use LDAP version 3."),
                choices = [ (2, "2"), (3, "3") ],
                default_value = 3,
            )),
            ("page_size", Integer(
                title = _("Page Size"),
                help = _("LDAP searches can be performed in paginated mode, for example to improve "
                         "the performance. This enables pagination and configures the size of the pages."),
                minvalue = 1,
                default_value = 1000,
            )),
            ("response_timeout", Integer(
                title = _("Response Timeout"),
                unit = _("Seconds"),
                help = _("Timeout for LDAP query responses."),
                minvalue = 0,
                default_value = 5,
            )),
            ("suffix", TextUnicode(
                allow_empty = False,
                title = _("LDAP connection suffix"),
                help = _("The LDAP connection suffix can be used to distinguish equal named objects "
                         "(name conflicts), for example user accounts, from different LDAP connections.<br>"
                         "It is used in the following situations:<br><br>"
                         "During LDAP synchronization, the LDAP sync might discover that a user to be "
                         "synchronized from from the current LDAP is already being synchronized from "
                         "another LDAP connection. Without the suffix configured this results in a name "
                         "conflict and the later user not being synchronized. If the connection has a "
                         "suffix configured, this suffix is added to the later username in case of the name "
                         "conflict to resolve it. The user will then be named <tt>[username]@[suffix]</tt> "
                         "instead of just <tt>[username]</tt>.<br><br>"
                         "In the case a user which users name is existing in multiple LDAP directories, "
                         "but associated to different persons, your user can insert <tt>[username]@[suffix]</tt>"
                         " during login instead of just the plain <tt>[username]</tt> to tell which LDAP "
                         "directory he is assigned to. Users without name conflict just need to provide their "
                         "regular username as usual."),
                regex = re.compile(r'^[A-Z0-9.-]+(?:\.[A-Z]{2,24})?$', re.I),
            )),
        ]

        user_elements = [
            ("user_dn", LDAPDistinguishedName(
                title = _("User Base DN"),
                help  = _("Give a base distinguished name here, e. g. <tt>OU=users,DC=example,DC=com</tt><br> "
                          "All user accounts to synchronize must be located below this one."),
                size = 80,
            )),
            ("user_scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in LDAP searches. In most cases <i>Search whole subtree below "
                          "the base DN</i> is the best choice. "
                          "It searches for matching objects recursively."),
                choices = [
                    ("sub",  _("Search whole subtree below the base DN")),
                    ("base", _("Search only the entry at the base DN")),
                    ("one",  _("Search all entries one level below the base DN")),
                ],
                default_value = "sub",
            )),
            ("user_filter", TextAscii(
                title = _("Search Filter"),
                help = _("Using this option you can define an optional LDAP filter which is used during "
                         "LDAP searches. It can be used to only handle a subset of the users below the given "
                         "base DN.<br><br>Some common examples:<br><br> "
                         "All user objects in LDAP:<br> "
                         "<tt>(&(objectclass=user)(objectcategory=person))</tt><br> "
                         "Members of a group:<br> "
                         "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br> "
                         "Members of a nested group:<br> "
                         "<tt>(&(objectclass=user)(objectcategory=person)(memberof:1.2.840.113556.1.4.1941:=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"),
                size = 80,
                default_value = lambda: cmk.gui.plugins.userdb.ldap_connector.ldap_filter_of_connection(self._connection_id, 'users', False),
                attrencode = True,
            )),
            ("user_filter_group", LDAPDistinguishedName(
                title = _("Filter Group (Only use in special situations)"),
                help = _("Using this option you can define the DN of a group object which is used to filter the users. "
                         "Only members of this group will then be synchronized. This is a filter which can be "
                         "used to extend capabilities of the regular \"Search Filter\". Using the search filter "
                         "you can only define filters which directly apply to the user objects. To filter by "
                         "group memberships, you can use the <tt>memberOf</tt> attribute of the user objects in some "
                         "directories. But some directories do not have such attributes because the memberships "
                         "are stored in the group objects as e.g. <tt>member</tt> attributes. You should use the "
                         "regular search filter whenever possible and only use this filter when it is really "
                         "neccessary. Finally you can say, you should not use this option when using Active Directory. "
                         "This option is neccessary in OpenLDAP directories when you like to filter by group membership.<br><br>"
                         "If using, give a plain distinguished name of a group here, e. g. "
                         "<tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt>"),
                size = 80,
            )),
            ("user_id", TextAscii(
                title = _("User-ID Attribute"),
                help  = _("The attribute used to identify the individual users. It must have "
                          "unique values to make an user identifyable by the value of this "
                          "attribute."),
                default_value = lambda: cmk.gui.plugins.userdb.ldap_connector.ldap_attr_of_connection(self._connection_id, 'user_id'),
                attrencode = True,
            )),
            ("lower_user_ids", FixedValue(
                title  = _("Lower Case User-IDs"),
                help   = _("Convert imported User-IDs to lower case during synchronization."),
                value  = True,
                totext = _("Enforce lower case User-IDs."),
            )),
            ("user_id_umlauts", Transform(
                DropdownChoice(
                    title = _("Translate Umlauts in User-IDs (deprecated)"),
                    help  = _("Check_MK was not not supporting special characters (like Umlauts) in "
                              "User-IDs. To deal with LDAP users having umlauts in their User-IDs "
                              "you had the choice to replace umlauts with other characters. This option "
                              "is still available for compatibility reasons, but you are adviced to use "
                              "the \"keep\" option for new installations."),
                    choices = [
                        ("keep",     _("Keep special characters")),
                        ("replace",  _("Replace umlauts like \"&uuml;\" with \"ue\"")),
                    ],
                    default_value = "keep",
                ),
                forth = lambda x: "keep" if (x == "skip") else x
            )),
            ("create_only_on_login", FixedValue(
                title  = _("Create users only on login"),
                value  = True,
                totext = _("Instead of creating the user accounts during the regular sync, create "
                           "the user on the first login."),
            )),
        ]

        group_elements = [
            ("group_dn", LDAPDistinguishedName(
                title = _("Group Base DN"),
                help  = _("Give a base distinguished name here, e. g. <tt>OU=groups,DC=example,DC=com</tt><br> "
                          "All groups used must be located below this one."),
                size = 80,
            )),
            ("group_scope", DropdownChoice(
                title = _("Search Scope"),
                help  = _("Scope to be used in group related LDAP searches. In most cases "
                          "<i>Search whole subtree below the base DN</i> "
                          "is the best choice. It searches for matching objects in the given base "
                          "recursively."),
                choices = [
                    ("sub",  _("Search whole subtree below the base DN")),
                    ("base", _("Search only the entry at the base DN")),
                    ("one",  _("Search all entries one level below the base DN")),
                ],
                default_value = "sub",
            )),
            ("group_filter", TextAscii(
                title = _("Search Filter"),
                help = _("Using this option you can define an optional LDAP filter which is used "
                         "during group related LDAP searches. It can be used to only handle a "
                         "subset of the groups below the given base DN.<br><br>"
                         "e.g. <tt>(objectclass=group)</tt>"),
                size = 80,
                default_value = lambda: cmk.gui.plugins.userdb.ldap_connector.ldap_filter_of_connection(self._connection_id, 'groups', False),
                attrencode = True,
            )),
            ("group_member", TextAscii(
                title = _("Member Attribute"),
                help  = _("The attribute used to identify users group memberships."),
                default_value = lambda: cmk.gui.plugins.userdb.ldap_connector.ldap_attr_of_connection(self._connection_id, 'member'),
                attrencode = True,
            )),
        ]

        other_elements = [
            ("active_plugins", Dictionary(
                title = _('Attribute Sync Plugins'),
                help  = _('It is possible to fetch several attributes of users, like Email or full names, '
                          'from the LDAP directory. This is done by plugins which can individually enabled '
                          'or disabled. When enabling a plugin, it is used upon the next synchonisation of '
                          'user accounts for gathering their attributes. The user options which get imported '
                          'into Check_MK from LDAP will be locked in WATO.'),
                elements = lambda: cmk.gui.plugins.userdb.ldap_connector.ldap_attribute_plugins_elements(self._connection_id),
                default_keys = ['email', 'alias', 'auth_expire' ],
            )),
            ("cache_livetime", Age(
                title = _('Sync Interval'),
                help  = _('This option defines the interval of the LDAP synchronization. This setting is only '
                          'used by sites which have the '
                          '<a href="wato.py?mode=sites">Automatic User '
                          'Synchronization</a> enabled.<br><br>'
                          'Please note: Passwords of the users are never stored in WATO and therefor never cached!'),
                minvalue = 60,
                default_value = 300,
                display = ["days", "hours", "minutes" ],
            )),
        ]

        return Transform(Dictionary(
                title = _('LDAP Connection'),
                elements = general_elements
                    + connection_elements
                    + user_elements
                    + group_elements
                    + other_elements
                ,
                headers = [
                    (_("General Properties"), [ key for key, vs in general_elements ]),
                    (_("LDAP Connection"),    [ key for key, vs in connection_elements ]),
                    (_("Users"),              [ key for key, vs in user_elements ]),
                    (_("Groups"),             [ key for key, vs in group_elements ]),
                    (_("Attribute Sync Plugins"), [ "active_plugins" ]),
                    (_("Other"),              [ "cache_livetime" ]),
                ],
                render = "form",
                form_narrow = True,
                optional_keys = [
                    'port', 'use_ssl', 'bind', 'page_size', 'response_timeout', 'failover_servers',
                    'user_filter', 'user_filter_group', 'user_id', 'lower_user_ids', 'connect_timeout', 'version',
                    'group_filter', 'group_member', 'suffix', 'create_only_on_login',
                ],
                validate = self._validate_ldap_connection,
            ),
            forth = cmk.gui.plugins.userdb.ldap_connector.LDAPUserConnector.transform_config,
        )


    def _validate_ldap_connection_id(self, value, varprefix):
        if value in [ c['id'] for c in config.user_connections ]:
            raise MKUserError(varprefix, _("This ID is already user by another connection. Please choose another one."))


    def _validate_ldap_connection(self, value, varprefix):
        for role_id, group_specs in value["active_plugins"].get("groups_to_roles", {}).items():
            if role_id == "nested":
                continue # This is the option to enabled/disable nested group handling, not a role to DN entry

            for index, group_spec in enumerate(group_specs):
                dn, connection_id = group_spec

                if connection_id == None:
                    group_dn = value["group_dn"]

                else:
                    connection = userdb.get_connection(connection_id)
                    if not connection:
                        continue
                    group_dn = connection.get_group_dn()

                if not group_dn:
                    raise MKUserError(varprefix, _("You need to configure the group base DN to be able to "
                                                   "use the roles synchronization plugin."))

                if not dn.lower().endswith(group_dn.lower()):
                    varname = "connection_p_active_plugins_p_groups_to_roles_p_%s_1_%d" % (role_id, index)
                    raise MKUserError(varname, _("The configured DN does not match the group base DN."))


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
        else:
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

        domain, valuespec, need_restart, allow_reset, in_global_settings = watolib.configvars()[varname]
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
            else:
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
#   .--Notifications-------------------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Modes for managing notification configuration                         |
#   '----------------------------------------------------------------------'


class NotificationsMode(EventsMode):
    # TODO: Clean this up. Use inheritance
    @classmethod
    def _rule_match_conditions(cls):
        return cls._generic_rule_match_conditions() \
            + cls._event_rule_match_conditions(flavour="notify") \
            + cls._notification_rule_match_conditions()


    @classmethod
    def _notification_rule_match_conditions(cls):
        def transform_ec_rule_id_match(val):
            if isinstance(val, list):
                return val
            else:
                return [val]

        return [
           ( "match_escalation",
             Tuple(
                 title = _("Restrict to n<sup>th</sup> to m<sup>th</sup> notification"),
                 orientation = "float",
                 elements = [
                     Integer(
                         label = _("from"),
                         help = _("Let through notifications counting from this number. "
                                  "For normal alerts The first notification has the number 1. "
                                  "For custom notifications the number is 0."),
                         default_value = 0,
                         minvalue = 0,
                         maxvalue = 999999,
                     ),
                     Integer(
                         label = _("to"),
                         help = _("Let through notifications counting upto this number"),
                         default_value = 999999,
                         minvalue = 1,
                         maxvalue = 999999,
                     ),
               ],
             ),
           ),
           ( "match_escalation_throttle",
             Tuple(
                 title = _("Throttle periodic notifications"),
                 help = _("This match option allows you to throttle periodic notifications after "
                          "a certain number of notifications have been created by the monitoring "
                          "core. If you for example select 10 as the beginning and 5 as the rate "
                          "then you will receive the notification 1 through 10 and then 15, 20, "
                          "25... and so on. Note that recovery notifications are not affected by throttling."),
                 orientation = "float",
                 elements = [
                    Integer(
                        label = _("beginning from notification number"),
                        default_value = 10,
                        minvalue = 1,
                    ),
                    Integer(
                        label = _("send only every"),
                        default_value = 5,
                        unit = _("th notification"),
                        minvalue = 1,
                   )
                 ],
             )
           ),
            ( "match_notification_comment",
              RegExpUnicode(
                 title = _("Match notification comment"),
                 help = _("This match only makes sense for custom notifications. When a user creates "
                          "a custom notification then he/she can enter a comment. This comment is shipped "
                          "in the notification context variable <tt>NOTIFICATIONCOMMENT</tt>. Here you can "
                          "make a condition of that comment. It is a regular expression matching the beginning "
                          "of the comment."),
                 size = 60,
                 mode = RegExpUnicode.prefix,
            )),
            ( "match_ec",
              Alternative(
                  title = _("Event Console alerts"),
                  help = _("The Event Console can have events create notifications in Check_MK. "
                           "These notifications will be processed by the rule based notification "
                           "system of Check_MK. This matching option helps you distinguishing "
                           "and also gives you access to special event fields."),
                  style = "dropdown",
                  elements = [
                       FixedValue(False, title = _("Do not match Event Console alerts"), totext=""),
                       Dictionary(
                           title = _("Match only Event Console alerts"),
                           elements = [
                               ( "match_rule_id",
                                Transform(
                                    ListOf(
                                        ID(title = _("Match event rule"), label = _("Rule ID:"), size=12, allow_empty=False),
                                        add_label = _("Add Rule ID"),
                                        title = _("Rule IDs")
                                    ),
                                    forth = transform_ec_rule_id_match,
                                )
                               ),
                               ( "match_priority",
                                 Tuple(
                                     title = _("Match syslog priority"),
                                     help = _("Define a range of syslog priorities this rule matches"),
                                     orientation = "horizontal",
                                     show_titles = False,
                                     elements = [
                                        DropdownChoice(label = _("from:"), choices = mkeventd.syslog_priorities, default_value = 4),
                                        DropdownChoice(label = _(" to:"),   choices = mkeventd.syslog_priorities, default_value = 0),
                                     ],
                                 ),
                               ),
                               ( "match_facility",
                                 DropdownChoice(
                                     title = _("Match syslog facility"),
                                     help = _("Make the rule match only if the event has a certain syslog facility. "
                                              "Messages not having a facility are classified as <tt>user</tt>."),
                                     choices = mkeventd.syslog_facilities,
                                 )
                               ),
                               ( "match_comment",
                                 RegExpUnicode(
                                     title = _("Match event comment"),
                                     help = _("This is a regular expression for matching the event's comment."),
                                     mode = RegExpUnicode.prefix,
                                 )
                               ),
                           ]
                       )
                  ]
              )
            )
        ]


    def _render_notification_rules(self, rules, userid="", show_title=False, show_buttons=True,
                                    analyse=False, start_nr=0, profilemode=False):
        if not rules:
            html.message(_("You have not created any rules yet."))
            return

        vs_match_conditions = Dictionary(
            elements = self._rule_match_conditions()
        )

        if rules:
            if not show_title:
                title = ""
            elif profilemode:
                title = _("Notification rules")
            elif userid:
                url = html.makeuri([("mode", "user_notifications"), ("user", userid)])
                code = html.render_icon_button(url, _("Edit this user's notifications"), "edit")
                title = code + _("Notification rules of user %s") % userid
            else:
                title = _("Global notification rules")
            table.begin(title=title, limit=None, sortable=False)

            if analyse:
                analyse_rules, analyse_plugins = analyse

            # have_match = False
            for nr, rule in enumerate(rules):
                table.row()

                # Analyse
                if analyse:
                    table.cell(css="buttons")
                    what, anarule, reason = analyse_rules[nr + start_nr]
                    if what == "match":
                        html.icon(_("This rule matches"), "rulematch")
                    elif what == "miss":
                        html.icon(_("This rule does not match: %s") % reason, "rulenmatch")

                if profilemode:
                    listmode = "user_notifications_p"
                elif userid:
                    listmode = "user_notifications"
                else:
                    listmode = "notifications"

                actions_allowed =  config.user.may("notification_plugin.%s" % rule['notify_plugin'][0])

                if show_buttons and actions_allowed:
                    anavar = html.var("analyse", "")
                    delete_url = make_action_link([("mode", listmode), ("user", userid), ("_delete", nr)])
                    drag_url   = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr)])
                    suffix     = "_p" if profilemode else ""
                    edit_url   = watolib.folder_preserving_link([("mode", "notification_rule" + suffix), ("edit", nr), ("user", userid)])
                    clone_url  = watolib.folder_preserving_link([("mode", "notification_rule" + suffix), ("clone", nr), ("user", userid)])

                    table.cell(_("Actions"), css="buttons")
                    html.icon_button(edit_url, _("Edit this notification rule"), "edit")
                    html.icon_button(clone_url, _("Create a copy of this notification rule"), "clone")
                    html.element_dragger_url("tr", base_url=drag_url)
                    html.icon_button(delete_url, _("Delete this notification rule"), "delete")
                else:
                    table.cell("", css="buttons")
                    for x in range(4):
                        html.empty_icon_button()

                table.cell("", css="narrow")
                if rule.get("disabled"):
                    html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
                else:
                    html.empty_icon_button()

                notify_method = rule["notify_plugin"]
                # Catch rules with empty notify_plugin key
                # Maybe this should be avoided somewhere else (e.g. rule editor)
                if not notify_method:
                    notify_method = ( None, [] )
                notify_plugin = notify_method[0]

                table.cell(_("Type"), css="narrow")
                if notify_method[1] == None:
                    html.icon(_("Cancel notifications for this plugin type"), "notify_cancel")
                else:
                    html.icon(_("Create a notification"), "notify_create")

                table.cell(_("Plugin"), notify_plugin or _("Plain Email"), css="narrow nowrap")

                table.cell(_("Bulk"), css="narrow")
                if "bulk" in rule or "bulk_period" in rule:
                    html.icon(_("This rule configures bulk notifications."), "bulk")

                table.cell(_("Description"))
                url = rule.get("docu_url")
                if url:
                    html.icon_button(url, _("Context information about this rule"), "url", target="_blank")
                    html.write("&nbsp;")
                html.write_text(rule["description"])
                table.cell(_("Contacts"))
                infos = []
                if rule.get("contact_object"):
                    infos.append(_("all contacts of the notified object"))
                if rule.get("contact_all"):
                    infos.append(_("all users"))
                if rule.get("contact_all_with_email"):
                    infos.append(_("all users with and email address"))
                if rule.get("contact_users"):
                    infos.append(_("users: ") + (", ".join(rule["contact_users"])))
                if rule.get("contact_groups"):
                    infos.append(_("contact groups: ") + (", ".join(rule["contact_groups"])))
                if rule.get("contact_emails"):
                    infos.append(_("email addresses: ") + (", ".join(rule["contact_emails"])))
                if not infos:
                    html.i(_("(no one)"))

                else:
                    for line in infos:
                        html.write("&bullet; %s" % line)
                        html.br()

                table.cell(_("Conditions"), css="rule_conditions")
                num_conditions = len([key for key in rule if key.startswith("match_")])
                if num_conditions:
                    title = _("%d conditions") % num_conditions
                    html.begin_foldable_container(treename="rule_%d" % nr,
                        id="%s" % nr,
                        isopen=False,
                        title=title,
                        indent=False,
                        tree_img="tree_black",
                    )
                    html.write(vs_match_conditions.value_to_text(rule))
                    html.end_foldable_container()
                else:
                    html.i(_("(no conditions)"))

            table.end()


    def _add_change(self, log_what, log_text):
        add_change(log_what, log_text, need_restart=False)


    def _vs_notification_bulkby(self):
        return ListChoice(
          title = _("Create separate notification bulks based on"),
          choices = [
            ( "folder",     _("Folder") ),
            ( "host",       _("Host") ),
            ( "service",    _("Service description") ),
            ( "sl",         _("Service level") ),
            ( "check_type", _("Check type") ),
            ( "state",      _("Host/Service state") ),
            ( "ec_contact", _("Event Console contact") ),
            ( "ec_comment", _("Event Console comment") ),
          ],
          default_value = [ "host" ],
        )



@mode_registry.register
class ModeNotifications(NotificationsMode):
    @classmethod
    def name(cls):
        return "notifications"


    @classmethod
    def permissions(cls):
        return ["notifications"]


    def __init__(self):
        super(ModeNotifications, self).__init__()
        options = config.user.load_file("notification_display_options", {})
        self._show_user_rules = options.get("show_user_rules", False)
        self._show_backlog    = options.get("show_backlog", False)
        self._show_bulks      = options.get("show_bulks", False)


    def title(self):
        return _("Notification configuration")


    def buttons(self):
        global_buttons()
        html.context_button(_("New Rule"), watolib.folder_preserving_link([("mode", "notification_rule")]), "new")
        if self._show_user_rules:
            html.context_button(_("Hide user rules"), html.makeactionuri([("_show_user", "")]), "users")
        else:
            html.context_button(_("Show user rules"), html.makeactionuri([("_show_user", "1")]), "users")

        if self._show_backlog:
            html.context_button(_("Hide Analysis"), html.makeactionuri([("_show_backlog", "")]), "analyze")
        else:
            html.context_button(_("Analyse"), html.makeactionuri([("_show_backlog", "1")]), "analyze")

        if self._show_bulks:
            html.context_button(_("Hide Bulks"), html.makeactionuri([("_show_bulks", "")]), "bulk")
        else:
            html.context_button(_("Show Bulks"), html.makeactionuri([("_show_bulks", "1")]), "bulk")


    def action(self):
        if html.has_var("_show_user"):
            if html.check_transaction():
                self._show_user_rules = bool(html.var("_show_user"))
                self._save_notification_display_options()

        elif html.has_var("_show_backlog"):
            if html.check_transaction():
                self._show_backlog = bool(html.var("_show_backlog"))
                self._save_notification_display_options()

        elif html.has_var("_show_bulks"):
            if html.check_transaction():
                self._show_bulks = bool(html.var("_show_bulks"))
                self._save_notification_display_options()

        elif html.has_var("_replay"):
            if html.check_transaction():
                nr = int(html.var("_replay"))
                result = watolib.check_mk_local_automation("notification-replay", [str(nr)], None)
                return None, _("Replayed notifiation number %d") % (nr + 1)

        else:
            return self._generic_rule_list_actions(self._get_notification_rules(), "notification", _("notification rule"),  watolib.save_notification_rules)


    def _get_notification_rules(self):
        return watolib.load_notification_rules()


    def _save_notification_display_options(self):
        config.user.save_file("notification_display_options", {
            "show_user_rules" : self._show_user_rules,
            "show_backlog"    : self._show_backlog,
            "show_bulks"      : self._show_bulks,
        })


    def page(self):
        self._show_not_enabled_warning()
        self._show_no_fallback_contact_warning()
        self._show_bulk_notifications()
        self._show_notification_backlog()
        self._show_rules()


    def _show_not_enabled_warning(self):
        # Check setting of global notifications. Are they enabled? If not, display
        # a warning here. Note: this is a main.mk setting, so we cannot access this
        # directly.
        current_settings = watolib.load_configuration_settings()
        if not current_settings.get("enable_rulebased_notifications"):
            url = 'wato.py?mode=edit_configvar&varname=enable_rulebased_notifications'
            html.show_warning(
               _("<b>Warning</b><br><br>Rule based notifications are disabled in your global settings. "
                 "The rules that you edit here will have affect only on notifications that are "
                 "created by the Event Console. Normal monitoring alerts will <b>not</b> use the "
                 "rule based notifications now."
                 "<br><br>"
                 "You can change this setting <a href=\"%s\">here</a>.") % url)


    def _show_no_fallback_contact_warning(self):
        if not self._fallback_mail_contacts_configured():
            url = 'wato.py?mode=edit_configvar&varname=notification_fallback_email'
            html.show_warning(
              _("<b>Warning</b><br><br>You haven't configured a "
                "<a href=\"%s\">fallback email address</a> nor enabled receiving fallback emails for "
                "any user. If your monitoring produces a notification that is not matched by any of your "
                "notification rules, the notification will not be sent out. To prevent that, please "
                "configure either the global setting or enable the fallback contact option for at least "
                "one of your users.") % url)


    def _fallback_mail_contacts_configured(self):
        current_settings = watolib.load_configuration_settings()
        if current_settings.get("notification_fallback_email"):
            return True

        for user_id, user in userdb.load_users(lock=False).items():
            if user.get("fallback_contact", False):
                return True

        return False


    def _show_bulk_notifications(self):
        if self._show_bulks:
            if not self._render_bulks(only_ripe = False): # Warn if there are unsent bulk notificatios
                html.message(_("Currently there are no unsent notification bulks pending."))
        else:
            self._render_bulks(only_ripe = True) # Warn if there are unsent bulk notificatios


    def _render_bulks(self, only_ripe):
        bulks = watolib.check_mk_local_automation("notification-get-bulks", [ "1" if only_ripe else "0" ], None)
        if not bulks:
            return False

        if only_ripe:
            table.begin(title = _("Overdue bulk notifications!"))
        else:
            table.begin(title = _("Open bulk notifications"))

        for dir, age, interval, timeperiod, maxcount, uuids in bulks:
            dirparts = dir.split("/")
            contact = dirparts[-3]
            method = dirparts[-2]
            bulk_id = dirparts[-1].split(",", 2)[-1]
            table.row()
            table.cell(_("Contact"), contact)
            table.cell(_("Method"), method)
            table.cell(_("Bulk ID"), bulk_id)
            table.cell(_("Max. Age (sec)"), "%s" % interval, css="number")
            table.cell(_("Age (sec)"), "%d" % age, css="number")
            if interval and age >= interval:
                html.icon(_("Age of oldest notification is over maximum age"), "warning")
            table.cell(_("Timeperiod"), "%s" % timeperiod)
            table.cell(_("Max. Count"), str(maxcount), css="number")
            table.cell(_("Count"), str(len(uuids)), css="number")
            if len(uuids) >= maxcount:
                html.icon(_("Number of notifications exceeds maximum allowed number"), "warning")
        table.end()
        return True


    def _show_notification_backlog(self):
        """Show recent notifications. We can use them for rule analysis"""
        if not self._show_backlog:
            return

        backlog = store.load_data_from_file(cmk.paths.var_dir + "/notify/backlog.mk", [])
        if not backlog:
            return

        table.begin(table_id = "backlog", title = _("Recent notifications (for analysis)"), sortable=False)
        for nr, context in enumerate(backlog):
            self._convert_context_to_unicode(context)
            table.row()
            table.cell("&nbsp;", css="buttons")

            analyse_url = html.makeuri([("analyse", str(nr))])
            html.icon_button(analyse_url, _("Analyze ruleset with this notification"), "analyze")

            html.icon_button(None, _("Show / hide notification context"),
                             "toggle_context",
                             onclick="toggle_container('notification_context_%d')" % nr)

            replay_url = html.makeactionuri([("_replay", str(nr))])
            html.icon_button(replay_url, _("Replay this notification, send it again!"), "replay")

            if html.var("analyse") and nr == int(html.var("analyse")):
                html.icon(_("You are analysing this notification"), "rulematch")

            table.cell(_("Nr."), nr+1, css="number")
            if "MICROTIME" in context:
                date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(context["MICROTIME"]) / 1000000.0))
            else:
                date = context.get("SHORTDATETIME") or \
                       context.get("LONGDATETIME") or \
                       context.get("DATE") or \
                       _("Unknown date")

            table.cell(_("Date/Time"), date, css="nobr")
            nottype = context.get("NOTIFICATIONTYPE", "")
            table.cell(_("Type"), nottype)

            if nottype in [ "PROBLEM", "RECOVERY" ]:
                if context.get("SERVICESTATE"):
                    statename = context["SERVICESTATE"][:4]
                    state = context["SERVICESTATEID"]
                    css = "state svcstate state%s" % state
                else:
                    statename = context.get("HOSTSTATE")[:4]
                    state = context["HOSTSTATEID"]
                    css = "state hstate hstate%s" % state
                table.cell(_("State"), statename, css=css)
            elif nottype.startswith("DOWNTIME"):
                table.cell(_("State"))
                html.icon(_("Downtime"), "downtime")
            elif nottype.startswith("ACK"):
                table.cell(_("State"))
                html.icon(_("Acknowledgement"), "ack")
            elif nottype.startswith("FLAP"):
                table.cell(_("State"))
                html.icon(_("Flapping"), "flapping")
            else:
                table.cell(_("State"), "")

            table.cell(_("Host"), context.get("HOSTNAME", ""))
            table.cell(_("Service"), context.get("SERVICEDESC", ""))
            output = context.get("SERVICEOUTPUT", context.get("HOSTOUTPUT"))

            table.cell(_("Plugin output"), utils.format_plugin_output(output, shall_escape=config.escape_plugin_output))

            # Add toggleable notitication context
            table.row(class_="notification_context hidden",
                      id_="notification_context_%d" % nr)
            table.cell(colspan=8)

            html.open_table()
            for nr, (key, val) in enumerate(sorted(context.items())):
                if nr % 2 == 0:
                    if nr != 0:
                        html.close_tr()
                    html.open_tr()
                html.th(key)
                html.td(val)
            html.close_table()

            # This dummy row is needed for not destroying the odd/even row highlighting
            table.row(class_="notification_context hidden")

        table.end()


    def _convert_context_to_unicode(self, context):
        # Convert all values to unicode
        for key, value in context.iteritems():
            if type(value) == str:
                try:
                    value_unicode = value.decode("utf-8")
                except:
                    try:
                        value_unicode = value.decode("latin-1")
                    except:
                        value_unicode = u"(Invalid byte sequence)"
                context[key] = value_unicode


    # TODO: Refactor this
    def _show_rules(self):
        # Do analysis
        if html.var("analyse"):
            nr = int(html.var("analyse"))
            analyse = watolib.check_mk_local_automation("notification-analyse", [str(nr)], None)
        else:
            analyse = False

        start_nr = 0
        rules= self._get_notification_rules()
        self._render_notification_rules(rules, show_title = True, analyse=analyse, start_nr = start_nr)
        start_nr += len(rules)

        if self._show_user_rules:
            users = userdb.load_users()
            userids = users.keys()
            userids.sort() # Create same order as modules/notification.py
            for userid in userids:
                user = users[userid]
                user_rules = user.get("notification_rules", [])
                if user_rules:
                    self._render_notification_rules(user_rules, userid, show_title = True, show_buttons = False, analyse=analyse, start_nr = start_nr)
                    start_nr += len(user_rules)

        if analyse:
            table.begin(table_id = "plugins", title = _("Resulting notifications"))
            for contact, plugin, parameters, bulk in analyse[1]:
                table.row()
                if contact.startswith('mailto:'):
                    contact = contact[7:] # strip of fake-contact mailto:-prefix
                table.cell(_("Recipient"), contact)
                table.cell(_("Plugin"), self._vs_notification_scripts().value_to_text(plugin))
                table.cell(_("Plugin parameters"), ", ".join(parameters))
                table.cell(_("Bulking"))
                if bulk:
                    html.write(_("Time horizon") + ": " + Age().value_to_text(bulk["interval"]))
                    html.write_text(", %s: %d" % (_("Maximum count"), bulk["count"]))
                    html.write(", %s %s" % (_("group by"), self._vs_notification_bulkby().value_to_text(bulk["groupby"])))

            table.end()


    def _vs_notification_scripts(self):
        return DropdownChoice(
           title = _("Notification Script"),
           choices = watolib.notification_script_choices,
           default_value = "mail"
        )




class UserNotificationsMode(NotificationsMode):
    def __init__(self):
        super(UserNotificationsMode, self).__init__()
        self._start_async_repl = False


    def _from_vars(self):
        self._users = userdb.load_users(lock=html.is_transaction() or html.has_var("_move"))

        try:
            user = self._users[self._user_id()]
        except KeyError:
            raise MKUserError(None, _('The requested user does not exist'))

        self._rules = user.setdefault("notification_rules", [])


    @abc.abstractmethod
    def _user_id(self):
        raise NotImplementedError()


    def title(self):
        return _("Custom notification table for user ") + self._user_id()


    def buttons(self):
        html.context_button(_("All Users"), watolib.folder_preserving_link([("mode", "users")]), "back")
        html.context_button(_("User Properties"),
            watolib.folder_preserving_link([("mode", "edit_user"), ("edit", self._user_id())]), "edit")
        html.context_button(_("New Rule"),
            watolib.folder_preserving_link([("mode", "notification_rule"), ("user", self._user_id())]), "new")


    def action(self):
        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = self._rules[nr]
            c = wato_confirm(_("Confirm notification rule deletion"),
                             _("Do you really want to delete the notification rule <b>%d</b> <i>%s</i>?") %
                               (nr, rule.get("description","")))
            if c:
                del self._rules[nr]
                userdb.save_users(self._users)

                self._add_change("notification-delete-user-rule",
                    _("Deleted notification rule %d of user %s") % (nr, self._user_id()))
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                rule = self._rules[from_pos]
                del self._rules[from_pos] # make to_pos now match!
                self._rules[to_pos:to_pos] = [rule]
                userdb.save_users(self._users)

                self._add_change("notification-move-user-rule",
                    _("Changed position of notification rule %d of user %s") % (from_pos, self._user_id()))


    def page(self):
        if self._start_async_repl:
            user_profile_async_replication_dialog(sites=watolib.get_notification_sync_sites())
            html.h3(_('Notification Rules'))

        self._render_notification_rules(self._rules, self._user_id(),
            profilemode=isinstance(self, ModePersonalUserNotifications))



@mode_registry.register
class ModeUserNotifications(UserNotificationsMode):
    @classmethod
    def name(cls):
        return "user_notifications"


    @classmethod
    def permissions(cls):
        return ["users"]


    def _user_id(self):
        return html.get_unicode_input("user")



@mode_registry.register
class ModePersonalUserNotifications(UserNotificationsMode):
    @classmethod
    def name(cls):
        return "user_notifications_p"


    @classmethod
    def permissions(cls):
        return None


    def __init__(self):
        super(ModePersonalUserNotifications, self).__init__()
        config.user.need_permission("general.edit_notifications")


    def _user_id(self):
        return config.user.id


    def _add_change(self, log_what, log_text):
        if config.has_wato_slave_sites():
            self._start_async_repl = True
            watolib.log_audit(None, log_what, log_text)
        else:
            super(ModePersonalUserNotifications, self)._add_change(log_what, log_text)


    def title(self):
        return _("Your personal notification rules")


    def buttons(self):
        html.context_button(_("Profile"), "user_profile.py", "back")
        html.context_button(_("New Rule"), watolib.folder_preserving_link([("mode", "notification_rule_p")]), "new")



# TODO: Split editing of user notification rule and global notification rule
#       into separate classes
class EditNotificationRuleMode(NotificationsMode):
    def __init__(self):
        super(EditNotificationRuleMode, self).__init__()
        self._start_async_repl = False


    # TODO: Refactor this
    def _from_vars(self):
        self._edit_nr = html.get_integer_input("edit", -1)
        self._clone_nr = html.get_integer_input("clone", -1)
        self._new = self._edit_nr < 0

        if self._user_id():
            self._users = userdb.load_users(lock=html.is_transaction())
            if self._user_id() not in self._users:
                raise MKUserError(None, _("The user you are trying to edit "
                                          "notification rules for does not exist."))
            user = self._users[self._user_id()]
            self._rules = user.setdefault("notification_rules", [])
        else:
            self._rules = watolib.load_notification_rules(lock=html.is_transaction())

        if self._new:
            if self._clone_nr >= 0 and not html.var("_clear"):
                self._rule = {}
                try:
                    self._rule.update(self._rules[self._clone_nr])
                except IndexError:
                    raise MKUserError(None, _("This %s does not exist.") % "notification rule")
            else:
                self._rule = {}
        else:
            try:
                self._rule = self._rules[self._edit_nr]
            except IndexError:
                raise MKUserError(None, _("This %s does not exist.") % "notification rule")


    def _valuespec(self):
        return self._vs_notification_rule(self._user_id())


    # TODO: Refactor this mess
    def _vs_notification_rule(self, userid=None):
        if userid:
            contact_headers = []
            section_contacts = []
            section_override = []
        else:
            contact_headers = [
                ( _("Contact Selection"), [ "contact_all", "contact_all_with_email", "contact_object",
                                            "contact_users", "contact_groups", "contact_emails", "contact_match_macros",
                                            "contact_match_groups", ] ),
            ]
            section_contacts = [
                # Contact selection
                ( "contact_object",
                  Checkbox(
                      title = _("All contacts of the notified object"),
                      label = _("Notify all contacts of the notified host or service."),
                      default_value = True,
                  )
                ),
                ( "contact_all",
                  Checkbox(
                      title = _("All users"),
                      label = _("Notify all users"),
                  )
                ),
                ( "contact_all_with_email",
                  Checkbox(
                      title = _("All users with an email address"),
                      label = _("Notify all users that have configured an email address in their profile"),
                  )
                ),
                ( "contact_users",
                  ListOf(
                      UserSelection(only_contacts = False),
                      title = _("The following users"),
                      help = _("Enter a list of user IDs to be notified here. These users need to be members "
                               "of at least one contact group in order to be notified."),
                      movable = False,
                      add_label = _("Add user"),
                  )
                ),
                ( "contact_groups",
                  ListOf(
                      cmk.gui.plugins.wato.GroupSelection("contact"),
                      title = _("The members of certain contact groups"),
                      movable = False,
                  )
                ),
                ( "contact_emails",
                  ListOfStrings(
                      valuespec = EmailAddress(size = 44),
                      title = _("The following explicit email addresses"),
                      orientation = "vertical",
                  )
                ),
                ( "contact_match_macros",
                  ListOf(
                      Tuple(
                          elements = [
                              TextAscii(
                                  title = _("Name of the macro"),
                                  help = _("As configured in the users settings. Do not add a leading underscore."),
                                  allow_empty = False,
                              ),
                              RegExp(
                                  title = _("Required match (regular expression)"),
                                  help = _("This expression must match the value of the variable"),
                                  allow_empty = False,
                                  mode = RegExp.complete,
                             ),
                          ]
                      ),
                      title = _("Restrict by custom macros"),
                      help = _("Here you can <i>restrict</i> the list of contacts that has been "
                               "built up by the previous options to those who have certain values "
                               "in certain custom macros. If you add more than one macro here then "
                               "<i>all</i> macros must match. The matches are regular expressions "
                               "that must fully match the value of the macro."),
                      add_label = _("Add condition"),
                  )
                ),
                ( "contact_match_groups",
                  ListOf(
                      cmk.gui.plugins.wato.GroupSelection("contact"),
                      title = _("Restrict by contact groups"),
                      help = _("Here you can <i>restrict</i> the list of contacts that has been "
                               "built up by the previous options to those that are members of "
                               "selected contact groups. If you select more than one contact group here then "
                               "the user must be member of <i>all</i> these groups."),
                      add_label = _("Add Group"),
                      movable = False,
                  )
                ),
            ]
            section_override = [
                ( "allow_disable",
                  Checkbox(
                    title = _("Overriding by users"),
                    help = _("If you uncheck this option then users are not allowed to deactive notifications "
                             "that are created by this rule."),
                    label = _("allow users to deactivate this notification"),
                    default_value = True,
                  )
                ),
            ]

        bulk_options = [
                    ("count", Integer(
                        title = _("Maximum bulk size"),
                        label = _("Bulk up to"),
                        unit  = _("Notifications"),
                        help = _("At most that many Notifications are kept back for bulking. A value of "
                                "1 essentially turns off notification bulking."),
                        default_value = 1000,
                        minvalue = 1,
                    )),
                    ("groupby",
                        self._vs_notification_bulkby(),
                    ),
                    ("groupby_custom", ListOfStrings(
                        valuespec = ID(),
                        orientation = "horizontal",
                        title = _("Create separate notification bulks for different values of the following custom macros"),
                        help = _("If you enter the names of host/service-custom macros here then for each different "
                                "combination of values of those macros a separate bulk will be created. This can be used "
                                "in combination with the grouping by folder, host etc. Omit any leading underscore. "
                                "<b>Note</b>: If you are using "
                                "Nagios as a core you need to make sure that the values of the required macros are "
                                "present in the notification context. This is done in <tt>check_mk_templates.cfg</tt>. If you "
                                "macro is <tt>_FOO</tt> then you need to add the variables <tt>NOTIFY_HOST_FOO</tt> and "
                                "<tt>NOTIFY_SERVICE_FOO</tt>."),
                    )),
                    ("bulk_subject", TextAscii(
                        title = _("Subject for bulk notifications"),
                        help = _("Customize the subject for bulk notifications and overwrite "
                                    "default subject <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for HOST</tt>"
                                    " resp. <tt>Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts</tt>. "
                                    "Both macros <tt>$COUNT_NOTIFICATIONS$</tt> and <tt>$COUNT_HOSTS$</tt> can be used in "
                                    "any customized subject. If <tt>$COUNT_NOTIFICATIONS$</tt> is used, the amount of "
                                    "notifications will be inserted and if you use <tt>$COUNT_HOSTS$</tt> then the "
                                    "amount of hosts will be applied."),
                        size = 80,
                        default_value = "Check_MK: $COUNT_NOTIFICATIONS$ notifications for $COUNT_HOSTS$ hosts"
                    )),
        ]

        return Dictionary(
            title = _("Rule Properties"),
            elements = rule_option_elements()
                + section_override
                + self._rule_match_conditions()
                + section_contacts
                + [
                    # Notification
                    ( "notify_plugin",
                    watolib.get_vs_notification_methods(),
                    ),
                    ("bulk", Transform(
                        CascadingDropdown(
                            title = "Notification Bulking",
                            orientation = "vertical",
                            choices = [
                                ("always", _("Always bulk"), Dictionary(
                                    help = _("Enabling the bulk notifications will collect several subsequent notifications "
                                            "for the same contact into one single notification, which lists of all the "
                                            "actual problems, e.g. in a single email. This cuts down the number of notifications "
                                            "in cases where many (related) problems occur within a short time."),
                                    elements = [
                                        ( "interval", Age(
                                            title = _("Time horizon"),
                                            label = _("Bulk up to"),
                                            help = _("Notifications are kept back for bulking at most for this time."),
                                            default_value = 60,
                                        )),
                                        ] + bulk_options,
                                    columns = 1,
                                    optional_keys = ["bulk_subject"],
                                )),
                                ("timeperiod", _("Bulk during timeperiod"), Dictionary(
                                    help = _("By enabling this option notifications will be bulked only if the "
                                            "specified timeperiod is active. When the timeperiod ends a "
                                            "bulk containing all notifications that appeared during that time "
                                            "will be sent. "
                                            "If bulking should be enabled outside of the timeperiod as well, "
                                            "the option \"Also Bulk outside of timeperiod\" can be used."),
                                    elements = [
                                        ("timeperiod",
                                        TimeperiodSelection(
                                            title = _("Only bulk notifications during the following timeperiod"),
                                        )),
                                    ] + bulk_options + [
                                        ("bulk_outside", Dictionary(
                                            title = _("Also bulk outside of timeperiod"),
                                            help = _("By enabling this option notifications will be bulked "
                                                    "outside of the defined timeperiod as well."),
                                            elements = [
                                                ( "interval", Age(
                                                    title = _("Time horizon"),
                                                    label = _("Bulk up to"),
                                                    help = _("Notifications are kept back for bulking at most for this time."),
                                                    default_value = 60,
                                                )),
                                                ] + bulk_options,
                                            columns = 1,
                                            optional_keys = ["bulk_subject"],
                                        )),
                                    ],
                                    columns = 1,
                                    optional_keys = ["bulk_subject", "bulk_outside"],
                                )),
                            ],
                        ),
                        forth = lambda x: x if isinstance(x, tuple) else ("always", x)
                    )),
            ],
            optional_keys = [ "match_site", "match_folder", "match_hosttags", "match_hostgroups", "match_hosts", "match_exclude_hosts",
                              "match_servicegroups", "match_exclude_servicegroups", "match_servicegroups_regex", "match_exclude_servicegroups_regex",
                              "match_services", "match_exclude_services",
                              "match_contacts", "match_contactgroups",
                              "match_plugin_output",
                              "match_timeperiod", "match_escalation", "match_escalation_throttle",
                              "match_sl", "match_host_event", "match_service_event", "match_ec", "match_notification_comment",
                              "match_checktype", "bulk", "contact_users", "contact_groups", "contact_emails",
                              "contact_match_macros", "contact_match_groups" ],
            headers = [
                ( _("Rule Properties"), [ "description", "comment", "disabled", "docu_url", "allow_disable" ] ),
                ( _("Notification Method"), [ "notify_plugin", "notify_method", "bulk" ] ),]
                + contact_headers
                + [
                ( _("Conditions"),         [ "match_site", "match_folder", "match_hosttags", "match_hostgroups",
                                             "match_hosts", "match_exclude_hosts", "match_servicegroups",
                                             "match_exclude_servicegroups", "match_servicegroups_regex", "match_exclude_servicegroups_regex",
                                             "match_services", "match_exclude_services",
                                             "match_checktype",
                                             "match_contacts", "match_contactgroups",
                                             "match_plugin_output",
                                             "match_timeperiod",
                                             "match_escalation", "match_escalation_throttle",
                                             "match_sl", "match_host_event", "match_service_event", "match_ec", "match_notification_comment" ] ),
            ],
            render = "form",
            form_narrow = True,
            validate = self._validate_notification_rule,
        )


    def _validate_notification_rule(self, rule, varprefix):
        if "bulk" in rule and rule["notify_plugin"][1] == None:
            raise MKUserError(varprefix + "_p_bulk_USE",
                 _("It does not make sense to add a bulk configuration for cancelling rules."))

        if "bulk" in rule or "bulk_period" in rule:
            if rule["notify_plugin"][0]:
                info = watolib.load_notification_scripts()[rule["notify_plugin"][0]]
                if not info["bulk"]:
                    raise MKUserError(varprefix + "_p_notify_plugin",
                          _("The notification script %s does not allow bulking.") % info["title"])
            else:
                raise MKUserError(varprefix + "_p_notify_plugin",
                      _("Legacy ASCII Emails do not support bulking. You can either disable notification "
                        "bulking or choose another notification plugin which allows bulking."))


    @abc.abstractmethod
    def _user_id(self):
        raise NotImplementedError()


    @abc.abstractmethod
    def _back_mode(self):
        raise NotImplementedError()


    def title(self):
        if self._new:
            if self._user_id():
                return _("Create new notification rule for user %s") % self._user_id()
            else:
                return _("Create new notification rule")
        else:
            if self._user_id():
                return _("Edit notification rule %d of user %s") % (self._edit_nr, self._user_id())
            else:
                return _("Edit notification rule %d") % self._edit_nr


    def buttons(self):
        html.context_button(_("All Rules"),
            watolib.folder_preserving_link([("mode", "notifications"), ("userid", self._user_id())]), "back")


    def action(self):
        if not html.check_transaction():
            return self._back_mode()

        vs = self._valuespec()
        self._rule = vs.from_html_vars("rule")
        if self._user_id():
            self._rule["contact_users"] = [ self._user_id() ] # Force selection of our user

        vs.validate_value(self._rule, "rule")

        if self._user_id():
            # User rules are always allow_disable
            # The parameter is set just after the validation, since the allow_disable
            # key isn't in the valuespec. Curiously, the validation does not fail
            # even the allow_disable key is set before the validate_value...
            self._rule["allow_disable"] = True

        if self._new and self._clone_nr >= 0:
            self._rules[self._clone_nr:self._clone_nr] = [ self._rule ]
        elif self._new:
            self._rules[0:0] = [ self._rule ]
        else:
            self._rules[self._edit_nr] = self._rule

        if self._user_id():
            userdb.save_users(self._users)
        else:
            watolib.save_notification_rules(self._rules)

        if self._new:
            log_what = "new-notification-rule"
            if self._user_id():
                log_text = _("Created new notification rule for user %s") % self._user_id()
            else:
                log_text = _("Created new notification rule")
        else:
            log_what = "edit-notification-rule"
            if self._user_id():
                log_text = _("Changed notification rule %d of user %s") % (self._edit_nr, self._user_id())
            else:
                log_text = _("Changed notification rule %d") % self._edit_nr
        self._add_change(log_what, log_text)

        return self._back_mode()

    def page(self):
        if self._start_async_repl:
            user_profile_async_replication_dialog(sites=watolib.get_notification_sync_sites())
            return

        html.begin_form("rule", method = "POST")
        vs = self._valuespec()
        vs.render_input("rule", self._rule)
        vs.set_focus("rule")
        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()



@mode_registry.register
class ModeEditNotificationRule(EditNotificationRuleMode):
    @classmethod
    def name(cls):
        return "notification_rule"


    @classmethod
    def permissions(cls):
        return ["notifications"]


    def _user_id(self):
        return html.get_unicode_input("user")



    def _back_mode(self):
        if self._user_id():
            return "user_notifications"
        else:
            return "notifications"



@mode_registry.register
class ModeEditPersonalNotificationRule(EditNotificationRuleMode):
    @classmethod
    def name(cls):
        return "notification_rule_p"


    @classmethod
    def permissions(cls):
        return None


    def __init__(self):
        super(ModeEditPersonalNotificationRule, self).__init__()
        config.user.need_permission("general.edit_notifications")


    def _user_id(self):
        return config.user.id


    def _add_change(self, log_what, log_text):
        if config.has_wato_slave_sites():
            self._start_async_repl = True
            watolib.log_audit(None, log_what, log_text)
        else:
            super(ModeEditPersonalNotificationRule, self)._add_change(log_what, log_text)


    def _back_mode(self):
        if config.has_wato_slave_sites():
            return
        else:
            return "user_notifications_p"


    def title(self):
        if self._new:
            return _("Create new notification rule")
        else:
            return _("Edit notification rule %d") % self._edit_nr


    def buttons(self):
        html.context_button(_("All Rules"),
            watolib.folder_preserving_link([("mode", "user_notifications_p")]), "back")


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

        domain, valuespec, need_restart, allow_reset, in_global_settings = watolib.configvars()[varname]
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
            else:
                return "edit_site_globals"

        elif c == False:
            return ""

        else:
            return None


    def _edit_mode(self):
        return "edit_site_configvar"


    def page(self):
        search = get_search_expression()
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
#   .--Users/Contacts------------------------------------------------------.
#   | _   _                      ______            _             _         |
#   || | | |___  ___ _ __ ___   / / ___|___  _ __ | |_ __ _  ___| |_ ___   |
#   || | | / __|/ _ \ '__/ __| / / |   / _ \| '_ \| __/ _` |/ __| __/ __|  |
#   || |_| \__ \  __/ |  \__ \/ /| |__| (_) | | | | || (_| | (__| |_\__ \  |
#   | \___/|___/\___|_|  |___/_/  \____\___/|_| |_|\__\__,_|\___|\__|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing users and contacts.                                |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeUsers(WatoMode):
    @classmethod
    def name(cls):
        return "users"


    @classmethod
    def permissions(cls):
        return ["users"]


    def __init__(self):
        super(ModeUsers, self).__init__()
        self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()


    def title(self):
        return _("Users")


    def buttons(self):
        global_buttons()
        html.context_button(_("New user"), watolib.folder_preserving_link([("mode", "edit_user")]), "new")
        if config.user.may("wato.custom_attributes"):
            html.context_button(_("Custom attributes"), watolib.folder_preserving_link([("mode", "user_attrs")]), "custom_attr")
        if userdb.sync_possible():
            if not self._job_snapshot.is_running():
                html.context_button(_("Sync users"), html.makeactionuri([("_sync", 1)]), "replicate")
                html.context_button(_("Last sync result"), self._job_details_url(), "background_job_details")


        if config.user.may("general.notify"):
            html.context_button(_("Notify users"), 'notify.py', "notification")
        html.context_button(_("LDAP connections"), watolib.folder_preserving_link([("mode", "ldap_config")]), "ldap")


    def action(self):
        if html.var('_delete'):
            delid = html.get_unicode_input("_delete")
            c = wato_confirm(_("Confirm deletion of user %s") % delid,
                             _("Do you really want to delete the user %s?") % delid)
            if c:
                watolib.delete_users([delid])
            elif c == False:
                return ""

        elif html.var('_sync'):
            try:
                html.check_transaction()

                job = userdb.UserSyncBackgroundJob()
                if job.is_running():
                    raise MKUserError(None, _("Another synchronization job is already running"))
                job.set_function(job.do_sync, add_to_changelog=True, enforce_sync=True)
                job.start()

                self._job_snapshot = job.get_status_snapshot()
            except Exception, e:
                logger.exception()
                raise MKUserError(None, traceback.format_exc().replace('\n', '<br>\n'))

        elif html.var("_bulk_delete_users"):
            return self._bulk_delete_users_after_confirm()

        elif html.check_transaction():
            action_handler = gui_background_job.ActionHandler(stylesheets=wato_styles)
            action_handler.handle_actions()
            if action_handler.did_acknowledge_job():
                self._job_snapshot = userdb.UserSyncBackgroundJob().get_status_snapshot()
                return None, _("Synchronization job acknowledged")


    def _bulk_delete_users_after_confirm(self):
        selected_users = []
        users = userdb.load_users()
        for varname in html.all_varnames_with_prefix("_c_user_"):
            if html.get_checkbox(varname):
                user = base64.b64decode(varname.split("_c_user_")[-1]).decode("utf-8")
                if user in users:
                    selected_users.append(user)

        if selected_users:
            c = wato_confirm(_("Confirm deletion of %d users") % len(selected_users),
                             _("Do you really want to delete %d users?") % len(selected_users))
            if c:
                watolib.delete_users(selected_users)
            elif c == False:
                return ""


    def page(self):
        if not self._job_snapshot.exists():
            # Skip if snapshot doesnt exists
            pass

        elif self._job_snapshot.is_running():
            # Still running
            html.message(_("User synchronization currently running: %s") % self._job_details_link())
            url = html.makeuri([])
            html.immediate_browser_redirect(2, url)

        elif self._job_snapshot.state() == gui_background_job.background_job.JobStatus.state_finished \
             and not self._job_snapshot.acknowledged_by():
            # Just finished, auto-acknowledge
            userdb.UserSyncBackgroundJob().acknowledge(config.user.id)
            #html.message(_("User synchronization successful"))

        elif not self._job_snapshot.acknowledged_by() and self._job_snapshot.has_exception():
            # Finished, but not OK - show info message with links to details
            html.show_warning(_("Last user synchronization ran into an exception: %s") % self._job_details_link())

        self._show_user_list()



    def _job_details_link(self):
        job = userdb.UserSyncBackgroundJob().get_status_snapshot()
        return html.render_a("%s" % job.get_title(), href=self._job_details_url())


    def _job_details_url(self):
        return html.makeuri_contextless([
            ("mode", "background_job_details"),
            ("back_url", html.makeuri_contextless([("mode", "users")], filename="%s.py" % html.myfile)),
            ("job_id", self._job_snapshot.get_job_id())
        ], filename="wato.py")


    def _show_job_info(self):
        if self._job_snapshot.is_running():
            html.h3(_("Current status of synchronization process"))
            html.javascript("set_reload(0.8)")
        else:
            html.h3(_("Result of last synchronization process"))

        job_manager = gui_background_job.GUIBackgroundJobManager()
        job_manager.show_job_details_from_snapshot(job_snapshot=self._job_snapshot)
        html.br()


    def _show_user_list(self):
        visible_custom_attrs = [
            (name, attr)
            for name, attr
            in userdb.get_user_attributes()
            if attr.show_in_table()
        ]

        users = userdb.load_users()

        entries = users.items()
        entries.sort(cmp = lambda a, b: cmp(a[1].get("alias", a[0]).lower(), b[1].get("alias", b[0]).lower()))

        html.begin_form("bulk_delete_form", method = "POST")

        roles = userdb.load_roles()
        timeperiods = watolib.load_timeperiods()
        contact_groups = userdb.load_group_information().get("contact", {})

        table.begin("users", None, empty_text = _("No users are defined yet."))
        online_threshold = time.time() - config.user_online_maxage
        for id, user in entries:
            table.row()

            # Checkboxes
            table.cell(html.render_input("_toggle_group", type_="button",
                        class_="checkgroup", onclick="toggle_all_rows();",
                        value='X'), sortable=False, css="checkbox")

            if id != config.user.id:
                html.checkbox("_c_user_%s" % base64.b64encode(id.encode("utf-8")))

            user_connection_id = userdb.cleanup_connection_id(user.get('connector'))
            connection = userdb.get_connection(user_connection_id)

            # Buttons
            table.cell(_("Actions"), css="buttons")
            if connection: # only show edit buttons when the connector is available and enabled
                edit_url = watolib.folder_preserving_link([("mode", "edit_user"), ("edit", id)])
                html.icon_button(edit_url, _("Properties"), "edit")

                clone_url = watolib.folder_preserving_link([("mode", "edit_user"), ("clone", id)])
                html.icon_button(clone_url, _("Create a copy of this user"), "clone")

            delete_url = make_action_link([("mode", "users"), ("_delete", id)])
            html.icon_button(delete_url, _("Delete"), "delete")

            notifications_url = watolib.folder_preserving_link([("mode", "user_notifications"), ("user", id)])
            if watolib.load_configuration_settings().get("enable_rulebased_notifications"):
                html.icon_button(notifications_url, _("Custom notification table of this user"), "notifications")

            # ID
            table.cell(_("ID"), id)

            # Online/Offline
            if config.save_user_access_times:
                last_seen = user.get('last_seen', 0)
                if last_seen >= online_threshold:
                    title = _('Online')
                    img_txt = 'online'
                elif last_seen != 0:
                    title = _('Offline')
                    img_txt = 'offline'
                elif last_seen == 0:
                    title = _('Never logged in')
                    img_txt = 'inactive'

                title += ' (%s %s)' % (render.date(last_seen), render.time_of_day(last_seen))
                table.cell(_("Act."))
                html.icon(title, img_txt)

                table.cell(_("Last seen"))
                if last_seen != 0:
                    html.write_text("%s %s" % (render.date(last_seen), render.time_of_day(last_seen)))
                else:
                    html.write_text(_("Never logged in"))

            if cmk.is_managed_edition():
                table.cell(_("Customer"), managed.get_customer_name(user))

            # Connection
            if connection:
                table.cell(_("Connection"), '%s (%s)' % (connection.short_title(), user_connection_id))
                locked_attributes = userdb.locked_attributes(user_connection_id)
            else:
                table.cell(_("Connection"), "%s (%s) (%s)" %
                        (_("UNKNOWN"), user_connection_id, _("disabled")), css="error")
                locked_attributes = []

            # Authentication
            if "automation_secret" in user:
                auth_method = _("Automation")
            elif user.get("password") or 'password' in locked_attributes:
                auth_method = _("Password")
            else:
                auth_method = "<i>%s</i>" % _("none")
            table.cell(_("Authentication"), auth_method)

            table.cell(_("State"))
            locked = user.get("locked", False)
            if user.get("locked", False):
                html.icon(_('The login is currently locked'), 'user_locked')

            if "disable_notifications" in user and type(user["disable_notifications"]) == bool:
                disable_notifications_opts = {"disable" : user["disable_notifications"]}
            else:
                disable_notifications_opts = user.get("disable_notifications", {})

            if disable_notifications_opts.get("disable", False):
                html.icon(_('Notifications are disabled'), 'notif_disabled')

            # Full name / Alias
            table.text_cell(_("Alias"), user.get("alias", ""))

            # Email
            table.text_cell(_("Email"), user.get("email", ""))

            # Roles
            table.cell(_("Roles"))
            if user.get("roles", []):
                role_links = [ (watolib.folder_preserving_link([("mode", "edit_role"), ("edit", role)]), roles[role].get("alias"))
                                    for role in user["roles"] ]
                html.write_html(HTML(", ").join(html.render_a(alias, href=link) for (link, alias) in role_links))

            # contact groups
            table.cell(_("Contact groups"))
            cgs = user.get("contactgroups", [])
            if cgs:
                cg_aliases = [contact_groups[c]['alias'] if c in contact_groups else c for c in cgs]
                cg_urls    = [watolib.folder_preserving_link([("mode", "edit_contact_group"), ("edit", c)]) for c in cgs]
                html.write_html(HTML(", ").join(html.render_a(content, href=url) for (content, url) in zip(cg_aliases, cg_urls)))
            else:
                html.i(_("none"))

            #table.cell(_("Sites"))
            #html.write(vs_authorized_sites().value_to_text(user.get("authorized_sites",
            #                                                vs_authorized_sites().default_value())))

            # notifications
            if not watolib.load_configuration_settings().get("enable_rulebased_notifications"):
                table.cell(_("Notifications"))
                if not cgs:
                    html.i(_("not a contact"))
                elif not user.get("notifications_enabled", True):
                    html.write_text(_("disabled"))
                elif user.get("host_notification_options", "") == "" and \
                     user.get("service_notification_options", "") == "":
                    html.write_text(_("all events disabled"))
                else:
                    tp = user.get("notification_period", "24X7")
                    if tp != "24X7" and tp not in timeperiods:
                        tp = tp + _(" (invalid)")
                    elif tp != "24X7":
                        url = watolib.folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tp)])
                        tp = html.render_a(timeperiods[tp].get("alias", tp), href=url)
                    else:
                        tp = _("Always")
                    html.write(tp)

            # the visible custom attributes
            for name, attr in visible_custom_attrs:
                vs = attr.valuespec()
                table.cell(html.attrencode(_u(vs.title())))
                html.write(vs.value_to_text(user.get(name, vs.default_value())))

        table.end()

        html.button("_bulk_delete_users", _("Bulk Delete"), "submit", style="margin-top:10px")
        html.hidden_fields()
        html.end_form()

        if not userdb.load_group_information().get("contact", {}):
            url = "wato.py?mode=contact_groups"
            html.open_div(class_="info")
            html.write(_("Note: you haven't defined any contact groups yet. If you <a href='%s'>"
                         "create some contact groups</a> you can assign users to them und thus "
                         "make them monitoring contacts. Only monitoring contacts can receive "
                         "notifications.") % url)
            html.write(" you can assign users to them und thus "
                        "make them monitoring contacts. Only monitoring contacts can receive "
                        "notifications.")
            html.close_div()


# TODO: Create separate ModeCreateUser()
# TODO: Move CME specific stuff to CME related class
# TODO: Refactor action / page to use less hand crafted logic (valuespecs instead?)
@mode_registry.register
class ModeEditUser(WatoMode):
    @classmethod
    def name(cls):
        return "edit_user"


    @classmethod
    def permissions(cls):
        return ["users"]


    def __init__(self):
        super(ModeEditUser, self).__init__()

        # Load data that is referenced - in order to display dropdown
        # boxes and to check for validity.
        self._contact_groups = userdb.load_group_information().get("contact", {})
        self._timeperiods    = watolib.load_timeperiods()
        self._roles          = userdb.load_roles()

        if cmk.is_managed_edition():
            self._vs_customer = managed.vs_customer()


    def _from_vars(self):
        self._user_id = html.get_unicode_input("edit") # missing -> new user
        self._cloneid = html.get_unicode_input("clone") # Only needed in 'new' mode
        self._is_new_user = self._user_id == None

        self._users = userdb.load_users(lock=html.is_transaction())

        if self._is_new_user:
            if self._cloneid:
                self._user = self._users.get(self._cloneid, userdb.new_user_template('htpasswd'))
            else:
                self._user = userdb.new_user_template('htpasswd')
        else:
            self._user = self._users.get(self._user_id, userdb.new_user_template('htpasswd'))

        self._locked_attributes = userdb.locked_attributes(self._user.get('connector'))


    def title(self):
        if self._is_new_user:
            return _("Create new user")
        else:
            return _("Edit user %s") % self._user_id


    def buttons(self):
        html.context_button(_("Users"), watolib.folder_preserving_link([("mode", "users")]), "back")
        if self._rbn_enabled and not self._is_new_user:
            html.context_button(_("Notifications"), watolib.folder_preserving_link([("mode", "user_notifications"),
                    ("user", self._user_id)]), "notifications")
        return


    def action(self):
        if not html.check_transaction():
            return "users"

        if self._is_new_user:
            self._user_id = UserID(allow_empty = False).from_html_vars("user_id")
            user_attrs = {}
        else:
            self._user_id = html.get_unicode_input("edit").strip()
            user_attrs = self._users[self._user_id]

        # Full name
        user_attrs["alias"] = html.get_unicode_input("alias").strip()

        # Locking
        user_attrs["locked"] = html.get_checkbox("locked")
        increase_serial = False

        if self._user_id in self._users and self._users[self._user_id]["locked"] != user_attrs["locked"] and user_attrs["locked"]:
            increase_serial = True # when user is being locked now, increase the auth serial

        # Authentication: Password or Secret
        auth_method = html.var("authmethod")
        if auth_method == "secret":
            secret = html.var("secret", "").strip()
            user_attrs["automation_secret"] = secret
            user_attrs["password"] = encrypt_password(secret)
            increase_serial = True # password changed, reflect in auth serial

        else:
            password  = html.var("password_" + self._pw_suffix(), '').strip()
            password2 = html.var("password2_" + self._pw_suffix(), '').strip()

            # We compare both passwords only, if the user has supplied
            # the repeation! We are so nice to our power users...
            # Note: this validation is done before the main-validiation later on
            # It doesn't make any sense to put this block into the main validation function
            if password2 and password != password2:
                raise MKUserError("password2", _("The both passwords do not match."))

            # Detect switch back from automation to password
            if "automation_secret" in user_attrs:
                del user_attrs["automation_secret"]
                if "password" in user_attrs:
                    del user_attrs["password"] # which was the encrypted automation password!

            if password:
                user_attrs["password"] = encrypt_password(password)
                user_attrs["last_pw_change"] = int(time.time())
                increase_serial = True # password changed, reflect in auth serial

            # PW change enforcement
            user_attrs["enforce_pw_change"] = html.get_checkbox("enforce_pw_change")
            if user_attrs["enforce_pw_change"]:
                increase_serial = True # invalidate all existing user sessions, enforce relogon


        # Increase serial (if needed)
        if increase_serial:
            user_attrs["serial"] = user_attrs.get("serial", 0) + 1

        # Email address
        user_attrs["email"] = EmailAddressUnicode().from_html_vars("email")

        idle_timeout = watolib.get_vs_user_idle_timeout().from_html_vars("idle_timeout")
        user_attrs["idle_timeout"] = idle_timeout
        if idle_timeout != None:
            user_attrs["idle_timeout"] = idle_timeout
        elif idle_timeout == None and "idle_timeout" in user_attrs:
            del user_attrs["idle_timeout"]

        # Pager
        user_attrs["pager"] = html.var("pager", '').strip()

        if cmk.is_managed_edition():
            customer = self._vs_customer.from_html_vars("customer")
            self._vs_customer.validate_value(customer, "customer")

            if customer != managed.default_customer_id():
                user_attrs["customer"] = customer
            elif "customer" in user_attrs:
                del user_attrs["customer"]

        vs_sites = self._vs_sites()
        authorized_sites = vs_sites.from_html_vars("authorized_sites")
        vs_sites.validate_value(authorized_sites, "authorized_sites")

        if authorized_sites is not None:
            user_attrs["authorized_sites"] = authorized_sites
        elif "authorized_sites" in user_attrs:
            del user_attrs["authorized_sites"]

        # Roles
        user_attrs["roles"] = [role for role in self._roles.keys() if html.get_checkbox("role_" + role)]

        # Language configuration
        set_lang = html.get_checkbox("_set_lang")
        language = html.var("language")
        if set_lang:
            if language == "":
                language = None
            user_attrs["language"] = language
        elif not set_lang and "language" in user_attrs:
            del user_attrs["language"]

        # Contact groups
        cgs = []
        for c in self._contact_groups:
            if html.get_checkbox("cg_" + c):
                cgs.append(c)
        user_attrs["contactgroups"] = cgs

        # Notification settings are only active if we do *not* have
        # rule based notifications!
        if not self._rbn_enabled():
            # Notifications
            user_attrs["notifications_enabled"] = html.get_checkbox("notifications_enabled")

            ntp = html.var("notification_period")
            if ntp not in self._timeperiods:
                ntp = "24X7"
            user_attrs["notification_period"] = ntp

            for what, opts in [ ( "host", "durfs"), ("service", "wucrfs") ]:
                user_attrs[what + "_notification_options"] = "".join(
                  [ opt for opt in opts if html.get_checkbox(what + "_" + opt) ])

            value = watolib.get_vs_flexible_notifications().from_html_vars("notification_method")
            user_attrs["notification_method"] = value
        else:
            user_attrs["fallback_contact"] = html.get_checkbox("fallback_contact")

        # Custom user attributes
        for name, attr in userdb.get_user_attributes():
            value = attr.valuespec().from_html_vars('ua_' + name)
            user_attrs[name] = value

        # Generate user "object" to update
        user_object = {self._user_id: {"attributes": user_attrs, "is_new_user": self._is_new_user}}
        # The following call validates and updated the users
        watolib.edit_users(user_object)
        return "users"


    def page(self):
        # Let exceptions from loading notification scripts happen now
        watolib.load_notification_scripts()

        html.begin_form("user", method="POST")
        html.prevent_password_auto_completion()

        forms.header(_("Identity"))

        # ID
        forms.section(_("Username"), simple = not self._is_new_user)
        if self._is_new_user:
            vs_user_id = UserID(allow_empty = False)

        else:
            vs_user_id = FixedValue(self._user_id)
        vs_user_id.render_input("user_id", self._user_id)

        def lockable_input(name, dflt):
            if not self._is_locked(name):
                html.text_input(name, self._user.get(name, dflt), size = 50)
            else:
                html.write_text(self._user.get(name, dflt))
                html.hidden_field(name, self._user.get(name, dflt))

        # Full name
        forms.section(_("Full name"))
        lockable_input('alias', self._user_id)
        html.help(_("Full name or alias of the user"))

        # Email address
        forms.section(_("Email address"))
        email = self._user.get("email", "")
        if not self._is_locked("email"):
            EmailAddressUnicode().render_input("email", email)
        else:
            html.write_text(email)
            html.hidden_field("email", email)

        html.help(_("The email address is optional and is needed "
                    "if the user is a monitoring contact and receives notifications "
                    "via Email."))

        forms.section(_("Pager address"))
        lockable_input('pager', '')
        html.help(_("The pager address is optional "))

        if cmk.is_managed_edition():
            forms.section(self._vs_customer.title())
            self._vs_customer.render_input("customer", managed.get_customer_id(self._user))

            html.help(self._vs_customer.help())

        vs_sites = self._vs_sites()
        forms.section(vs_sites.title())
        authorized_sites = self._user.get("authorized_sites", vs_sites.default_value())
        if not self._is_locked("authorized_sites"):
            vs_sites.render_input("authorized_sites", authorized_sites)
        else:
            html.write_html(vs_sites.value_to_text(authorized_sites))
        html.help(vs_sites.help())

        self._show_custom_user_attributes('ident')

        forms.header(_("Security"))
        forms.section(_("Authentication"))

        is_automation = self._user.get("automation_secret", None) != None
        html.radiobutton("authmethod", "password", not is_automation,
                         _("Normal user login with password"))
        html.open_ul()
        html.open_table()
        html.open_tr()
        html.td(_("password:"))
        html.open_td()

        if not self._is_locked('password'):
            html.password_input("password_" + self._pw_suffix(), autocomplete="new-password")
            html.close_td()
            html.close_tr()

            html.open_tr()
            html.td(_("repeat:"))
            html.open_td()
            html.password_input("password2_" + self._pw_suffix(), autocomplete="new-password")
            html.write_text(" (%s)" % _("optional"))
            html.close_td()
            html.close_tr()

            html.open_tr()
            html.td("%s:" % _("Enforce change"))
            html.open_td()
            # Only make password enforcement selection possible when user is allowed to change the PW
            if self._is_new_user or config.user_may(self._user_id, 'general.edit_profile') and config.user_may(self._user_id, 'general.change_password'):
                html.checkbox("enforce_pw_change", self._user.get("enforce_pw_change", False),
                              label=_("Change password at next login or access"))
            else:
                html.write_text(_("Not permitted to change the password. Change can not be enforced."))
        else:
            html.i(_('The password can not be changed (It is locked by the user connector).'))
            html.hidden_field('password', '')
            html.hidden_field('password2', '')

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_ul()

        html.radiobutton("authmethod", "secret", is_automation,
                         _("Automation secret for machine accounts"))

        html.open_ul()
        html.text_input("secret", self._user.get("automation_secret", ""), size=30,
                        id_="automation_secret")
        html.write_text(" ")
        html.open_b(style=["position: relative", "top: 4px;"])
        html.write(" &nbsp;")
        html.icon_button("javascript:wato_randomize_secret('automation_secret', 20);",
                    _("Create random secret"), "random")
        html.close_b()
        html.close_ul()

        html.help(_("If you want the user to be able to login "
                    "then specify a password here. Users without a login make sense "
                    "if they are monitoring contacts that are just used for "
                    "notifications. The repetition of the password is optional. "
                    "<br>For accounts used by automation processes (such as fetching "
                    "data from views for further procession), set the method to "
                    "<u>secret</u>. The secret will be stored in a local file. Processes "
                    "with read access to that file will be able to use Multisite as "
                    "a webservice without any further configuration."))

        # Locking
        forms.section(_("Disable password"), simple=True)
        if not self._is_locked('locked'):
            html.checkbox("locked", self._user.get("locked", False), label = _("disable the login to this account"))
        else:
            html.write_text(_('Login disabled') if self._user.get("locked", False) else _('Login possible'))
            html.hidden_field('locked', '1' if self._user.get("locked", False) else '')
        html.help(_("Disabling the password will prevent a user from logging in while "
                     "retaining the original password. Notifications are not affected "
                     "by this setting."))

        forms.section(_("Idle timeout"))
        idle_timeout = self._user.get("idle_timeout")
        if not self._is_locked("idle_timeout"):
            watolib.get_vs_user_idle_timeout().render_input("idle_timeout", idle_timeout)
        else:
            html.write_text(idle_timeout)
            html.hidden_field("idle_timeout", idle_timeout)

        # Roles
        forms.section(_("Roles"))
        entries = self._roles.items()
        entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))
        is_member_of_at_least_one = False
        for role_id, role in entries:
            if not self._is_locked("roles"):
                html.checkbox("role_" + role_id, role_id in self._user.get("roles", []))
                url = watolib.folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                html.a(role["alias"], href=url)
                html.br()
            else:
                is_member = role_id in self._user.get("roles", [])
                if is_member:
                    is_member_of_at_least_one = True
                    url = watolib.folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                    html.a(role["alias"], href=url)
                    html.br()

                html.hidden_field("role_" + role_id, '1' if is_member else '')
        if self._is_locked('roles') and not is_member_of_at_least_one:
            html.i(_('No roles assigned.'))
        self._show_custom_user_attributes('security')

        # Contact groups
        forms.header(_("Contact Groups"), isopen=False)
        forms.section()
        groups_page_url  = watolib.folder_preserving_link([("mode", "contact_groups")])
        group_assign_url = watolib.folder_preserving_link([("mode", "rulesets"), ("group", "grouping")])
        if not self._contact_groups:
            html.write(_("Please first create some <a href='%s'>contact groups</a>") %
                    groups_page_url)
        else:
            entries = sorted([ (group['alias'] or c, c) for c, group in self._contact_groups.items() ])
            is_member_of_at_least_one = False
            for alias, gid in entries:
                is_member = gid in self._user.get("contactgroups", [])

                if not self._is_locked('contactgroups'):
                    html.checkbox("cg_" + gid, gid in self._user.get("contactgroups", []))
                else:
                    if is_member:
                        is_member_of_at_least_one = True
                    html.hidden_field("cg_" + gid, '1' if is_member else '')

                if not self._is_locked('contactgroups') or is_member:
                    url = watolib.folder_preserving_link([("mode", "edit_contact_group"), ("edit", gid)])
                    html.a(alias, href=url)
                    html.br()

            if self._is_locked('contactgroups') and not is_member_of_at_least_one:
                html.i(_('No contact groups assigned.'))

        html.help(_("Contact groups are used to assign monitoring "
                    "objects to users. If you haven't defined any contact groups yet, "
                    "then first <a href='%s'>do so</a>. Hosts and services can be "
                    "assigned to contact groups using <a href='%s'>rules</a>.<br><br>"
                    "If you do not put the user into any contact group "
                    "then no monitoring contact will be created for the user.") %
                                        (groups_page_url, group_assign_url))

        forms.header(_("Notifications"), isopen=False)
        if not self._rbn_enabled():
            forms.section(_("Enabling"), simple=True)
            html.checkbox("notifications_enabled", self._user.get("notifications_enabled", False),
                 label = _("enable notifications"))
            html.help(_("Notifications are sent out "
                        "when the status of a host or service changes."))

            # Notification period
            forms.section(_("Notification time period"))
            choices = [ ( "24X7", _("Always")) ] + \
                      [ ( id, "%s" % (tp["alias"])) for (id, tp) in self._timeperiods.items() ]
            html.dropdown("notification_period", choices, deflt=self._user.get("notification_period"), sorted=True)
            html.help(_("Only during this time period the "
                         "user will get notifications about host or service alerts."))

            # Notification options
            notification_option_names = { # defined here: _() must be executed always!
                "host" : {
                    "d" : _("Host goes down"),
                    "u" : _("Host gets unreachble"),
                    "r" : _("Host goes up again"),
                },
                "service" : {
                    "w" : _("Service goes into warning state"),
                    "u" : _("Service goes into unknown state"),
                    "c" : _("Service goes into critical state"),
                    "r" : _("Service recovers to OK"),
                },
                "both" : {
                    "f" : _("Start or end of flapping state"),
                    "s" : _("Start or end of a scheduled downtime"),
                }
            }

            forms.section(_("Notification Options"))
            for title, what, opts in [ ( _("Host events"), "host", "durfs"),
                          (_("Service events"), "service", "wucrfs") ]:
                html.write_text("%s:" % title)
                html.open_ul()

                user_opts = self._user.get(what + "_notification_options", opts)
                for opt in opts:
                    opt_name = notification_option_names[what].get(opt,
                           notification_option_names["both"].get(opt))
                    html.checkbox(what + "_" + opt, opt in user_opts, label = opt_name)
                    html.br()
                html.close_ul()

            html.help(_("Here you specify which types of alerts "
                       "will be notified to this contact. Note: these settings will only be saved "
                       "and used if the user is member of a contact group."))

            forms.section(_("Notification Method"))
            watolib.get_vs_flexible_notifications().render_input("notification_method", self._user.get("notification_method"))

        else:
            forms.section(_("Fallback notifications"), simple=True)

            html.checkbox("fallback_contact", self._user.get("fallback_contact", False),
                          label = _("Receive fallback notifications"))

            html.help(_("In case none of your notification rules handles a certain event a notification "
                     "will be sent to this contact. This makes sure that in that case at least <i>someone</i> "
                     "gets notified. Furthermore this contact will be used for notifications to any host or service "
                     "that is not known to the monitoring. This can happen when you forward notifications "
                     "from the Event Console.<br><br>Notification fallback can also configured in the global "
                     "setting <a href=\"wato.py?mode=edit_configvar&varname=notification_fallback_email\">"
                        "Fallback email address for notifications</a>."))

        self._show_custom_user_attributes('notify')

        forms.header(_("Personal Settings"), isopen = False)
        select_language(self._user)
        self._show_custom_user_attributes('personal')

        # Later we could add custom macros here, which then could be used
        # for notifications. On the other hand, if we implement some check_mk
        # --notify, we could directly access the data in the account with the need
        # to store values in the monitoring core. We'll see what future brings.
        forms.end()
        html.button("save", _("Save"))
        if self._is_new_user:
            html.set_focus("user_id")
        else:
            html.set_focus("alias")
        html.hidden_fields()
        html.end_form()


    def _rbn_enabled(self):
        # Check if rule based notifications are enabled (via WATO)
        return watolib.load_configuration_settings().get("enable_rulebased_notifications")


    def _pw_suffix(self):
        if self._is_new_user:
            return 'new'
        else:
            return base64.b64encode(self._user_id.encode("utf-8"))


    def _is_locked(self, attr):
        """Returns true if an attribute is locked and should be read only. Is only
        checked when modifying an existing user"""
        return not self._is_new_user and attr in self._locked_attributes


    def _vs_sites(self):
        return Alternative(
            title = _("Authorized sites"),
            help = _("The sites the user is authorized to see in the GUI."),
            default_value = None,
            style = "dropdown",
            elements = [
                FixedValue(None,
                    title = _("All sites"),
                    totext = _("May see all sites"),
                ),
                DualListChoice(
                    title = _("Specific sites"),
                    choices = config.site_choices,
                ),
            ],
        )


    def _show_custom_user_attributes(self, topic):
        for name, attr in userdb.get_user_attributes():
            if topic is not None and topic != attr.topic():
                continue # skip attrs of other topics

            vs = attr.valuespec()
            forms.section(_u(vs.title()))
            if not self._is_locked(name):
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
            else:
                html.write(vs.value_to_text(self._user.get(name, vs.default_value())))
                # Render hidden to have the values kept after saving
                html.open_div(style="display:none")
                vs.render_input("ua_" + name, self._user.get(name, vs.default_value()))
                html.close_div()
            html.help(_u(vs.help()))




#.
#   .--Roles---------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing roles and permissions.                             |
#   | In order to make getting started easier - Check_MK Multisite comes   |
#   | with three builtin-roles: admin, user and guest. These roles have    |
#   | predefined permissions. The builtin roles cannot be deleted. Users   |
#   | listed in admin_users in multisite.mk automatically get the role     |
#   | admin - even if no such user or contact has been configured yet. By  |
#   | that way an initial login - e.g. as omdamin - is possible. The admin |
#   | role cannot be removed from that user as long as he is listed in     |
#   | admin_users. Also the variables guest_users, users and default_user_ |
#   | role still work. That way Multisite is fully operable without WATO   |
#   | and also backwards compatible.                                       |
#   | In WATO you can create further roles and also edit the permissions   |
#   | of the existing roles. Users can be assigned to builtin and custom   |
#   | roles.                                                               |
#   | This modes manages the creation of custom roles and the permissions  |
#   | configuration of all roles.                                          |
#   '----------------------------------------------------------------------'

class RoleManagement(object):
    def __init__(self):
        self._roles = userdb.load_roles()
        super(RoleManagement, self).__init__()


    def _save_roles(self):
        # Reflect the data in the roles dict kept in the config module Needed
        # for instant changes in current page while saving modified roles.
        # Otherwise the hooks would work with old data when using helper
        # functions from the config module
        config.roles.update(self._roles)

        store.mkdir(multisite_dir)
        store.save_to_mk_file(multisite_dir + "roles.mk", "roles", self._roles, pprint_value = config.wato_pprint_config)

        watolib.call_hook_roles_saved(self._roles)


    # Adapt references in users. Builtin rules cannot
    # be renamed and are not handled here. If new_id is None,
    # the role is being deleted
    def _rename_user_role(self, id, new_id):
        users = userdb.load_users(lock = True)
        for user in users.values():
            if id in user["roles"]:
                user["roles"].remove(id)
                if new_id:
                    user["roles"].append(new_id)
        userdb.save_users(users)



@mode_registry.register
class ModeRoles(RoleManagement, WatoMode):
    @classmethod
    def name(cls):
        return "roles"


    @classmethod
    def permissions(cls):
        return ["users"]


    def title(self):
        return _("Roles & Permissions")


    def buttons(self):
        global_buttons()
        html.context_button(_("Matrix"), watolib.folder_preserving_link([("mode", "role_matrix")]), "matrix")


    def action(self):
        if html.var("_delete"):
            delid = html.var("_delete")

            if delid not in self._roles:
                raise MKUserError(None, _("This role does not exist."))

            if html.transaction_valid() and self._roles[delid].get('builtin'):
                raise MKUserError(None, _("You cannot delete the builtin roles!"))

            c = wato_confirm(_("Confirm deletion of role %s") % delid,
                             _("Do you really want to delete the role %s?") % delid)
            if c:
                self._rename_user_role(delid, None) # Remove from existing users
                del self._roles[delid]
                self._save_roles()
                watolib.add_change("edit-roles", _("Deleted role '%s'") % delid, sites=config.get_login_sites())
            elif c == False:
                return ""

        elif html.var("_clone"):
            if html.check_transaction():
                cloneid = html.var("_clone")

                try:
                    cloned_role = self._roles[cloneid]
                except KeyError:
                    raise MKUserError(None, _("This role does not exist."))

                newid = cloneid
                while newid in self._roles:
                    newid += "x"

                new_role = {}
                new_role.update(cloned_role)

                new_alias = new_role["alias"]
                while not watolib.is_alias_used("roles", newid, new_alias)[0]:
                    new_alias += _(" (copy)")
                new_role["alias"] = new_alias

                if cloned_role.get("builtin"):
                    new_role["builtin"] = False
                    new_role["basedon"] = cloneid

                self._roles[newid] = new_role
                self._save_roles()
                watolib.add_change("edit-roles", _("Created new role '%s'") % newid,
                           sites=config.get_login_sites())


    def page(self):
        table.begin("roles")

        users = userdb.load_users()
        for id, role in sorted(self._roles.items(), key = lambda a: (a[1]["alias"],a[0])):
            table.row()

            # Actions
            table.cell(_("Actions"), css="buttons")
            edit_url = watolib.folder_preserving_link([("mode", "edit_role"), ("edit", id)])
            clone_url = make_action_link([("mode", "roles"), ("_clone", id)])
            delete_url = make_action_link([("mode", "roles"), ("_delete", id)])
            html.icon_button(edit_url, _("Properties"), "edit")
            html.icon_button(clone_url, _("Clone"), "clone")
            if not role.get("builtin"):
                html.icon_button(delete_url, _("Delete this role"), "delete")

            # ID
            table.text_cell(_("Name"), id)

            # Alias
            table.text_cell(_("Alias"), role["alias"])

            # Type
            table.cell(_("Type"), _("builtin") if role.get("builtin") else _("custom"))

            # Modifications
            table.cell(_("Modifications"), "<span title='%s'>%s</span>" % (
                _("That many permissions do not use the factory defaults."), len(role["permissions"])))

            # Users
            table.cell(_("Users"),
              HTML(", ").join([ html.render_a(user.get("alias", user_id), watolib.folder_preserving_link([("mode", "edit_user"), ("edit", user_id)]))
                for (user_id, user) in users.items() if id in user["roles"]]))


        # Possibly we could also display the following information
        # - number of set permissions (needs loading users)
        # - number of users with this role
        table.end()



@mode_registry.register
class ModeEditRole(RoleManagement, WatoMode):
    @classmethod
    def name(cls):
        return "edit_role"


    @classmethod
    def permissions(cls):
        return ["users"]


    def __init__(self):
        super(ModeEditRole, self).__init__()

        # Make sure that all dynamic permissions are available (e.g. those for custom
        # views)
        config.load_dynamic_permissions()


    def _from_vars(self):
        self._role_id = html.var("edit")

        try:
            self._role = self._roles[self._role_id]
        except KeyError:
            raise MKGeneralException(_("This role does not exist."))


    def title(self):
        return _("Edit user role %s") % self._role_id


    def buttons(self):
        html.context_button(_("All Roles"), watolib.folder_preserving_link([("mode", "roles")]), "back")


    def action(self):
        if html.form_submitted("search"):
            return

        alias = html.get_unicode_input("alias")

        unique, info = watolib.is_alias_used("roles", self._role_id, alias)
        if not unique:
            raise MKUserError("alias", info)

        new_id = html.var("id")
        if len(new_id) == 0:
            raise MKUserError("id", _("Please specify an ID for the new role."))
        if not re.match("^[-a-z0-9A-Z_]*$", new_id):
            raise MKUserError("id", _("Invalid role ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
        if new_id != self._role_id:
            if new_id in self._roles:
                raise MKUserError("id", _("The ID is already used by another role"))

        self._role["alias"] = alias

        # based on
        if not self._role.get("builtin"):
            basedon = html.var("basedon")
            if basedon not in config.builtin_role_ids:
                raise MKUserError("basedon", _("Invalid valid for based on. Must be id of builtin rule."))
            self._role["basedon"] = basedon

        # Permissions
        permissions = self._role["permissions"]
        for var_name in html.all_varnames_with_prefix("perm_"):
            try:
                perm = config.permissions_by_name[var_name[5:]]
            except KeyError:
                continue

            perm_name = perm["name"]
            value = html.var(var_name)
            if value == "yes":
                permissions[perm_name] = True
            elif value == "no":
                permissions[perm_name] = False
            elif value == "default":
                try:
                    del permissions[perm_name]
                except KeyError:
                    pass # Already at defaults

        if self._role_id != new_id:
            self._roles[new_id] = self._role
            del self._roles[self._role_id]
            self._rename_user_role(self._role_id, new_id)

        self._save_roles()
        watolib.add_change("edit-roles", _("Modified user role '%s'") % new_id,
                            sites=config.get_login_sites())
        return "roles"


    def page(self):
        search = get_search_expression()
        search_form(_("Search for permissions: "), "edit_role")

        html.begin_form("role", method="POST")

        # ID
        forms.header(_("Basic Properties"))
        forms.section(_("Internal ID"), simple = "builtin" in self._role)
        if self._role.get("builtin"):
            html.write_text("%s (%s)" % (self._role_id, _("builtin role")))
            html.hidden_field("id", self._role_id)
        else:
            html.text_input("id", self._role_id)
            html.set_focus("id")

        # Alias
        forms.section(_("Alias"))
        html.help(_("An alias or description of the role"))
        html.text_input("alias", self._role.get("alias", ""), size = 50)

        # Based on
        if not self._role.get("builtin"):
            forms.section(_("Based on role"))
            html.help(_("Each user defined role is based on one of the builtin roles. "
                        "When created it will start with all permissions of that role. When due to a software "
                        "update or installation of an addons new permissions appear, the user role will get or "
                        "not get those new permissions based on the default settings of the builtin role it's "
                        "based on."))
            choices = [ (i, r["alias"]) for i, r in self._roles.items() if r.get("builtin") ]
            html.dropdown("basedon", choices, deflt=self._role.get("basedon", "user"), sorted=True)

        forms.end()

        html.h2(_("Permissions"))

        # Permissions
        base_role_id = self._role.get("basedon", self._role_id)

        html.help(
           _("When you leave the permissions at &quot;default&quot; then they get their "
             "settings from the factory defaults (for builtin roles) or from the "
             "factory default of their base role (for user define roles). Factory defaults "
             "may change due to software updates. When choosing another base role, all "
             "permissions that are on default will reflect the new base role."))

        # Loop all permission sections, but sorted plz
        for section, (prio, section_title, do_sort) in sorted(config.permission_sections.iteritems(),
                                                     key = lambda x: x[1][0], reverse = True):
            # Loop all permissions
            permlist = config.permissions_by_order[:]
            if do_sort:
                permlist.sort(cmp = lambda a,b: cmp(a["title"], b["title"]))

            # Now filter by permission section and the optional search term
            filtered_perms = []
            for perm in permlist:
                pname = perm["name"]
                this_section = pname.split(".")[0]
                if section != this_section:
                    continue # Skip permissions of other sections

                if search and (search not in perm["title"].lower() and search not in pname.lower()):
                    continue

                filtered_perms.append(perm)

            if not filtered_perms:
                continue

            forms.header(section_title, isopen=search != None)
            for perm in filtered_perms:
                pname = perm["name"]

                forms.section(perm["title"])

                pvalue = self._role["permissions"].get(pname)
                def_value = base_role_id in perm["defaults"]

                choices = [ ( "yes", _("yes")),
                            ( "no", _("no")),
                            ( "default", _("default (%s)") % (def_value and _("yes") or _("no") )) ]
                deflt = { True: "yes", False: "no" }.get(pvalue, "default")

                html.dropdown("perm_" + pname, choices, deflt=deflt, style="width: 130px;")
                html.help(perm["description"])

        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()



@mode_registry.register
class ModeRoleMatrix(WatoMode):
    @classmethod
    def name(cls):
        return "role_matrix"


    @classmethod
    def permissions(cls):
        return ["users"]


    def title(self):
        return _("Role & Permission Matrix")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "roles")]), "back")


    def page(self):
        role_list = sorted(userdb.load_roles().items(), key = lambda a: (a[1]["alias"],a[0]))

        # Loop all permission sections, but sorted plz
        for section, (prio, section_title, do_sort) in sorted(config.permission_sections.iteritems(),
                                                     key = lambda x: x[1][0], reverse = True):

            html.begin_foldable_container("perm_matrix", section, section == "general", section_title, indent = True)

            table.begin(section)

            # Loop all permissions
            permlist = config.permissions_by_order[:]
            if do_sort:
                permlist.sort(cmp = lambda a,b: cmp(a["title"], b["title"]))

            for perm in permlist:
                pname = perm["name"]
                this_section = pname.split(".")[0]
                if section != this_section:
                    continue # Skip permissions of other sections

                table.row()
                table.cell(_("Permission"), perm["title"], css="wide")
                html.help(perm["description"])
                for role_id, role in role_list:
                    base_on_id = role.get('basedon', role_id)
                    pvalue = role["permissions"].get(pname)
                    if pvalue is None:
                        if base_on_id in perm["defaults"]:
                            icon_name = "perm_yes_default"
                        else:
                            icon_name = None
                    else:
                        icon_name = "perm_%s" % (pvalue and "yes" or "no")

                    table.cell(role_id, css="center")
                    if icon_name:
                        html.icon(None, icon_name)

            table.end()
            html.end_foldable_container()

        html.close_table()

#.
#   .--Host-Tags-----------------------------------------------------------.
#   |              _   _           _     _____                             |
#   |             | | | | ___  ___| |_  |_   _|_ _  __ _ ___               |
#   |             | |_| |/ _ \/ __| __|   | |/ _` |/ _` / __|              |
#   |             |  _  | (_) \__ \ |_    | | (_| | (_| \__ \              |
#   |             |_| |_|\___/|___/\__|   |_|\__,_|\__, |___/              |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   | Manage the variable config.wato_host_tags -> The set of tags to be   |
#   | assigned to hosts and that is the basis of the rules.                |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeHostTags(WatoMode, watolib.HosttagsConfiguration):
    @classmethod
    def name(cls):
        return "hosttags"


    @classmethod
    def permissions(cls):
        return ["hosttags"]


    def __init__(self):
        super(ModeHostTags, self).__init__()
        self._hosttags, self._auxtags = self._load_hosttags()


    def title(self):
        return _("Host tag groups")


    def buttons(self):
        global_buttons()
        html.context_button(_("New Tag group"), watolib.folder_preserving_link([("mode", "edit_hosttag")]), "new")
        html.context_button(_("New Aux tag"), watolib.folder_preserving_link([("mode", "edit_auxtag")]), "new")


    def action(self):
        # Deletion of tag groups
        del_id = html.var("_delete")
        if del_id:
            operations = None
            for e in self._hosttags:
                if e[0] == del_id:
                    # In case of tag group deletion, the operations is a pair of tag_id
                    # and list of choice-ids.
                    operations = [ x[0] for x in e[2] ]


            message = rename_host_tags_after_confirmation(del_id, operations)
            if message == True: # no confirmation yet
                c = wato_confirm(_("Confirm deletion of the host "
                                   "tag group '%s'") % del_id,
                                _("Do you really want to delete the "
                                  "host tag group '%s'?") % del_id)
                if c == False:
                    return ""
                elif c == None:
                    return None

            if message:
                self._hosttags = [ e for e in self._hosttags if e[0] != del_id ]
                watolib.save_hosttags(self._hosttags, self._auxtags)
                watolib.Folder.invalidate_caches()
                watolib.Folder.root_folder().rewrite_hosts_files()
                add_change("edit-hosttags", _("Removed host tag group %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        # Deletion of auxiliary tags
        del_nr = html.var("_delaux")
        if del_nr:
            nr = int(del_nr)
            del_id = self._auxtags[nr][0]

            # Make sure that this aux tag is not begin used by any tag group
            for entry in self._hosttags:
                choices = entry[2]
                for e in choices:
                    if len(e) > 2:
                        if del_id in e[2]:
                            raise MKUserError(None, _("You cannot delete this auxiliary tag. "
                               "It is being used in the tag group <b>%s</b>.") % entry[1])

            operations = { del_id : False }
            message = rename_host_tags_after_confirmation(None, operations)
            if message == True: # no confirmation yet
                c = wato_confirm(_("Confirm deletion of the auxiliary "
                                   "tag '%s'") % del_id,
                                _("Do you really want to delete the "
                                  "auxiliary tag '%s'?") % del_id)
                if c == False:
                    return ""
                elif c == None:
                    return None

            if message:
                del self._auxtags[nr]
                # Remove auxiliary tag from all host tags
                for e in self._hosttags:
                    choices = e[2]
                    for choice in choices:
                        if len(choice) > 2:
                            if del_id in choice[2]:
                                choice[2].remove(del_id)

                watolib.save_hosttags(self._hosttags, self._auxtags)
                watolib.Folder.invalidate_caches()
                watolib.Folder.root_folder().rewrite_hosts_files()
                add_change("edit-hosttags", _("Removed auxiliary tag %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        move_nr = html.var("_move")
        if move_nr != None:
            if html.check_transaction():
                move_nr = int(move_nr)
                if move_nr >= 0:
                    dir = 1
                else:
                    move_nr = -move_nr
                    dir = -1
                moved = self._hosttags[move_nr]
                del self._hosttags[move_nr]
                self._hosttags[move_nr+dir:move_nr+dir] = [moved]
                watolib.save_hosttags(self._hosttags, self._auxtags)
                config.wato_host_tags = self._hosttags
                watolib.add_change("edit-hosttags", _("Changed order of host tag groups"))


    def page(self):
        if not self._hosttags + self._auxtags:
            MainMenu([
                MenuItem("edit_hosttag", _("Create new tag group"), "new", "hosttags",
                    _("Each host tag group will create one dropdown choice in the host configuration.")),
                MenuItem("edit_auxtag", _("Create new auxiliary tag"), "new", "hosttags",
                    _("You can have these tags automatically added if certain primary tags are set.")),
                ]).show()

        else:
            self._render_host_tag_list()
            self._render_aux_tag_list()


    def _render_host_tag_list(self):
        table.begin("hosttags", _("Host tag groups"),
                    help = (_("Host tags are the basis of Check_MK's rule based configuration. "
                             "If the first step you define arbitrary tag groups. A host "
                             "has assigned exactly one tag out of each group. These tags can "
                             "later be used for defining parameters for hosts and services, "
                             "such as <i>disable notifications for all hosts with the tags "
                             "<b>Network device</b> and <b>Test</b></i>.")),
                    empty_text = _("You haven't defined any tag groups yet."),
                    searchable = False, sortable = False)

        effective_tag_groups = self._get_effective_tag_groups()

        if not effective_tag_groups:
            table.end()
            return

        for nr, entry in enumerate(effective_tag_groups):
            tag_id, title, choices = entry[:3] # fourth: tag dependency information
            topic, title = map(_u, watolib.parse_hosttag_title(title))
            table.row()
            table.cell(_("Actions"), css="buttons")
            if watolib.is_builtin_host_tag_group(tag_id):
                html.i("(%s)" % _("builtin"))
            else:
                edit_url     = watolib.folder_preserving_link([("mode", "edit_hosttag"), ("edit", tag_id)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delete", tag_id)])
                if nr == 0:
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(-nr))]),
                                _("Move this tag group one position up"), "up")

                if nr == len(effective_tag_groups) - 1 \
                   or watolib.is_builtin_host_tag_group(effective_tag_groups[nr+1][0]):
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(nr))]),
                                _("Move this tag group one position down"), "down")

                html.icon_button(edit_url,   _("Edit this tag group"), "edit")
                html.icon_button(delete_url, _("Delete this tag group"), "delete")

            table.text_cell(_("ID"), tag_id)
            table.text_cell(_("Title"), title)
            table.text_cell(_("Topic"), topic or '')
            table.text_cell(_("Type"), (len(choices) == 1 and _("Checkbox") or _("Dropdown")))
            table.text_cell(_("Choices"), str(len(choices)))
            table.cell(_("Demonstration"), sortable=False)
            html.begin_form("tag_%s" % tag_id)
            watolib.host_attribute("tag_%s" % tag_id).render_input("", None)
            html.end_form()
        table.end()


    def _render_aux_tag_list(self):
        table.begin("auxtags", _("Auxiliary tags"),
                    help = _("Auxiliary tags can be attached to other tags. That way "
                             "you can for example have all hosts with the tag <tt>cmk-agent</tt> "
                             "get also the tag <tt>tcp</tt>. This makes the configuration of "
                             "your hosts easier."),
                    empty_text = _("You haven't defined any auxiliary tags."),
                    searchable = False)

        aux_tags = config.BuiltinTags().get_effective_aux_tags(self._auxtags)
        effective_tag_groups = self._get_effective_tag_groups()

        if not aux_tags:
            table.end()
            return

        for nr, (tag_id, title) in enumerate(aux_tags):
            table.row()
            topic, title = watolib.parse_hosttag_title(title)
            table.cell(_("Actions"), css="buttons")
            if watolib.is_builtin_aux_tag(tag_id):
                html.i("(%s)" % _("builtin"))
            else:
                edit_url     = watolib.folder_preserving_link([("mode", "edit_auxtag"), ("edit", nr)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delaux", nr)])
                html.icon_button(edit_url, _("Edit this auxiliary tag"), "edit")
                html.icon_button(delete_url, _("Delete this auxiliary tag"), "delete")
            table.text_cell(_("ID"), tag_id)

            table.text_cell(_("Title"), _u(title))
            table.text_cell(_("Topic"), _u(topic) or '')
            table.text_cell(_("Tags using this auxiliary tag"),
                            ", ".join(self._get_tags_using_aux_tag(effective_tag_groups, tag_id)))
        table.end()


    def _get_effective_tag_groups(self):
        return config.BuiltinTags().get_effective_tag_groups(self._hosttags)


    def _get_tags_using_aux_tag(self, tag_groups, aux_tag):
        used_tags = set()
        for tag_def in tag_groups:
            for entry in tag_def[2]:
                if aux_tag in entry[-1]:
                    used_tags.add(tag_def[1].split("/")[-1])
        return sorted(used_tags)



class ModeEditHosttagConfiguration(WatoMode):
    def __init__(self):
        super(ModeEditHosttagConfiguration, self).__init__()
        self._untainted_hosttags_config = watolib.HosttagsConfiguration()
        self._untainted_hosttags_config.load()


    def _get_topic_valuespec(self):
        return OptionalDropdownChoice(
            title = _("Topic"),
            choices = self._untainted_hosttags_config.get_hosttag_topics(),
            explicit = TextUnicode(),
            otherlabel = _("Create New Topic"),
            default_value = None,
            sorted = True
        )



@mode_registry.register
class ModeEditAuxtag(ModeEditHosttagConfiguration):
    @classmethod
    def name(cls):
        return "edit_auxtag"


    @classmethod
    def permissions(cls):
        return ["hosttags"]


    def title(self):
        if self._is_new_aux_tag():
            return _("Create new auxiliary tag")
        else:
            return _("Edit auxiliary tag")


    def _is_new_aux_tag(self):
        return html.var("edit") == None


    def buttons(self):
        html.context_button(_("All Hosttags"), watolib.folder_preserving_link([("mode", "hosttags")]), "back")


    def action(self):
        if not html.transaction_valid():
            return "hosttags"

        html.check_transaction() # use up transaction id

        if self._is_new_aux_tag():
            changed_aux_tag = watolib.AuxTag()
            changed_aux_tag.id = self._get_tag_id()
        else:
            tag_nr = self._get_tag_number()
            changed_aux_tag = self._untainted_hosttags_config.aux_tag_list.get_number(tag_nr)

        changed_aux_tag.title = html.get_unicode_input("title").strip()

        topic = forms.get_input(self._get_topic_valuespec(), "topic")
        if topic != '':
            changed_aux_tag.topic = topic

        changed_aux_tag.validate()

        # Make sure that this ID is not used elsewhere
        for tag_group in self._untainted_hosttags_config.tag_groups:
            if changed_aux_tag.id in tag_group.get_tag_ids():
                raise MKUserError("tag_id",
                _("This tag id is already being used in the host tag group %s") % tag_group.title)


        changed_hosttags_config = watolib.HosttagsConfiguration()
        changed_hosttags_config.load()
        if self._is_new_aux_tag():
            changed_hosttags_config.aux_tag_list.append(changed_aux_tag)
        else:
            changed_hosttags_config.aux_tag_list.update(self._get_tag_number(), changed_aux_tag)

        changed_hosttags_config.save()

        return "hosttags"


    def _get_tag_number(self):
        return int(html.var("edit"))


    def _get_tag_id(self):
        return html.var("tag_id")


    def page(self):
        if self._is_new_aux_tag():
            changed_aux_tag = watolib.AuxTag()
        else:
            tag_nr = self._get_tag_number()
            changed_aux_tag = self._untainted_hosttags_config.aux_tag_list.get_number(tag_nr)

        html.begin_form("auxtag")
        forms.header(_("Auxiliary Tag"))

        # Tag ID
        forms.section(_("Tag ID"))
        if self._is_new_aux_tag():
            html.text_input("tag_id", "")
            html.set_focus("tag_id")
        else:
            html.write_text(self._get_tag_id())
        html.help(_("The internal name of the tag. The special tags "
                    "<tt>snmp</tt>, <tt>tcp</tt> and <tt>ping</tt> can "
                    "be used here in order to specify the agent type."))

        # Title
        forms.section(_("Title") + "<sup>*</sup>")
        html.text_input("title", changed_aux_tag.title, size = 30)
        html.help(_("An alias or description of this auxiliary tag"))

        # The (optional) topic
        forms.section(_("Topic") + "<sup>*</sup>")
        html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                    "selections in the GUI more comfortable."))
        forms.input(self._get_topic_valuespec(), "topic", changed_aux_tag.topic)

        # Button and end
        forms.end()
        html.show_localization_hint()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()



@mode_registry.register
class ModeEditHosttagGroup(ModeEditHosttagConfiguration):
    @classmethod
    def name(cls):
        return "edit_hosttag"


    @classmethod
    def permissions(cls):
        return ["hosttags"]


    def __init__(self):
        super(ModeEditHosttagGroup, self).__init__()
        self._untainted_tag_group = self._untainted_hosttags_config.get_tag_group(self._get_taggroup_id())
        if not self._untainted_tag_group:
            self._untainted_tag_group = watolib.HosttagGroup()


    def title(self):
        if self._is_new_hosttag_group():
            return _("Create new tag group")
        else:
            return _("Edit tag group")


    def _is_new_hosttag_group(self):
        return html.var("edit") == None


    def buttons(self):
        html.context_button(_("All Hosttags"), watolib.folder_preserving_link([("mode", "hosttags")]), "back")


    def action(self):
        if not html.transaction_valid():
            return "hosttags"

        if self._is_new_hosttag_group():
            html.check_transaction() # use up transaction id

        changed_tag_group = watolib.HosttagGroup()
        changed_tag_group.id = self._get_taggroup_id()

        # Create new object with existing host tags
        changed_hosttags_config = watolib.HosttagsConfiguration()
        changed_hosttags_config.load()

        changed_tag_group.title = html.get_unicode_input("title").strip()
        changed_tag_group.topic = forms.get_input(self._get_topic_valuespec(), "topic")


        for tag_entry in forms.get_input(self._get_taggroups_valuespec(), "choices"):
            changed_tag_group.tags.append(watolib.GroupedHosttag(tag_entry))


        if self._is_new_hosttag_group():
            # Inserts and verifies changed tag group
            changed_hosttags_config.insert_tag_group(changed_tag_group)
            changed_hosttags_config.save()

            # Make sure, that all tags are active (also manual ones from main.mk)
            config.load_config()
            watolib.update_config_based_host_attributes()
            add_change("edit-hosttags", _("Created new host tag group '%s'") % changed_tag_group.id)
            return "hosttags", _("Created new host tag group '%s'") % changed_tag_group.title
        else:
            # Updates and verifies changed tag group
            changed_hosttags_config.update_tag_group(changed_tag_group)

            # This is the major effort of WATO when it comes to
            # host tags: renaming and deleting of tags that might be
            # in use by folders, hosts and rules. First we create a
            # kind of "patch" from the old to the new tags. The renaming
            # of a tag is detected by comparing the titles. Addition
            # of new tags is not a problem and need not be handled.
            # Result of this is the dict 'operations': it's keys are
            # current tag names, its values the corresponding new names
            # or False in case of tag removals.
            operations = {}

            # Detect renaming
            new_by_title = dict([(tag.title, tag.id)
                                 for tag in changed_tag_group.tags])

            for former_tag in self._untainted_tag_group.tags:
                if former_tag.title in new_by_title:
                    new_id = new_by_title[former_tag.title]
                    if new_id != former_tag.id:
                        operations[former_tag.id] = new_id # might be None

            # Detect removal
            for former_tag in self._untainted_tag_group.tags:
                if former_tag.id != None \
                    and former_tag.id not in [ tmp_tag.id for tmp_tag in changed_tag_group.tags ] \
                    and former_tag.id not in operations:
                    # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
                    operations[former_tag.id] = False


            # Now check, if any folders, hosts or rules are affected
            message = rename_host_tags_after_confirmation(changed_tag_group.id, operations)
            if message:
                changed_hosttags_config.save()
                config.load_config()
                watolib.update_config_based_host_attributes()
                add_change("edit-hosttags", _("Edited host tag group %s (%s)") % (message, self._get_taggroup_id()))
                return "hosttags", message != True and message or None

        return "hosttags"


    def page(self):
        html.begin_form("hosttaggroup", method = 'POST')
        forms.header(_("Edit group") + (self._untainted_tag_group.title and " %s" % self._untainted_tag_group.title or ""))

        # Tag ID
        forms.section(_("Internal ID"))
        html.help(_("The internal ID of the tag group is used to store the tag's "
                    "value in the host properties. It cannot be changed later."))
        if self._is_new_hosttag_group():
            html.text_input("tag_id")
            html.set_focus("tag_id")
        else:
            html.write_text(self._untainted_tag_group.id)

        # Title
        forms.section(_("Title") + "<sup>*</sup>")
        html.help(_("An alias or description of this tag group"))
        html.text_input("title", self._untainted_tag_group.title, size = 30)

        # The (optional) topic
        forms.section(_("Topic") + "<sup>*</sup>")
        html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                    "selections in the GUI more comfortable."))
        forms.input(self._get_topic_valuespec(), "topic", self._untainted_tag_group.topic)

        # Choices
        forms.section(_("Choices"))
        html.help(_("The first choice of a tag group will be its default value. "
                     "If a tag group has only one choice, it will be displayed "
                     "as a checkbox and set or not set the only tag. If it has "
                     "more choices you may leave at most one tag id empty. A host "
                     "with that choice will not get any tag of this group.<br><br>"
                     "The tag ID must contain only of letters, digits and "
                     "underscores.<br><br><b>Renaming tags ID:</b> if you want "
                     "to rename the ID of a tag, then please make sure that you do not "
                     "change its title at the same time! Otherwise WATO will not "
                     "be able to detect the renaming and cannot exchange the tags "
                     "in all folders, hosts and rules accordingly."))
        forms.input(self._get_taggroups_valuespec(), "choices", self._untainted_tag_group.get_tags_legacy_format())

        # Button and end
        forms.end()
        html.show_localization_hint()

        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


    def _get_taggroup_id(self):
        return html.var("edit", html.var("tag_id"))


    def _get_taggroups_valuespec(self):
        aux_tags = config.BuiltinTags().get_effective_aux_tags(self._untainted_hosttags_config.get_legacy_format()[1])

        return ListOf(
            Tuple(
                elements = [
                    TextAscii(
                        title = _("Tag ID"),
                        size = 16,
                        regex="^[-a-z0-9A-Z_]*$",
                        none_is_empty = True,
                        regex_error = _("Invalid tag ID. Only the characters a-z, A-Z, "
                                      "0-9, _ and - are allowed.")),
                    TextUnicode(
                        title = _("Description") + "*",
                        allow_empty = False,
                        size = 40),

                    Foldable(
                        ListChoice(
                            title = _("Auxiliary tags"),
                            # help = _("These tags will implicitely added to a host if the "
                            #          "user selects this entry in the tag group. Select multiple "
                            #          "entries with the <b>Ctrl</b> key."),
                            choices = aux_tags)),

                ],
                show_titles = True,
                orientation = "horizontal"),

            add_label = _("Add tag choice"),
            row_label = "@. Choice",
            sort_by = 1, # sort by description
        )




# Handle renaming and deletion of host tags: find affected
# hosts, folders and rules. Remove or fix those rules according
# the the users' wishes. In case auf auxiliary tags the tag_id
# is None. In other cases it is the id of the tag group currently
# being edited.
def rename_host_tags_after_confirmation(tag_id, operations):
    mode = html.var("_repair")
    if mode == "abort":
        raise MKUserError("id_0", _("Aborting change."))

    elif mode:
        if tag_id and type(operations) == list: # make attribute unknown to system, important for save() operations
            watolib.undeclare_host_tag_attribute(tag_id)
        affected_folders, affected_hosts, affected_rulesets = \
        change_host_tags_in_folders(tag_id, operations, mode, watolib.Folder.root_folder())
        return _("Modified folders: %d, modified hosts: %d, modified rulesets: %d") % \
            (len(affected_folders), len(affected_hosts), len(affected_rulesets))

    message = ""
    affected_folders, affected_hosts, affected_rulesets = \
        change_host_tags_in_folders(tag_id, operations, "check", watolib.Folder.root_folder())

    if affected_folders:
        message += _("Affected folders with an explicit reference to this tag "
                     "group and that are affected by the change") + ":<ul>"
        for folder in affected_folders:
            message += '<li><a href="%s">%s</a></li>' % (folder.edit_url(), folder.alias_path())
        message += "</ul>"

    if affected_hosts:
        message += _("Hosts where this tag group is explicitely set "
                     "and that are effected by the change") + ":<ul><li>"
        for nr, host in enumerate(affected_hosts):
            if nr > 20:
                message += "... (%d more)" % (len(affected_hosts) - 20)
                break
            elif nr > 0:
                message += ", "

            message += '<a href="%s">%s</a>' % (host.edit_url(), host.name())
        message += "</li></ul>"

    if affected_rulesets:
        message += _("Rulesets that contain rules with references to the changed tags") + ":<ul>"
        for ruleset in affected_rulesets:
            message += '<li><a href="%s">%s</a></li>' % (
                watolib.folder_preserving_link([("mode", "edit_ruleset"), ("varname", ruleset.name)]),
                ruleset.title())
        message += "</ul>"

    if not message and type(operations) == tuple: # deletion of unused tag group
        html.open_div(class_="really")
        html.begin_form("confirm")
        html.write_text(_("Please confirm the deletion of the tag group."))
        html.button("_abort", _("Abort"))
        html.button("_do_confirm", _("Proceed"))
        html.hidden_fields(add_action_vars = True)
        html.end_form()
        html.close_div()

    elif message:
        if type(operations) == list:
            wato_html_head(_("Confirm tag deletion"))
        else:
            wato_html_head(_("Confirm tag modifications"))
        html.open_div(class_="really")
        html.h3(_("Your modifications affect some objects"))
        html.write_text(message)
        html.br()
        html.write_text(_("WATO can repair things for you. It can rename tags in folders, host and rules. "
                          "Removed tag groups will be removed from hosts and folders, removed tags will be "
                          "replaced with the default value for the tag group (for hosts and folders). What "
                          "rules concern, you have to decide how to proceed."))
        html.begin_form("confirm")

        # Check if operations contains removal
        if type(operations) == list:
            have_removal = True
        else:
            have_removal = False
            for new_val in operations.values():
                if not new_val:
                    have_removal = True
                    break

        if affected_rulesets and have_removal:
            html.br()
            html.b(_("Some tags that are used in rules have been removed by you. What "
                     "shall we do with that rules?"))
            html.open_ul()
            html.radiobutton("_repair", "remove", True, _("Just remove the affected tags from the rules."))
            html.br()
            html.radiobutton("_repair", "delete", False, _("Delete rules containing tags that have been removed, if tag is used in a positive sense. Just remove that tag if it's used negated."))
        else:
            html.open_ul()
            html.radiobutton("_repair", "repair", True, _("Fix affected folders, hosts and rules."))

        html.br()
        html.radiobutton("_repair", "abort", False, _("Abort your modifications."))
        html.close_ul()

        html.button("_do_confirm", _("Proceed"), "")
        html.hidden_fields(add_action_vars = True)
        html.end_form()
        html.close_div()
        return False

    return True

# operation == None -> tag group is deleted completely
# tag_id == None -> Auxiliary tag has been deleted, no
# tag group affected
def change_host_tags_in_folders(tag_id, operations, mode, folder):
    need_save = False
    affected_folders = []
    affected_hosts = []
    affected_rulesets = []
    if tag_id:
        attrname = "tag_" + tag_id
        attributes = folder.attributes()
        if attrname in attributes: # this folder has set the tag group in question
            if type(operations) == list: # deletion of tag group
                if attrname in attributes:
                    affected_folders.append(folder)
                    if mode != "check":
                        del attributes[attrname]
                        need_save = True
            else:
                current = attributes[attrname]
                if current in operations:
                    affected_folders.append(folder)
                    if mode != "check":
                        new_tag = operations[current]
                        if new_tag == False: # tag choice has been removed -> fall back to default
                            del attributes[attrname]
                        else:
                            attributes[attrname] = new_tag
                        need_save = True
        if need_save:
            try:
                folder.save()
            except MKAuthException, e:
                # Ignore MKAuthExceptions of locked host.mk files
                pass

        for subfolder in folder.all_subfolders().values():
            aff_folders, aff_hosts, aff_rulespecs = change_host_tags_in_folders(tag_id, operations, mode, subfolder)
            affected_folders += aff_folders
            affected_hosts += aff_hosts
            affected_rulesets += aff_rulespecs

        affected_hosts += change_host_tags_in_hosts(folder, tag_id, operations, mode, folder.hosts())

    affected_rulesets += change_host_tags_in_rules(folder, operations, mode)
    return affected_folders, affected_hosts, affected_rulesets


def change_host_tags_in_hosts(folder, tag_id, operations, mode, hostlist):
    need_save = False
    affected_hosts = []
    for hostname, host in hostlist.items():
        attributes = host.attributes()
        attrname = "tag_" + tag_id
        if attrname in attributes:
            if type(operations) == list: # delete complete tag group
                affected_hosts.append(host)
                if mode != "check":
                    del attributes[attrname]
                    need_save = True
            else:
                if attributes[attrname] in operations:
                    affected_hosts.append(host)
                    if mode != "check":
                        new_tag = operations[attributes[attrname]]
                        if new_tag == False: # tag choice has been removed -> fall back to default
                            del attributes[attrname]
                        else:
                            attributes[attrname] = new_tag
                        need_save = True
    if need_save:
        try:
            folder.save_hosts()
        except MKAuthException, e:
            # Ignore MKAuthExceptions of locked host.mk files
            pass
    return affected_hosts


# The function parses all rules in all rulesets and looks
# for host tags that have been removed or renamed. If tags
# are removed then the depending on the mode affected rules
# are either deleted ("delete") or the vanished tags are
# removed from the rule ("remove").
def change_host_tags_in_rules(folder, operations, mode):
    need_save = False
    affected_rulesets = set([])

    rulesets = watolib.FolderRulesets(folder)
    rulesets.load()

    for varname, ruleset in rulesets.get_rulesets().items():
        rules_to_delete = set([])
        for _folder, _rulenr, rule in ruleset.get_rules():
            # Handle deletion of complete tag group
            if type(operations) == list: # this list of tags to remove
                for tag in operations:
                    if tag != None and (tag in rule.tag_specs or "!"+tag in rule.tag_specs):
                        affected_rulesets.add(ruleset)

                        if mode != "check":
                            need_save = True
                            if tag in rule.tag_specs and mode == "delete":
                                ruleset.delete_rule(rule)
                            elif tag in rule.tag_specs:
                                rule.tag_specs.remove(tag)
                            elif "+"+tag in rule.tag_specs:
                                rule.tag_specs.remove("!"+tag)

            # Removal or renamal of single tag choices
            else:
                for old_tag, new_tag in operations.items():
                    # The case that old_tag is None (an empty tag has got a name)
                    # cannot be handled when it comes to rules. Rules do not support
                    # such None-values.
                    if not old_tag:
                        continue

                    if old_tag in rule.tag_specs or ("!" + old_tag) in rule.tag_specs:
                        affected_rulesets.add(ruleset)

                        if mode != "check":
                            need_save = True
                            if old_tag in rule.tag_specs:
                                rule.tag_specs.remove(old_tag)
                                if new_tag:
                                    rule.tag_specs.append(new_tag)
                                elif mode == "delete":
                                    ruleset.delete_rule(rule)

                            # negated tag has been renamed or removed
                            if "!"+old_tag in rule.tag_specs:
                                rule.tag_specs.remove("!"+old_tag)
                                if new_tag:
                                    rule.tag_specs.append("!"+new_tag)
                                # the case "delete" need not be handled here. Negated
                                # tags can always be removed without changing the rule's
                                # behaviour.

    if need_save:
        rulesets.save()

    return sorted(affected_rulesets, key=lambda x: x.title())


#.
#   .--Rule-Editor---------------------------------------------------------.
#   |           ____        _        _____    _ _ _                        |
#   |          |  _ \ _   _| | ___  | ____|__| (_) |_ ___  _ __            |
#   |          | |_) | | | | |/ _ \ |  _| / _` | | __/ _ \| '__|           |
#   |          |  _ <| |_| | |  __/ | |__| (_| | | || (_) | |              |
#   |          |_| \_\\__,_|_|\___| |_____\__,_|_|\__\___/|_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | WATO's awesome rule editor: Lets the user edit rule based parameters |
#   | from main.mk.                                                        |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeRuleEditor(WatoMode):
    @classmethod
    def name(cls):
        return "ruleeditor"


    @classmethod
    def permissions(cls):
        return ["rulesets"]


    def __init__(self):
        super(ModeRuleEditor, self).__init__()
        self._only_host = html.var("host")


    def title(self):
        if self._only_host:
            return _("Rules effective on host ") + self._only_host
        else:
            return _("Rule-Based Configuration of Host & Service Parameters")


    def buttons(self):
        global_buttons()

        if self._only_host:
            html.context_button(self._only_host,
                watolib.folder_preserving_link([("mode", "edit_host"), ("host", self._only_host)]), "host")

        html.context_button(_("Used Rulesets"), watolib.folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_ruleset_used", DropdownChoice.option_id(True)),
            ("search_p_ruleset_used_USE", "on"),
        ]), "usedrulesets")

        html.context_button(_("Ineffective rules"), watolib.folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_rule_ineffective", DropdownChoice.option_id(True)),
            ("search_p_rule_ineffective_USE", "on")]
        ), "rulesets_ineffective")

        html.context_button(_("Deprecated Rulesets"), watolib.folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_ruleset_deprecated", DropdownChoice.option_id(True)),
            ("search_p_ruleset_deprecated_USE", "on")
        ]), "rulesets_deprecated")

        rule_search_button()


    def page(self):
        if self._only_host:
            html.h3("%s: %s" % (_("Host"), self._only_host))

        search_form(mode="rulesets")

        menu = MainMenu()
        for groupname in watolib.g_rulespecs.get_main_groups():
            url_vars = [
                ("mode", "rulesets"),
                ("group", groupname),
            ]
            if self._only_host:
                url_vars.append(("host", self._only_host))
            url = watolib.folder_preserving_link(url_vars)
            if groupname == "static": # these have moved into their own WATO module
                continue

            rulegroup = watolib.get_rulegroup(groupname)
            icon = "rulesets"

            if rulegroup.help:
                help_text = rulegroup.help.split('\n')[0] # Take only first line as button text
            else:
                help_text = None

            menu.add_item(MenuItem(
                mode_or_url=url,
                title=rulegroup.title,
                icon=icon,
                permission="rulesets",
                description=help_text
            ))
        menu.show()


class RulesetMode(WatoMode):
    def __init__(self):
        super(RulesetMode, self).__init__()

        self._title = None
        self._help = None

        self._set_title_and_help()


    @abc.abstractmethod
    def _set_title_and_help(self):
        raise NotImplementedError()


    def _from_vars(self):
        self._group_name = html.var("group")

        #  Explicitly hide deprecated rulesets by default
        if not html.has_var("search_p_ruleset_deprecated"):
            html.set_var("search_p_ruleset_deprecated", DropdownChoice.option_id(False))
            html.set_var("search_p_ruleset_deprecated_USE", "on")

        # Transform group argument to the "rule search arguments"
        # Keeping this for compatibility reasons for the moment
        if self._group_name:
            html.set_var("search_p_ruleset_group",
                           DropdownChoice.option_id(self._group_name))
            html.set_var("search_p_ruleset_group_USE", "on")
            html.del_var("group")

        # Transform the search argument to the "rule search" arguments
        if html.has_var("search"):
            html.set_var("search_p_fulltext", html.get_unicode_input("search"))
            html.set_var("search_p_fulltext_USE", "on")
            html.del_var("search")

        # Transform the folder argumen (from URL or bradcrumb) to the "rule search arguments
        if html.var("folder"):
            html.set_var("search_p_rule_folder_0", DropdownChoice.option_id(html.var("folder")))
            html.set_var("search_p_rule_folder_1", DropdownChoice.option_id(True))
            html.set_var("search_p_rule_folder_USE", "on")

        self._search_options = ModeRuleSearch().search_options

        self._only_host = html.var("host")


    @abc.abstractmethod
    def _rulesets(self):
        raise NotImplementedError()


    def title(self):
        if self._only_host:
            return _("%s - %s") % (self._only_host, self._title)
        else:
            return self._title


    def buttons(self):
        global_buttons()

        if self._only_host:
            self._only_host_buttons()
        else:
            self._regular_buttons()

        rule_search_button(self._search_options, mode=self.name())


    def _only_host_buttons(self):
        html.context_button(_("All Rulesets"), watolib.folder_preserving_link([("mode", "ruleeditor"), ("host", self._only_host)]), "back")
        html.context_button(self._only_host,
             watolib.folder_preserving_link([("mode", "edit_host"), ("host", self._only_host)]), "host")


    def _regular_buttons(self):
        if self.name() != "static_checks":
            html.context_button(_("All Rulesets"), watolib.folder_preserving_link([("mode", "ruleeditor")]), "back")

        if config.user.may("wato.hosts") or config.user.may("wato.seeall"):
            html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]), "folder")

        if self._group_name == "agents":
            html.context_button(_("Agent Bakery"), watolib.folder_preserving_link([("mode", "agents")]), "agents")


    def page(self):
        if not self._only_host:
            watolib.Folder.current().show_breadcrump(keepvarnames=True)

        search_form(default_value=self._search_options.get("fulltext", ""))

        if self._help:
            html.help(self._help)

        rulesets = self._rulesets()
        rulesets.load()

        # In case the user has filled in the search form, filter the rulesets by the given query
        if self._search_options:
            rulesets = watolib.SearchedRulesets(rulesets, self._search_options)

        html.open_div(class_="rulesets")

        grouped_rulesets = sorted(rulesets.get_grouped(), key=lambda (k, v): watolib.get_rulegroup(k).title)

        for main_group_name, sub_groups in grouped_rulesets:
            # Display the main group header only when there are several main groups shown
            if len(grouped_rulesets) > 1:
                html.h3(watolib.get_rulegroup(main_group_name).title)
                html.br()

            for sub_group_title, group_rulesets in sub_groups:
                forms.header(sub_group_title or watolib.get_rulegroup(main_group_name).title)
                forms.container()

                for ruleset in group_rulesets:
                    float_cls = None
                    if not config.wato_hide_help_in_lists:
                        float_cls = "nofloat" if html.help_visible else "float"
                    html.open_div(class_=["ruleset", float_cls], title=html.strip_tags(ruleset.help() or ''))
                    html.open_div(class_="text")

                    url_vars = [
                        ("mode", "edit_ruleset"),
                        ("varname", ruleset.name),
                        ("back_mode", self.name()),
                    ]
                    if self._only_host:
                        url_vars.append(("host", self._only_host))
                    view_url = html.makeuri(url_vars)

                    html.a(ruleset.title(), href=view_url, class_="nonzero" if ruleset.is_empty() else "zero")
                    html.span("." * 100, class_="dots")
                    html.close_div()

                    num_rules = ruleset.num_rules()
                    if ruleset.search_matching_rules:
                        num_rules = "%d/%d" % (len(ruleset.search_matching_rules), num_rules)

                    html.div(num_rules, class_=["rulecount", "nonzero" if ruleset.is_empty() else "zero"])
                    if not config.wato_hide_help_in_lists and ruleset.help():
                        html.help(ruleset.help())

                    html.close_div()
                forms.end()

        if not grouped_rulesets:
            if self._only_host:
                msg = _("There are no rules with an exception for the host <b>%s</b>.") % self._only_host
            elif self._search_options:
                msg = _("There are no rulesets or rules matching your search.")
            else:
                msg = _("There are no rules defined in this folder.")

            html.div(msg, class_="info")

        html.close_div()



@mode_registry.register
class ModeRulesets(RulesetMode):
    @classmethod
    def name(cls):
        return "rulesets"


    @classmethod
    def permissions(cls):
        return ["rulesets"]


    def _rulesets(self):
        return watolib.NonStaticChecksRulesets()


    def _set_title_and_help(self):
        if self._search_options.keys() == ["ruleset_deprecated"]:
            self._title = _("Deprecated Rulesets")
            self._help = _("Here you can see a list of all deprecated rulesets (which are not used by Check_MK anymore). If "
                     "you have defined some rules here, you might have to migrate the rules to their successors. Please "
                     "refer to the release notes or context help of the rulesets for details.")

        elif self._search_options.keys() == ["rule_ineffective"]:
            self._title = _("Rulesets with ineffective rules")
            self._help = _("The following rulesets contain rules that do not match to any of the existing hosts.")

        elif self._search_options.keys() == ["ruleset_used"]:
            self._title = _("Used rulesets")
            self._help = _("Non-empty rulesets")

        elif self._group_name == None:
            self._title = _("Rulesets")
            self._help = None

        else:
            rulegroup = watolib.get_rulegroup(self._group_name)
            self._title, self._help = rulegroup.title, rulegroup.help




@mode_registry.register
class ModeStaticChecksRulesets(RulesetMode):
    @classmethod
    def name(cls):
        return "static_checks"


    @classmethod
    def permissions(cls):
        return ["rulesets"]


    def _rulesets(self):
        return watolib.StaticChecksRulesets()


    def _set_title_and_help(self):
        self._title = _("Manual Checks")
        self._help = _("Here you can create explicit checks that are not being created by the "
                       "automatic service discovery.")



def rule_search_button(search_options=None, mode="rulesets"):
    is_searching = bool(search_options)
    # Don't highlight the button on "standard page" searches. Meaning the page calls
    # that are no searches from the users point of view because he did not fill the
    # search form, but clicked a link in the GUI
    if is_searching:
        search_keys = sorted(search_options.keys())
        if search_keys == ["ruleset_deprecated", "ruleset_group"] \
           or search_keys == ["ruleset_deprecated"] \
           or search_keys == ["rule_ineffective"] \
           or search_keys == ["ruleset_used"]:
            is_searching = False

    if is_searching:
        title = _("Refine search")
    else:
        title = _("Search")

    html.context_button(title, html.makeuri([
        ("mode", "rule_search"),
        ("back_mode", mode),
    ],
    delvars=["filled_in"]), "search", hot=is_searching)


@mode_registry.register
class ModeEditRuleset(WatoMode):
    @classmethod
    def name(cls):
        return "edit_ruleset"


    @classmethod
    def permissions(cls):
        return []


    def _from_vars(self):
        self._name = html.var("varname")
        self._back_mode = html.var("back_mode", html.var("ruleset_back_mode", "rulesets"))

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        self._item = None

        # TODO: Clean this up. In which case is it used?
        if html.var("check_command"):
            check_command = html.var("check_command")
            checks = watolib.check_mk_local_automation("get-check-information")
            if check_command.startswith("check_mk-"):
                check_command = check_command[9:]
                self._name = "checkgroup_parameters:" + checks[check_command].get("group","")
                descr_pattern  = checks[check_command]["service_description"].replace("%s", "(.*)")
                matcher = re.search(descr_pattern, html.var("service_description"))
                if matcher:
                    try:
                        self._item = matcher.group(1)
                    except:
                        pass
            elif check_command.startswith("check_mk_active-"):
                check_command = check_command[16:].split(" ")[0][:-1]
                self._name = "active_checks:" + check_command

        try:
            self._rulespec = watolib.g_rulespecs.get(self._name)
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        if not self._item:
            self._item = NO_ITEM
            if html.has_var("item"):
                try:
                    self._item = watolib.mk_eval(html.var("item"))
                except:
                    pass

        hostname = html.var("host")
        if hostname and watolib.Folder.current().has_host(hostname):
            self._hostname = hostname
        else:
            self._hostname = None

        self._just_edited_rule_from_vars()


    # After actions like editing or moving a rule there is a rule that the user has been
    # working before. Focus this rule row again to make multiple actions with a single
    # rule easier to handle
    def _just_edited_rule_from_vars(self):
        if not html.has_var("rule_folder") or not html.has_var("rulenr"):
            self._just_edited_rule = None
            return

        rule_folder = watolib.Folder.folder(html.var("rule_folder"))
        rulesets = watolib.FolderRulesets(rule_folder)
        rulesets.load()
        ruleset = rulesets.get(self._name)

        try:
            rulenr = int(html.var("rulenr")) # rule number relative to folder
            self._just_edited_rule = ruleset.get_rule(rule_folder, rulenr)
        except (IndexError, TypeError, ValueError, KeyError):
            self._just_edited_rule = None


    def title(self):
        title = self._rulespec.title

        if self._hostname:
            title += _(" for host %s") % self._hostname
            if html.has_var("item") and self._rulespec.item_type:
                title += _(" and %s '%s'") % (self._rulespec.item_name, self._item)

        return title


    def buttons(self):
        global_buttons()

        if config.user.may('wato.rulesets'):
            if self._back_mode == "rulesets":
                group_arg = [("group", self._rulespec.main_group_name)]
            else:
                group_arg = []

            html.context_button(_("Back"), watolib.folder_preserving_link([
                ("mode", self._back_mode),
                ("host", self._hostname)
            ] + group_arg), "back")

        if self._hostname:
            html.context_button(_("Services"),
                 watolib.folder_preserving_link([("mode", "inventory"),
                                         ("host", self._hostname)]), "services")

            if config.user.may('wato.rulesets'):
                html.context_button(_("Parameters"),
                      watolib.folder_preserving_link([("mode", "object_parameters"),
                                              ("host", self._hostname),
                                              ("service", self._item)]), "rulesets")

        if watolib.has_agent_bakery():
            import cmk.gui.cee.plugins.wato.agent_bakery
            cmk.gui.cee.plugins.wato.agent_bakery.agent_bakery_context_button(self._name)


    def action(self):
        rule_folder = watolib.Folder.folder(html.var("_folder", html.var("folder")))
        rule_folder.need_permission("write")
        rulesets = watolib.FolderRulesets(rule_folder)
        rulesets.load()
        ruleset = rulesets.get(self._name)

        try:
            rulenr = int(html.var("_rulenr")) # rule number relativ to folder
            rule = ruleset.get_rule(rule_folder, rulenr)
        except (IndexError, TypeError, ValueError, KeyError):
            raise MKUserError("rulenr", _("You are trying to edit a rule which does not exist "
                                              "anymore."))

        action = html.var("_action")

        if action == "delete":
            c = wato_confirm(_("Confirm"), _("Delete rule number %d of folder '%s'?")
                % (rulenr + 1, rule_folder.alias_path()))
            if c:
                ruleset.delete_rule(rule)
                rulesets.save()
                return
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload

        else:
            if not html.check_transaction():
                return None # browser reload

            if action == "up":
                ruleset.move_rule_up(rule)
            elif action == "down":
                ruleset.move_rule_down(rule)
            elif action == "top":
                ruleset.move_rule_to_top(rule)
            elif action == "move_to":
                ruleset.move_rule_to(rule, int(html.var("_index")))
            else:
                ruleset.move_rule_to_bottom(rule)

            rulesets.save()


    def page(self):
        if not self._hostname:
            watolib.Folder.current().show_breadcrump(keepvarnames=True) # = ["mode", "varname"])

        if not config.wato_hide_varnames:
            display_varname = '%s["%s"]' % tuple(self._name.split(":")) \
                    if ':' in self._name else self._name
            html.div(display_varname, class_="varname")

        rulesets = watolib.AllRulesets()
        rulesets.load()
        ruleset = rulesets.get(self._name)

        html.help(ruleset.help())

        self._explain_match_type(ruleset.match_type())

        if ruleset.is_empty():
            html.div(_("There are no rules defined in this set."), class_="info")
        else:
            self._rule_listing(ruleset)

        self._create_form()


    def _explain_match_type(self, match_type):
        html.b("%s: " % _("Matching"))
        if match_type == "first":
            html.write_text(_("The first matching rule defines the parameter."))

        elif match_type == "dict":
            html.write_text(_("Each parameter is defined by the first matching rule where that "
                              "parameter is set (checked)."))

        elif match_type in ("all", "list"):
            html.write_text(_("All matching rules will add to the resulting list."))

        else:
            html.write_text(_("Unknown match type: %s") % match_type)


    # TODO: Clean this function up!
    def _rule_listing(self, ruleset):
        alread_matched = False
        match_keys = set([]) # in case if match = "dict"
        last_folder = None

        search_options = ModeRuleSearch().search_options

        skip_this_folder = False
        for folder, rulenr, rule in ruleset.get_rules():
            if folder != last_folder:
                # Only show folders related to the currently viewed folder hierarchy
                if folder.is_transitive_parent_of(watolib.Folder.current()) \
                   or watolib.Folder.current().is_transitive_parent_of(folder):
                    skip_this_folder = False
                else:
                    skip_this_folder = True
                    continue

                if last_folder != None:
                    table.end()

                first_in_group = True
                last_folder = folder

                alias_path = folder.alias_path(show_main = False)
                table_id = "rules_%s_%s" % (self._name, folder.ident())
                table.begin(table_id, title="%s %s (%d)" % (_("Rules in folder"), alias_path,
                                                            ruleset.num_rules_in_folder(folder)),
                    css="ruleset", searchable=False, sortable=False, limit=None, foldable=True)
            else:
                if skip_this_folder:
                    continue

                first_in_group = False

            last_in_group = rulenr == ruleset.num_rules_in_folder(folder) - 1

            css = []
            if rule.is_disabled():
                css.append("disabled")

            if ruleset.has_rule_search_options(search_options) \
               and rule.matches_search(search_options) \
               and ("fulltext" not in search_options or not ruleset.matches_fulltext_search(search_options)):
                css.append("matches_search")

            table.row(css=" ".join(css) if css else None)

            if self._just_edited_rule and self._just_edited_rule.folder == rule.folder and self._just_edited_rule.index() == rulenr:
                html.focus_here()

            # Rule matching
            if self._hostname:
                table.cell(_("Ma."))
                if rule.is_disabled():
                    reasons = [ _("This rule is disabled") ]
                else:
                    reasons = list(rule.get_mismatch_reasons(watolib.Folder.current(), self._hostname, self._item))

                matches_rule = not reasons

                # Handle case where dict is constructed from rules
                if matches_rule and ruleset.match_type() == "dict":
                    if not rule.value:
                        title = _("This rule matches, but does not define any parameters.")
                        img = 'imatch'
                    else:
                        new_keys = set(rule.value.keys()) # pylint: disable=no-member
                        if match_keys.isdisjoint(new_keys):
                            title = _("This rule matches and defines new parameters.")
                            img = 'match'
                        elif new_keys.issubset(match_keys):
                            title = _("This rule matches, but all of its parameters are overridden by previous rules.")
                            img = 'imatch'
                        else:
                            title = _("This rule matches, but some of its parameters are overridden by previous rules.")
                            img = 'pmatch'
                        match_keys.update(new_keys)

                elif matches_rule and (not alread_matched or ruleset.match_type() == "all"):
                    title = _("This rule matches for the host '%s'") % self._hostname
                    if ruleset.item_type():
                        title += _(" and the %s '%s'.") % (ruleset.item_name(), self._item)
                    else:
                        title += "."
                    img = 'match'
                    alread_matched = True
                elif matches_rule:
                    title = _("This rule matches, but is overridden by a previous rule.")
                    img = 'imatch'
                    alread_matched = True
                else:
                    title = _("This rule does not match: %s") % " ".join(reasons)
                    img = 'nmatch'
                html.img("images/icon_rule%s.png" % img, align="absmiddle", title=title, class_="icon")

            # Disabling
            table.cell("", css="buttons")
            if rule.is_disabled():
                html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
            else:
                html.empty_icon()

            table.cell(_("Actions"), css="buttons rulebuttons")
            edit_url = watolib.folder_preserving_link([
                ("mode", "edit_rule"),
                ("ruleset_back_mode", self._back_mode),
                ("varname", self._name),
                ("rulenr", rulenr),
                ("host", self._hostname),
                ("item", watolib.mk_repr(self._item)),
                ("rule_folder", folder.path()),
            ])
            html.icon_button(edit_url, _("Edit this rule"), "edit")

            clone_url = watolib.folder_preserving_link([
                ("mode", "clone_rule"),
                ("ruleset_back_mode", self._back_mode),
                ("varname", self._name),
                ("rulenr", rulenr),
                ("host", self._hostname),
                ("item", watolib.mk_repr(self._item)),
                ("rule_folder", folder.path()),
            ])
            html.icon_button(clone_url, _("Create a copy of this rule"), "clone")

            html.element_dragger_url("tr", base_url=self._action_url("move_to", folder, rulenr))
            self._rule_button("delete", _("Delete this rule"), folder, rulenr)

            self._rule_cells(rule)

        if last_folder != None:
            table.end()


    def _action_url(self, action, folder, rulenr):
        vars = [
            ("mode",    html.var('mode', 'edit_ruleset')),
            ("ruleset_back_mode", self._back_mode),
            ("varname", self._name),
            ("_folder", folder.path()),
            ("_rulenr", str(rulenr)),
            ("_action", action),
        ]
        if html.var("rule_folder"):
            vars.append(("rule_folder", folder.path()))
        if html.var("host"):
            vars.append(("host", self._hostname))
        if html.var("item"):
            vars.append(("item", self._item))

        return make_action_link(vars)


    def _rule_button(self, action, help=None, folder=None, rulenr=0):
        html.icon_button(self._action_url(action, folder, rulenr), help, action)


    # TODO: Refactor this whole method
    def _rule_cells(self, rule):
        rulespec  = rule.ruleset.rulespec
        varname   = rule.ruleset.name
        tag_specs = rule.tag_specs
        host_list = rule.host_list
        item_list = rule.item_list
        value     = rule.value
        folder    = rule.folder
        rule_options = rule.rule_options

        # Conditions
        table.cell(_("Conditions"), css="condition")
        self._rule_conditions(rule)

        # Value
        table.cell(_("Value"))
        if rulespec.valuespec:
            try:
                value_html = rulespec.valuespec.value_to_text(value)
            except Exception, e:
                try:
                    reason = "%s" % e
                    rulespec.valuespec.validate_datatype(value, "")
                except Exception, e:
                    reason = "%s" % e

                value_html = '<img src="images/icon_alert.png" class=icon>' \
                           + _("The value of this rule is not valid. ") \
                           + reason
        else:
            img ="yes" if value else "no"
            title = _("This rule results in a positive outcome.") if value else _("this rule results in a negative outcome.")
            value_html = '<img align=absmiddle class=icon title="%s" src="images/rule_%s.png">' \
                            % (title, img)
        html.write(value_html)

        # Comment
        table.cell(_("Description"))
        url = rule_options.get("docu_url")
        if url:
            html.icon_button(url, _("Context information about this rule"), "url", target="_blank")
            html.write("&nbsp;")

        desc = rule_options.get("description") or rule_options.get("comment", "")
        html.write_text(desc)


    def _rule_conditions(self, rule):
        html.open_ul(class_="conditions")
        self._tag_conditions(rule)
        self._host_conditions(rule)
        self._service_conditions(rule)
        html.close_ul()


    def _tag_conditions(self, rule):
        # Host tags
        for tagspec in rule.tag_specs:
            if tagspec[0] == '!':
                negate = True
                tag = tagspec[1:]
            else:
                negate = False
                tag = tagspec

            html.open_li(class_="condition")
            alias = config.tag_alias(tag)
            group_alias = config.tag_group_title(tag)
            if alias:
                if group_alias:
                    html.write_text(_("Host") + ": " + group_alias + " " + _("is") + " ")
                    if negate:
                        html.b(_("not") + " ")
                else:
                    if negate:
                        html.write_text(_("Host does not have tag") + " ")
                    else:
                        html.write_text(_("Host has tag") + " ")
                html.b(alias)
            else:
                if negate:
                    html.write_text(_("Host has <b>not</b> the tag") + " ")
                    html.tt(tag)
                else:
                    html.write_text(_("Host has the tag") + " ")
                    html.tt(tag)
            html.close_li()


    def _host_conditions(self, rule):
        if rule.host_list == ALL_HOSTS:
            return
        # Other cases should not occur, e.g. list of explicit hosts
        # plus ALL_HOSTS.
        condition = self._render_host_condition_text(rule)
        if condition:
            html.li(condition, class_="condition")


    def _render_host_condition_text(self, rule):
        if rule.host_list == []:
            return _("This rule does <b>never</b> apply due to an empty list of explicit hosts!")

        condition, text_list = [], []

        if rule.host_list[0][0] == ENTRY_NEGATE_CHAR:
            host_list = rule.host_list[:-1]
            is_negate = True
        else:
            is_negate = False
            host_list = rule.host_list

        regex_count = len([x for x in host_list if "~" in x])

        condition.append(_("Host name"))

        if regex_count == len(host_list) or regex_count == 0:
            # Entries are either complete regex or no regex at all
            is_regex = regex_count > 0
            if is_regex:
                condition.append(_("is not one of regex")
                                    if is_negate else _("matches one of regex"))
            else:
                condition.append(_("is not one of")
                                    if is_negate else _("is"))

            for host_spec in host_list:
                if not is_regex:
                    host = watolib.Host.host(host_spec)
                    if host:
                        host_spec = html.render_a(host_spec, host.edit_url())

                text_list.append(html.render_b(host_spec.strip("!").strip("~")))

        else:
            # Mixed entries
            for host_spec in host_list:
                is_regex = "~" in host_spec
                host_spec = host_spec.strip("!").strip("~")
                if not is_regex:
                    host = watolib.Host.host(host_spec)
                    if host:
                        host_spec = html.render_a(host_spec, host.edit_url())

                if is_negate:
                    expression = "%s" % (is_regex and _("does not match regex") or _("is not"))
                else:
                    expression = "%s" % (is_regex and _("matches regex") or _("is "))
                text_list.append("%s %s" % (expression, html.render_b(host_spec)))

        if len(text_list) == 1:
            condition.append(text_list[0])
        else:
            condition.append(", ".join([ "%s" % s for s in text_list[:-1] ]))
            condition.append(_(" or ") + text_list[-1])

        return HTML(" ").join(condition)



    def _service_conditions(self, rule):
        if not rule.ruleset.rulespec.item_type or rule.item_list == ALL_SERVICES:
            return

        if rule.ruleset.rulespec.item_type == "service":
            condition = _("Service name ")
        elif rule.ruleset.rulespec.item_type == "item":
            condition = rule.ruleset.rulespec.item_name + " "

        is_negate = rule.item_list[-1] == ALL_SERVICES[0]
        if is_negate:
            item_list = rule.item_list[:-1]
            cleaned_item_list = [ i.lstrip(ENTRY_NEGATE_CHAR) for i in is_negate and item_list ]
        else:
            item_list = rule.item_list
            cleaned_item_list = rule.item_list

        exact_match_count = len([x for x in item_list if x[-1] == "$"])

        text_list = []
        if exact_match_count == len(cleaned_item_list) or exact_match_count == 0:
            if is_negate:
                condition += exact_match_count == 0 and _("does not begin with ") or ("is not ")
            else:
                condition += exact_match_count == 0 and _("begins with ") or ("is ")

            for item in cleaned_item_list:
                text_list.append(html.render_b(item.rstrip("$")))
        else:
            for item in cleaned_item_list:
                is_exact = item[-1] == "$"
                if is_negate:
                    expression = "%s" % (is_exact and _("is not ") or _("begins not with "))
                else:
                    expression = "%s" % (is_exact and _("is ") or _("begins with "))
                text_list.append("%s%s" % (expression, html.render_b(item.rstrip("$"))))

        if len(text_list) == 1:
            condition += text_list[0]
        else:
            condition += ", ".join([ "%s" % s for s in text_list[:-1] ])
            condition += _(" or ") + text_list[-1]

        if condition:
            html.li(condition, class_="condition")


    def _create_form(self):
        html.begin_form("new_rule", add_transid = False)
        html.hidden_field("ruleset_back_mode", self._back_mode, add_var=True)

        html.open_table()
        if self._hostname:
            label = _("Host %s") % self._hostname
            ty = _('Host')
            if self._item != NO_ITEM and self._rulespec.item_type:
                label += _(" and %s '%s'") % (self._rulespec.item_name, self._item)
                ty = self._rulespec.item_name

            html.open_tr()
            html.open_td()
            html.button("_new_host_rule", _("Create %s specific rule for: ") % ty)
            html.hidden_field("host", self._hostname)
            html.hidden_field("item", watolib.mk_repr(self._item))
            html.close_td()
            html.open_td(style="vertical-align:middle")
            html.write_text(label)
            html.close_td()
            html.close_tr()

        html.open_tr()
        html.open_td()
        html.button("_new_rule", _("Create rule in folder: "))
        html.close_td()
        html.open_td()

        html.dropdown("rule_folder", watolib.Folder.folder_choices(), deflt=html.var('folder'))
        html.close_td()
        html.close_tr()
        html.close_table()
        html.write_text("\n")
        html.hidden_field("varname", self._name)
        html.hidden_field("mode", "new_rule")
        html.hidden_field('folder', html.var('folder'))
        html.end_form()



@mode_registry.register
class ModeRuleSearch(WatoMode):
    @classmethod
    def name(cls):
        return "rule_search"


    @classmethod
    def permissions(cls):
        return ["rulesets"]


    def __init__(self):
        self.back_mode = html.var("back_mode", "rulesets")
        super(ModeRuleSearch, self).__init__()


    def title(self):
        if self.search_options:
            return _("Refine search")
        else:
            return _("Search rulesets and rules")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), html.makeuri([("mode", self.back_mode)]), "back")


    def page(self):
        html.begin_form("rule_search", method="GET")
        html.hidden_field("mode", self.back_mode, add_var=True)

        valuespec = self._valuespec()
        valuespec.render_input_as_form("search", self.search_options)

        html.button("_do_search",    _("Search"))
        html.button("_reset_search", _("Reset"))
        html.hidden_fields()
        html.end_form()


    def _from_vars(self):
        if html.var("_reset_search"):
            html.del_all_vars("search_")
            return {}

        value = self._valuespec().from_html_vars("search")
        self._valuespec().validate_value(value, "search")

        # In case all checkboxes are unchecked, treat this like the reset search button press
        # and remove all vars
        if not value:
            html.del_all_vars("search_")

        self.search_options = value


    def _valuespec(self):
        return Dictionary(
            title = _("Search rulesets"),
            headers = [
                (_("Fulltext search"), [
                    "fulltext",
                ]),
                (_("Rulesets"), [
                    "ruleset_group",
                    "ruleset_name",
                    "ruleset_title",
                    "ruleset_help",
                    "ruleset_deprecated",
                    "ruleset_used",
                ]),
                (_("Rules"), [
                    "rule_description",
                    "rule_comment",
                    "rule_value",
                    "rule_host_list",
                    "rule_item_list",
                    "rule_hosttags",
                    "rule_disabled",
                    "rule_ineffective",
                    "rule_folder",
                ]),
            ],
            elements = [
                ("fulltext", RegExpUnicode(
                    title = _("Rules matching pattern"),
                    help = _("Use this field to search the description, comment, host and "
                             "service conditions including the text representation of the "
                             "configured values."),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),

                ("ruleset_group", DropdownChoice(
                    title = _("Group"),
                    choices = lambda: watolib.g_rulespecs.get_group_choices(self.back_mode),
                )),
                ("ruleset_name", RegExpUnicode(
                    title = _("Name"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("ruleset_title", RegExpUnicode(
                    title = _("Title"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("ruleset_help", RegExpUnicode(
                    title = _("Help"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("ruleset_deprecated", DropdownChoice(
                    title = _("Deprecated"),
                    choices = [
                        (True, _("Search for deprecated rulesets")),
                        (False, _("Search for not deprecated rulesets")),
                    ],
                )),
                ("ruleset_used", DropdownChoice(
                    title = _("Used"),
                    choices = [
                        (True, _("Search for rulesets that have rules configured")),
                        (False, _("Search for rulesets that don't have rules configured")),
                    ],
                )),

                ("rule_description", RegExpUnicode(
                    title = _("Description"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("rule_comment", RegExpUnicode(
                    title = _("Comment"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("rule_value", RegExpUnicode(
                    title = _("Value"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("rule_host_list", RegExpUnicode(
                    title = _("Host match list"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("rule_item_list", RegExpUnicode(
                    title = _("Item match list"),
                    size = 60,
                    mode = RegExpUnicode.infix,
                )),
                ("rule_hosttags", watolib.HostTagCondition(
                    title = _("Used host tags"))
                ),
                ("rule_disabled", DropdownChoice(
                    title = _("Disabled"),
                    choices = [
                        (True, _("Search for disabled rules")),
                        (False, _("Search for enabled rules")),
                    ],
                )),
                ("rule_ineffective", DropdownChoice(
                    title = _("Ineffective"),
                    choices = [
                        (True, _("Search for ineffective rules (not matching any host or service)")),
                        (False, _("Search for effective rules")),
                    ],
                )),
                ("rule_folder", Tuple(
                    title = _("Folder"),
                    elements = [
                        DropdownChoice(
                            title   = _("Selection"),
                            choices = watolib.Folder.folder_choices(),
                        ),
                        DropdownChoice(
                            title   = _("Recursion"),
                            choices = [
                                (True,  _("Also search in subfolders")),
                                (False, _("Search in this folder")),
                            ],
                            default_value = False,
                        ),
                    ],
                )),
            ],
        )


class EditRuleMode(WatoMode):
    def _from_vars(self):
        self._name = html.var("varname")

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        try:
            self._rulespec = watolib.g_rulespecs.get(self._name)
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        self._back_mode = html.var('back_mode', 'edit_ruleset')

        self._set_folder()

        self._rulesets = watolib.FolderRulesets(self._folder)
        self._rulesets.load()
        self._ruleset = self._rulesets.get(self._name)

        self._set_rule()


    def _set_folder(self):
        self._folder = watolib.Folder.folder(html.var("rule_folder"))


    def _set_rule(self):
        if html.var("rulenr"):
            try:
                rulenr = int(html.var("rulenr"))
                self._rule = self._ruleset.get_rule(self._folder, rulenr)
            except (KeyError, TypeError, ValueError, IndexError):
                raise MKUserError("rulenr", _("You are trying to edit a rule which does "
                                              "not exist anymore."))
        elif html.var("_export_rule"):
            self._rule = watolib.Rule(self._folder, self._ruleset)
            self._update_rule_from_html_vars()

        else:
            raise NotImplementedError()


    def title(self):
        return _("Edit rule: %s") % self._rulespec.title


    def buttons(self):
        if self._back_mode == 'edit_ruleset':
            var_list = [
                ("mode", "edit_ruleset"),
                ("varname", self._name),
                ("host", html.var("host", "")),
            ]
            if html.var("item"):
                var_list.append(("item", html.var("item")))
            backurl = watolib.folder_preserving_link(var_list)

        else:
            backurl = watolib.folder_preserving_link([
                ('mode', self._back_mode),
                ("host", html.var("host",""))
            ])

        html.context_button(_("Abort"), backurl, "abort")


    def action(self):
        if not html.check_transaction():
            return self._back_mode

        self._update_rule_from_html_vars()

        # Check permissions on folders
        new_rule_folder = watolib.Folder.folder(html.var("new_rule_folder"))
        if not isinstance(self, ModeNewRule):
            self._folder.need_permission("write")
        new_rule_folder.need_permission("write")

        if html.var("_export_rule"):
            return "edit_rule"

        if new_rule_folder == self._folder:
            self._rule.folder = new_rule_folder
            self._save_rule()

        else:
            # Move rule to new folder during editing
            self._remove_from_orig_folder()

            # Set new folder
            self._rule.folder = new_rule_folder

            self._rulesets = watolib.FolderRulesets(new_rule_folder)
            self._rulesets.load()
            self._ruleset = self._rulesets.get(self._name)
            self._ruleset.append_rule(new_rule_folder, self._rule)
            self._rulesets.save()

            affected_sites = list(set(self._folder.all_site_ids() + new_rule_folder.all_site_ids()))
            add_change("edit-rule", _("Changed properties of rule \"%s\", moved rule from "
                        "folder \"%s\" to \"%s\"") % (self._ruleset.title(), self._folder.alias_path(),
                        new_rule_folder.alias_path()), sites=affected_sites)

        return (self._back_mode, self._success_message())


    def _update_rule_from_html_vars(self):
        # Additional options
        rule_options = self._vs_rule_options().from_html_vars("options")
        self._vs_rule_options().validate_value(rule_options, "options")
        self._rule.rule_options = rule_options

        # CONDITION
        tag_specs, host_list, item_list = self._get_rule_conditions()
        self._rule.tag_specs = tag_specs
        self._rule.host_list = host_list
        self._rule.item_list = item_list

        # VALUE
        if self._ruleset.valuespec():
            value = get_edited_value(self._ruleset.valuespec())
        else:
            value = html.var("value") == "yes"
        self._rule.value = value


    @abc.abstractmethod
    def _save_rule(self):
        raise NotImplementedError()


    def _remove_from_orig_folder(self):
        self._ruleset.delete_rule(self._rule)
        self._rulesets.save()


    def _success_message(self):
        return _("Edited rule in ruleset \"%s\" in folder \"%s\"") % \
                 (self._ruleset.title(), self._folder.alias_path())


    def _get_rule_conditions(self):
        tag_list = watolib.get_tag_conditions()

        # Host list
        if not html.get_checkbox("explicit_hosts"):
            host_list = ALL_HOSTS
        else:
            negate = html.get_checkbox("negate_hosts")
            nr = 0
            vs = ListOfStrings()
            host_list = vs.from_html_vars("hostlist")
            vs.validate_value(host_list, "hostlist")
            if negate:
                host_list = [ ENTRY_NEGATE_CHAR + h for h in host_list ]
            # append ALL_HOSTS to negated host lists
            if len(host_list) > 0 and host_list[0][0] == ENTRY_NEGATE_CHAR:
                host_list += ALL_HOSTS
            elif len(host_list) == 0 and negate:
                host_list = ALL_HOSTS # equivalent

        # Item list
        itemtype = self._rulespec.item_type
        if itemtype:
            explicit = html.get_checkbox("explicit_services")
            if not explicit:
                item_list = ALL_SERVICES
            else:
                itemenum = self._rulespec.item_enum
                negate = html.get_checkbox("negate_entries")

                if itemenum:
                    itemspec = ListChoice(choices = itemenum, columns = 3)
                    item_list = [ x+"$" for x in itemspec.from_html_vars("item") ]
                else:
                    vs = self._vs_service_conditions()
                    item_list = vs.from_html_vars("itemlist")
                    vs.validate_value(item_list, "itemlist")

                if negate:
                    item_list = [ ENTRY_NEGATE_CHAR + i for i in item_list]

                if len(item_list) > 0 and item_list[0][0] == ENTRY_NEGATE_CHAR:
                    item_list += ALL_SERVICES
                elif len(item_list) == 0 and negate:
                    item_list = ALL_SERVICES # equivalent

                if len(item_list) == 0:
                    raise MKUserError("item_0", _("Please specify at least one %s or "
                        "this rule will never match.") % self._rulespec.item_name)
        else:
            item_list = None

        return tag_list, host_list, item_list


    def page(self):
        if html.var("_export_rule"):
            self._show_rule_representation()

        else:
            self._show_rule_editor()


    def _show_rule_editor(self):
        if self._ruleset.help():
            html.div(HTML(self._ruleset.help()), class_="info")

        html.begin_form("rule_editor", method="POST")

        # Additonal rule options
        self._vs_rule_options().render_input("options", self._rule.rule_options)

        # Value
        valuespec = self._ruleset.valuespec()
        if valuespec:
            forms.header(valuespec.title() or _("Value"))
            forms.section()
            html.prevent_password_auto_completion()
            try:
                valuespec.validate_datatype(self._rule.value, "ve")
                valuespec.render_input("ve", self._rule.value)
            except Exception, e:
                if config.debug:
                    raise
                else:
                    html.show_warning(_('Unable to read current options of this rule. Falling back to '
                                        'default values. When saving this rule now, your previous settings '
                                        'will be overwritten. Problem was: %s.') % e)

                # In case of validation problems render the input with default values
                valuespec.render_input("ve", valuespec.default_value())

            valuespec.set_focus("ve")
        else:
            forms.header(_("Positive / Negative"))
            forms.section("")
            for posneg, img in [ ("positive", "yes"), ("negative", "no")]:
                val = img == "yes"
                html.img("images/rule_%s.png" % img, class_="ruleyesno", align="top")
                html.radiobutton("value", img, self._rule.value == val, _("Make the outcome of the ruleset <b>%s</b><br>") % posneg)
        # Conditions
        forms.header(_("Conditions"))

        # Rule folder
        forms.section(_("Folder"))
        html.dropdown("new_rule_folder", watolib.Folder.folder_choices(), deflt=self._folder.path())
        html.help(_("The rule is only applied to hosts directly in or below this folder."))

        # Host tags
        forms.section(_("Host tags"))
        watolib.render_condition_editor(self._rule.tag_specs)
        html.help(_("The rule will only be applied to hosts fulfilling all "
                     "of the host tag conditions listed here, even if they appear "
                     "in the list of explicit host names."))

        # Explicit hosts / ALL_HOSTS
        forms.section(_("Explicit hosts"))
        div_id = "div_all_hosts"

        checked = self._rule.host_list != ALL_HOSTS
        html.checkbox("explicit_hosts", checked, onclick="valuespec_toggle_option(this, %r)" % div_id,
              label = _("Specify explicit host names"))
        html.open_div(style="display:none;" if not checked else None, id_=div_id)
        negate_hosts = len(self._rule.host_list) > 0 and self._rule.host_list[0].startswith("!")

        explicit_hosts = [ h.strip("!") for h in self._rule.host_list if h != ALL_HOSTS[0] ]
        ListOfStrings(
            orientation = "horizontal",
            valuespec = TextAscii(size = 30)).render_input("hostlist", explicit_hosts)

        html.checkbox("negate_hosts", negate_hosts, label =
                     _("<b>Negate:</b> make rule apply for <b>all but</b> the above hosts"))
        html.close_div()
        html.help(_("Here you can enter a list of explicit host names that the rule should or should "
                     "not apply to. Leave this option disabled if you want the rule to "
                     "apply for all hosts specified by the given tags. The names that you "
                     "enter here are compared with case sensitive exact matching. Alternatively "
                     "you can use regular expressions if you enter a tilde (<tt>~</tt>) as the first "
                     "character. That regular expression must match the <i>beginning</i> of "
                     "the host names in question."))

        # Itemlist
        itemtype = self._ruleset.item_type()
        if itemtype:
            if itemtype == "service":
                forms.section(_("Services"))
                html.help(_("Specify a list of service patterns this rule shall apply to. "
                             "The patterns must match the <b>beginning</b> of the service "
                             "in question. Adding a <tt>$</tt> to the end forces an excact "
                             "match. Pattern use <b>regular expressions</b>. A <tt>.*</tt> will "
                             "match an arbitrary text."))
            elif itemtype == "checktype":
                forms.section(_("Check types"))
            elif itemtype == "item":
                forms.section(self._ruleset.item_name().title())
                if self._ruleset.item_help():
                    html.help(self._ruleset.item_help())
                else:
                    html.help(_("You can make the rule apply only to certain services of the "
                                 "specified hosts. Do this by specifying explicit <b>items</b> to "
                                 "match here. <b>Hint:</b> make sure to enter the item only, "
                                 "not the full Service description. "
                                 "<b>Note:</b> the match is done on the <u>beginning</u> "
                                 "of the item in question. Regular expressions are interpreted, "
                                 "so appending a <tt>$</tt> will force an exact match."))
            else:
                raise MKGeneralException("Invalid item type '%s'" % itemtype)

            checked = html.get_checkbox("explicit_services")
            if checked == None: # read from rule itself
                checked = len(self._rule.item_list) == 0 or self._rule.item_list[0] != ""
            div_id = "item_list"
            html.checkbox("explicit_services", checked, onclick="valuespec_toggle_option(this, %r)" % div_id,
                         label = _("Specify explicit values"))
            html.open_div(id_=div_id, style=["display: none;" if not checked else "", "padding: 0px;"])

            negate_entries = len(self._rule.item_list) > 0 and self._rule.item_list[0].startswith(ENTRY_NEGATE_CHAR)
            if negate_entries:
                cleaned_item_list = [ i.lstrip(ENTRY_NEGATE_CHAR) for i in self._rule.item_list[:-1] ] # strip last entry (ALL_SERVICES)
            else:
                cleaned_item_list = self._rule.item_list

            itemenum = self._ruleset.item_enum()
            if itemenum:
                value = [ x.rstrip("$") for x in cleaned_item_list ]
                itemspec = ListChoice(choices = itemenum, columns = 3)
                itemspec.render_input("item", value)
            else:
                self._vs_service_conditions().render_input("itemlist", cleaned_item_list)

            html.checkbox("negate_entries", negate_entries, label =
                         _("<b>Negate:</b> make rule apply for <b>all but</b> the above entries"))

            html.close_div()

        forms.end()

        html.button("save", _("Save"))
        html.hidden_fields()
        self._vs_rule_options().set_focus("options")
        html.button("_export_rule", _("Export"))

        html.end_form()


    def _show_rule_representation(self):
        content = "<pre>%s</pre>" % html.render_text(pprint.pformat(self._rule.to_dict_config()))

        html.write(_("This rule representation can be used for Web API calls."))
        html.br()
        html.br()

        html.open_center()
        html.open_table(class_="progress")

        html.open_tr()
        html.th("Rule representation for Web API")
        html.close_tr()

        html.open_tr()
        html.td(html.render_div(content,  id_="rule_representation"), class_="log")
        html.close_tr()

        html.close_table()
        html.close_center()


    def _vs_service_conditions(self,):
        return ListOfStrings(
            orientation = "horizontal",
            valuespec = RegExpUnicode(
                size = 30,
                mode = RegExpUnicode.prefix
            ),
        )


    def _vs_rule_options(self, disabling=True):
        return Dictionary(
            title = _("Rule Properties"),
            optional_keys = False,
            render = "form",
            elements = rule_option_elements(disabling),
        )



@mode_registry.register
class ModeEditRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "edit_rule"


    @classmethod
    def permissions(cls):
        return []


    def _save_rule(self):
        # Just editing without moving to other folder
        self._ruleset.edit_rule(self._rule)
        self._rulesets.save()



@mode_registry.register
class ModeCloneRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "clone_rule"


    @classmethod
    def permissions(cls):
        return []


    def _set_rule(self):
        super(ModeCloneRule, self)._set_rule()

        self._orig_rule = self._rule
        self._rule = self._orig_rule.clone()


    def _save_rule(self):
        if self._rule.folder == self._orig_rule.folder:
            self._ruleset.insert_rule_after(self._rule, self._orig_rule)
        else:
            self._ruleset.append_rule(self._rule.folder(), self._rule)

        self._rulesets.save()


    def _remove_from_orig_folder(self):
        pass # Cloned rule is not yet in folder, don't try to remove



@mode_registry.register
class ModeNewRule(EditRuleMode):
    @classmethod
    def name(cls):
        return "new_rule"


    @classmethod
    def permissions(cls):
        return []


    def title(self):
        return _("New rule: %s") % self._rulespec.title


    def _set_folder(self):
        if html.has_var("_new_rule"):
            # Start creating new rule in the choosen folder
            self._folder = watolib.Folder.folder(html.var("rule_folder"))

        elif html.has_var("_new_host_rule"):
            # Start creating new rule for a specific host
            self._folder = watolib.Folder.current()

        else:
            # Submitting the creation dialog
            self._folder = watolib.Folder.folder(html.var("new_rule_folder"))


    def _set_rule(self):
        host_list = ALL_HOSTS
        item_list = [ "" ]

        if html.has_var("_new_host_rule"):
            hostname = html.var("host")
            if hostname:
                host_list = [hostname]

            if self._rulespec.item_type:
                item = watolib.mk_eval(html.var("item")) if html.has_var("item") else NO_ITEM
                if item != NO_ITEM:
                    item_list = [ "%s$" % escape_regex_chars(item) ]

        self._rule = watolib.Rule.create(self._folder, self._ruleset, host_list, item_list)


    def _save_rule(self):
        self._ruleset.append_rule(self._folder, self._rule)
        self._rulesets.save()
        add_change("edit-rule", _("Created new rule in ruleset \"%s\" in folder \"%s\"") %
                (self._ruleset.title(),
                 self._folder.alias_path()), # pylint: disable=no-member
                 sites=self._folder.all_site_ids()) # pylint: disable=no-member


    def _success_message(self):
        return _("Created new rule in ruleset \"%s\" in folder \"%s\"") % \
                 (self._ruleset.title(),
                  self._folder.alias_path()) # pylint: disable=no-member


#.
#   .--User Profile--------------------------------------------------------.
#   |         _   _                 ____             __ _ _                |
#   |        | | | |___  ___ _ __  |  _ \ _ __ ___  / _(_) | ___           |
#   |        | | | / __|/ _ \ '__| | |_) | '__/ _ \| |_| | |/ _ \          |
#   |        | |_| \__ \  __/ |    |  __/| | | (_) |  _| | |  __/          |
#   |         \___/|___/\___|_|    |_|   |_|  \___/|_| |_|_|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A user can change several aspects of it's own profile                |
#   '----------------------------------------------------------------------'


def select_language(user):
    languages = [ l for l in cmk.gui.i18n.get_languages() if not config.hide_language(l[0]) ]
    if languages:
        active = 'language' in user
        forms.section(_("Language"), checkbox = ('_set_lang', active, 'language'))
        default_label = _('Default: %s') % (cmk.gui.i18n.get_language_alias(config.default_language) or _('English'))
        html.div(default_label, class_="inherited", id_="attr_default_language", style= "display: none" if active else "")
        html.open_div(id_="attr_entry_language", style="display: none" if not active else "")

        language = user.get('language') if user.get('language') != None else ''

        # Transform 'en' configured language to empty string for compatibility reasons
        if language == "en":
            language = ""

        html.dropdown("language", languages, deflt=language)
        html.close_div()
        html.help(_('Configure the default language '
                    'to be used by the user in the user interface here. If you do not check '
                    'the checkbox, then the system default will be used.<br><br>'
                    'Note: currently Multisite is internationalized '
                    'but comes without any actual localisations (translations). If you want to '
                    'create you own translation, you find <a href="%(url)s">documentation online</a>.') %
                    { "url" : "https://mathias-kettner.com/checkmk_multisite_cmk.gui.i18n.html"} )

def user_profile_async_replication_page():
    html.header(_('Replicate new User Profile'),
                javascripts = ['wato'],
                stylesheets = ['check_mk', 'pages', 'wato', 'status'])

    html.begin_context_buttons()
    html.context_button(_('User Profile'), 'user_profile.py', 'back')
    html.end_context_buttons()

    sites = [site_id for site_id, site in config.user.authorized_login_sites()]
    user_profile_async_replication_dialog(sites=sites)

    html.footer()


def user_profile_async_replication_dialog(sites):
    repstatus = watolib.load_replication_status()

    html.p(_('In order to activate your changes available on all remote sites, your user profile needs '
             'to be replicated to the remote sites. This is done on this page now. Each site '
             'is being represented by a single image which is first shown gray and then fills '
             'to green during synchronisation.'))

    html.h3(_('Replication States'))
    html.open_div(id_="profile_repl")
    num_replsites = 0
    for site_id in sites:
        site = config.sites[site_id]
        srs  = repstatus.get(site_id, {})

        if not "secret" in site:
            status_txt = _('Not logged in.')
            start_sync = False
            icon       = 'repl_locked'
        else:
            status_txt = _('Waiting for replication to start')
            start_sync = True
            icon       = 'repl_pending'

        html.open_div(class_="site", id_="site-%s" % site_id)

        html.icon(status_txt, icon)
        if start_sync:
            changes_manager = watolib.ActivateChanges()
            changes_manager.load()
            estimated_duration = changes_manager.get_activation_time(site_id, watolib.ACTIVATION_TIME_PROFILE_SYNC, 2.0)
            html.javascript('wato_do_profile_replication(\'%s\', %d, \'%s\');' %
                      (site_id, int(estimated_duration * 1000.0), _('Replication in progress')))
            num_replsites += 1
        else:
            watolib.add_profile_replication_change(site_id, status_txt)
        html.span(site.get('alias', site_id))

        html.close_div()

    html.javascript('var g_num_replsites = %d;\n' % num_replsites)

    html.close_div()


@cmk.gui.pages.register("user_change_pw")
def page_change_own_password():
    page_user_profile(change_pw=True)


@cmk.gui.pages.register("user_profile")
def page_user_profile(change_pw=False):
    start_async_replication = False

    if not config.user.id:
        raise MKUserError(None, _('Not logged in.'))

    if not config.user.may('general.edit_profile') and not config.user.may('general.change_password'):
        raise MKAuthException(_("You are not allowed to edit your user profile."))

    if not config.wato_enabled:
        raise MKAuthException(_('User profiles can not be edited (WATO is disabled).'))

    success = None
    if html.has_var('_save') and html.check_transaction():
        users = userdb.load_users(lock = True)

        try:
            # Profile edit (user options like language etc.)
            if config.user.may('general.edit_profile'):
                if not change_pw:
                    set_lang = html.get_checkbox('_set_lang')
                    language = html.var('language')
                    # Set the users language if requested
                    if set_lang:
                        if language == '':
                            language = None
                        # Set custom language
                        users[config.user.id]['language'] = language
                        config.user.set_attribute("language", language)
                        cmk.gui.i18n.set_language_cookie(language)

                    else:
                        # Remove the customized language
                        if 'language' in users[config.user.id]:
                            del users[config.user.id]['language']
                        config.user.unset_attribute("language")

                    # load the new language
                    cmk.gui.i18n.localize(config.user.language())

                    user = users.get(config.user.id)
                    if config.user.may('general.edit_notifications') and user.get("notifications_enabled"):
                        value = forms.get_input(watolib.get_vs_flexible_notifications(), "notification_method")
                        users[config.user.id]["notification_method"] = value

                    # Custom attributes
                    if config.user.may('general.edit_user_attributes'):
                        for name, attr in userdb.get_user_attributes():
                            if attr.user_editable():
                                if not attr.permission() or config.user.may(attr.permission()):
                                    vs = attr.valuespec()
                                    value = vs.from_html_vars('ua_' + name)
                                    vs.validate_value(value, "ua_" + name)
                                    users[config.user.id][name] = value

            # Change the password if requested
            password_changed = False
            if config.user.may('general.change_password'):
                cur_password = html.var('cur_password')
                password     = html.var('password')
                password2    = html.var('password2', '')

                if change_pw:
                    # Force change pw mode
                    if not cur_password:
                        raise MKUserError("cur_password", _("You need to provide your current password."))
                    if not password:
                        raise MKUserError("password", _("You need to change your password."))
                    if cur_password == password:
                        raise MKUserError("password", _("The new password must differ from your current one."))

                if cur_password and password:
                    if userdb.hook_login(config.user.id, cur_password) in [ None, False ]:
                        raise MKUserError("cur_password", _("Your old password is wrong."))
                    if password2 and password != password2:
                        raise MKUserError("password2", _("The both new passwords do not match."))

                    watolib.verify_password_policy(password)
                    users[config.user.id]['password'] = encrypt_password(password)
                    users[config.user.id]['last_pw_change'] = int(time.time())

                    if change_pw:
                        # Has been changed, remove enforcement flag
                        del users[config.user.id]['enforce_pw_change']

                    # Increase serial to invalidate old cookies
                    if 'serial' not in users[config.user.id]:
                        users[config.user.id]['serial'] = 1
                    else:
                        users[config.user.id]['serial'] += 1

                    password_changed = True

            # Now, if in distributed environment where users can login to remote sites,
            # set the trigger for pushing the new auth information to the slave sites
            # asynchronous
            if config.user.authorized_login_sites():
                start_async_replication = True

            userdb.save_users(users)

            if password_changed:
                # Set the new cookie to prevent logout for the current user
                login.set_auth_cookie(config.user.id)

            success = True
        except MKUserError, e:
            html.add_user_error(e.varname, e)
    else:
        users = userdb.load_users()

    init_wato_datastructures(with_wato_lock=True)

    # When in distributed setup, display the replication dialog instead of the normal
    # profile edit dialog after changing the password.
    if start_async_replication:
        user_profile_async_replication_page()
        return

    if change_pw:
        title = _("Change Password")
    else:
        title = _("Edit User Profile")

    html.header(title, javascripts = ['wato'], stylesheets = ['check_mk', 'pages', 'wato', 'status'])

    # Rule based notifications: The user currently cannot simply call the according
    # WATO module due to WATO permission issues. So we cannot show this button
    # right now.
    if not change_pw:
        rulebased_notifications = watolib.load_configuration_settings().get("enable_rulebased_notifications")
        if rulebased_notifications and config.user.may('general.edit_notifications'):
            html.begin_context_buttons()
            url = "wato.py?mode=user_notifications_p"
            html.context_button(_("Notifications"), url, "notifications")
            html.end_context_buttons()
    else:
        reason = html.var('reason')
        if reason == 'expired':
            html.p(_('Your password is too old, you need to choose a new password.'))
        else:
            html.p(_('You are required to change your password before proceeding.'))

    if success:
        html.reload_sidebar()
        if change_pw:
            html.message(_("Your password has been changed."))
            html.response.http_redirect(html.var('_origtarget', 'index.py'))
        else:
            html.message(_("Successfully updated user profile."))

    if html.has_user_errors():
        html.show_user_errors()

    user = users.get(config.user.id)
    if user == None:
        html.show_warning(_("Sorry, your user account does not exist."))
        html.footer()
        return

    # Returns true if an attribute is locked and should be read only. Is only
    # checked when modifying an existing user
    locked_attributes = userdb.locked_attributes(user.get('connector'))
    def is_locked(attr):
        return attr in locked_attributes

    html.begin_form("profile", method="POST")
    html.prevent_password_auto_completion()
    html.open_div(class_="wato")
    forms.header(_("Personal Settings"))

    if not change_pw:
        forms.section(_("Name"), simple=True)
        html.write_text(user.get("alias", config.user.id))

    if config.user.may('general.change_password') and not is_locked('password'):
        forms.section(_("Current Password"))
        html.password_input('cur_password', autocomplete="new-password")

        forms.section(_("New Password"))
        html.password_input('password', autocomplete="new-password")

        forms.section(_("New Password Confirmation"))
        html.password_input('password2', autocomplete="new-password")

    if not change_pw and config.user.may('general.edit_profile'):
        select_language(user)

        # Let the user configure how he wants to be notified
        if not rulebased_notifications \
            and config.user.may('general.edit_notifications') \
            and user.get("notifications_enabled"):
            forms.section(_("Notifications"))
            html.help(_("Here you can configure how you want to be notified about host and service problems and "
                        "other monitoring events."))
            watolib.get_vs_flexible_notifications().render_input("notification_method", user.get("notification_method"))

        if config.user.may('general.edit_user_attributes'):
            for name, attr in userdb.get_user_attributes():
                if attr.user_editable():
                    vs = attr.valuespec()
                    forms.section(_u(vs.title()))
                    value = user.get(name, vs.default_value())
                    if not attr.permission() or config.user.may(attr.permission()):
                        vs.render_input("ua_" + name, value)
                        html.help(_u(vs.help()))
                    else:
                        html.write(vs.value_to_text(value))

    # Save button
    forms.end()
    html.button("_save", _("Save"))
    html.close_div()
    html.hidden_fields()
    html.end_form()
    html.footer()


class ModeAjaxProfileReplication(WatoWebApiMode):
    """AJAX handler for asynchronous replication of user profiles (changed passwords)"""

    def page(self):
        request = self.webapi_request()

        site_id = request.get("site")
        if not site_id:
            raise MKUserError(None, "The site_id is missing")

        if site_id not in config.sitenames():
            raise MKUserError(None, _("The requested site does not exist"))

        status = sites.state(site_id, {}).get("state", "unknown")
        if status == "dead":
            raise MKGeneralException(_('The site is marked as dead. Not trying to replicate.'))

        site = config.site(site_id)
        result = self._synchronize_profile(site_id, site, config.user.id)

        if result != True:
            watolib.add_profile_replication_change(site_id, result)
            raise MKGeneralException(result)

        return _("Replication completed successfully.")


    def _synchronize_profile(self, site_id, site, user_id):
        users = userdb.load_users(lock = False)
        if not user_id in users:
            raise MKUserError(None, _('The requested user does not exist'))

        start = time.time()
        result = watolib.push_user_profile_to_site(site, user_id, users[user_id])
        duration = time.time() - start
        watolib.ActivateChanges().update_activation_time(site_id, watolib.ACTIVATION_TIME_PROFILE_SYNC, duration)
        return result

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

        self._back_url = html.var("back_url")

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

        job_snapshot = self._job.get_status_snapshot()
        if html.has_var("_start") and not self._job.is_running():
            self._job.start()

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
#   .--Sampleconfig--------------------------------------------------------.
#   |   ____                        _                       __ _           |
#   |  / ___|  __ _ _ __ ___  _ __ | | ___  ___ ___  _ __  / _(_) __ _     |
#   |  \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __/ _ \| '_ \| |_| |/ _` |    |
#   |   ___) | (_| | | | | | | |_) | |  __/ (_| (_) | | | |  _| | (_| |    |
#   |  |____/ \__,_|_| |_| |_| .__/|_|\___|\___\___/|_| |_|_| |_|\__, |    |
#   |                        |_|                                 |___/     |
#   +----------------------------------------------------------------------+
#   | Functions for creating an example configuration                      |
#   '----------------------------------------------------------------------'

# Create a very basic sample configuration, but only if none of the
# files that we will create already exists. That is e.g. the case
# after an update from an older version where no sample config had
# been created.
# TODO: Create a hook here and move CEE and other specific things away
def create_sample_config():
    if not need_to_create_sample_config():
        return

    # Just in case. If any of the following functions try to write Git messages
    if config.wato_use_git:
        watolib.prepare_git_commit()

    # Global configuration settings
    watolib.save_global_settings(
        {
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
        }
    )


    # A contact group for all hosts and services
    groups = {
        "contact" : { 'all' : {'alias': u'Everything'} },
    }
    watolib.save_group_information(groups)

    # Basic setting of host tags
    wato_host_tags = \
    [('criticality',
      u'Criticality',
      [('prod', u'Productive system', []),
       ('critical', u'Business critical', []),
       ('test', u'Test system', []),
       ('offline', u'Do not monitor this host', [])]),
     ('networking',
      u'Networking Segment',
      [('lan', u'Local network (low latency)', []),
       ('wan', u'WAN (high latency)', []),
       ('dmz', u'DMZ (low latency, secure access)', [])]),
    ]

    wato_aux_tags = []

    watolib.save_hosttags(wato_host_tags, wato_aux_tags)

    # Rules that match the upper host tag definition
    ruleset_config = {
        # Make the tag 'offline' remove hosts from the monitoring
        'only_hosts': [
            (['!offline'], ['@all'],
            {'description': u'Do not monitor hosts with the tag "offline"'})],

        # Rule for WAN hosts with adapted PING levels
        'ping_levels': [
            ({'loss': (80.0, 100.0),
              'packets': 6,
              'rta': (1500.0, 3000.0),
              'timeout': 20}, ['wan'], ['@all'],
              {'description': u'Allow longer round trip times when pinging WAN hosts'})],

        # All hosts should use SNMP v2c if not specially tagged
        'bulkwalk_hosts': [
            (['snmp', '!snmp-v1'], ['@all'], {'description': u'Hosts with the tag "snmp-v1" must not use bulkwalk'})],

        # Put all hosts and the contact group 'all'
        'host_contactgroups': [
            ('all', [], ALL_HOSTS, {'description': u'Put all hosts into the contact group "all"'} ),
        ],

        # Interval for HW/SW-Inventory check
        'extra_service_conf': {
            'check_interval': [
                ( 1440, [], ALL_HOSTS, [ "Check_MK HW/SW Inventory$" ], {'description': u'Restrict HW/SW-Inventory to once a day'} ),
            ],
        },

        # Disable unreachable notifications by default
        'extra_host_conf': {
            'notification_options': [
                ( 'd,r,f,s', [], ALL_HOSTS, {} ),
            ],
        },

        # Periodic service discovery
        'periodic_discovery': [
            ({'severity_unmonitored': 1,
              'severity_vanished': 0,
              'inventory_check_do_scan': True,
              'check_interval': 120.0}, [], ALL_HOSTS, {'description': u'Perform every two hours a service discovery'} ),
        ],
    }

    rulesets = watolib.FolderRulesets(watolib.Folder.root_folder())
    rulesets.from_config(watolib.Folder.root_folder(), ruleset_config)
    rulesets.save()

    notification_rules = [{
        'allow_disable'          : True,
        'contact_all'            : False,
        'contact_all_with_email' : False,
        'contact_object'         : True,
        'description'            : 'Notify all contacts of a host/service via HTML email',
        'disabled'               : False,
        'notify_plugin'          : ('mail', {}),
    }]
    watolib.save_notification_rules(notification_rules)

    try:
        import cmk.gui.cee.plugins.wato.sample_config
        cmk.gui.cee.plugins.wato.sample_config.create_cee_sample_config()
    except ImportError:
        pass

    # Make sure the host tag attributes are immediately declared!
    config.wato_host_tags = wato_host_tags
    config.wato_aux_tags = wato_aux_tags

    # Initial baking of agents (when bakery is available)
    if watolib.has_agent_bakery():
        import cmk.gui.cee.plugins.wato.agent_bakery
        try:
            bake_job = cmk.gui.cee.plugins.wato.agent_bakery.BakeAgentsBackgroundJob()
            if not bake_job.is_running():
                bake_job.set_function(cmk.gui.cee.plugins.wato.agent_bakery.bake_agents_background_job)
                bake_job.start()
        except:
            pass # silently ignore building errors here

    # This is not really the correct place for such kind of action, but the best place we could
    # find to execute it only for new created sites.
    import cmk.gui.werks as werks
    werks.acknowledge_all_werks(check_permission=False)

    cmk.gui.plugins.wato.mkeventd.save_mkeventd_sample_config()

    userdb.create_cmk_automation_user()


def need_to_create_sample_config():
    if os.path.exists(multisite_dir + "hosttags.mk") \
        or os.path.exists(wato_root_dir + "rules.mk") \
        or os.path.exists(wato_root_dir + "groups.mk") \
        or os.path.exists(wato_root_dir + "notifications.mk") \
        or os.path.exists(wato_root_dir + "global.mk"):
        return False
    return True

#.
#   .--Pattern Editor------------------------------------------------------.
#   |   ____       _   _                    _____    _ _ _                 |
#   |  |  _ \ __ _| |_| |_ ___ _ __ _ __   | ____|__| (_) |_ ___  _ __     |
#   |  | |_) / _` | __| __/ _ \ '__| '_ \  |  _| / _` | | __/ _ \| '__|    |
#   |  |  __/ (_| | |_| ||  __/ |  | | | | | |__| (_| | | || (_) | |       |
#   |  |_|   \__,_|\__|\__\___|_|  |_| |_| |_____\__,_|_|\__\___/|_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModePatternEditor(WatoMode):
    @classmethod
    def name(cls):
        return "pattern_editor"


    @classmethod
    def permissions(cls):
        return ["pattern_editor"]


    def _from_vars(self):
        self._hostname   = html.var('host', '')
        # TODO: validate all fields
        self._item       = html.var('file', '')
        self._match_txt  = html.var('match', '')

        self._host = watolib.Folder.current().host(self._hostname)

        if self._hostname and not self._host:
            raise MKUserError(None, _("This host does not exist."))


    def title(self):
        if not self._hostname and not self._item:
            return _("Logfile Pattern Analyzer")
        elif not self._hostname:
            return _("Logfile Patterns of Logfile %s on all Hosts") % (self._item)
        elif not self._item:
            return _("Logfile Patterns of Host %s") % (self._hostname)
        else:
            return _("Logfile Patterns of Logfile %s on Host %s") % (self._item, self._hostname)


    def buttons(self):
        home_button()
        if self._host:
            if self._item:
                title = _("Show Logfile")
            else:
                title = _("Host Logfiles")

            html.context_button(title, html.makeuri_contextless([("host", self._hostname), ("file", self._item)], filename="logwatch.py"), 'logwatch')

        html.context_button(_('Edit Logfile Rules'), watolib.folder_preserving_link([
                ('mode', 'edit_ruleset'),
                ('varname', 'logwatch_rules')
            ]),
            'edit'
        )


    def page(self):
        html.help(_('On this page you can test the defined logfile patterns against a custom text, '
                    'for example a line from a logfile. Using this dialog it is possible to analyze '
                    'and debug your whole set of logfile patterns.'))

        self._show_try_form()
        self._show_patterns()


    def _show_try_form(self):
        html.begin_form('try')
        forms.header(_('Try Pattern Match'))
        forms.section(_('Hostname'))
        html.text_input('host')
        forms.section(_('Logfile'))
        html.text_input('file')
        forms.section(_('Text to match'))
        html.help(_('You can insert some text (e.g. a line of the logfile) to test the patterns defined '
              'for this logfile. All patterns for this logfile are listed below. Matching patterns '
              'will be highlighted after clicking the "Try out" button.')
        )
        html.text_input('match', cssclass = 'match', size=100)
        forms.end()
        html.button('_try', _('Try out'))
        html.del_var('folder') # Never hand over the folder here
        html.hidden_fields()
        html.end_form()


    def _show_patterns(self):
        import cmk.gui.logwatch as logwatch
        collection = watolib.SingleRulesetRecursively("logwatch_rules")
        collection.load()
        ruleset = collection.get("logwatch_rules")

        html.h3(_('Logfile Patterns'))
        if ruleset.is_empty():
            html.open_div(class_="info")
            html.write_text('There are no logfile patterns defined. You may create '
                            'logfile patterns using the <a href="%s">Rule Editor</a>.' %
                             watolib.folder_preserving_link([
                                 ('mode', 'edit_ruleset'),
                                 ('varname', 'logwatch_rules')
                             ]))
            html.close_div()

        # Loop all rules for this ruleset
        already_matched = False
        last_folder = None
        abs_rulenr = 0
        for folder, rulenr, rule in ruleset.get_rules():
            last_in_group = rulenr == ruleset.num_rules_in_folder(folder) - 1

            # Check if this rule applies to the given host/service
            if self._hostname:
                # If hostname (and maybe filename) try match it
                rule_matches = rule.matches_host_and_item(watolib.Folder.current(), self._hostname, self._item)
            elif self._item:
                # If only a filename is given
                rule_matches = rule.matches_item()
            else:
                # If no host/file given match all rules
                rule_matches = True

            html.begin_foldable_container("rule", "%s" % abs_rulenr, True,
                        HTML("<b>Rule #%d</b>" % (abs_rulenr + 1)), indent = False)
            table.begin("pattern_editor_rule_%d" % abs_rulenr, sortable=False)
            abs_rulenr += 1

            # TODO: What's this?
            pattern_list = rule.value
            if type(pattern_list) == dict:
                pattern_list = pattern_list["reclassify_patterns"]

            # Each rule can hold no, one or several patterns. Loop them all here
            odd = "odd"
            for state, pattern, comment in pattern_list:
                match_class = ''
                disp_match_txt = ''
                match_img = ''
                if rule_matches:
                    # Applies to the given host/service
                    reason_class = 'reason'

                    matched = re.search(pattern, self._match_txt)
                    if matched:

                        # Prepare highlighted search txt
                        match_start = matched.start()
                        match_end   = matched.end()
                        disp_match_txt = html.render_text(self._match_txt[:match_start]) \
                                         + html.render_span(self._match_txt[match_start:match_end], class_="match")\
                                         + html.render_text(self._match_txt[match_end:])

                        if already_matched == False:
                            # First match
                            match_class  = 'match first'
                            match_img   = 'match'
                            match_title = _('This logfile pattern matches first and will be used for '
                                            'defining the state of the given line.')
                            already_matched = True
                        else:
                            # subsequent match
                            match_class = 'match'
                            match_img  = 'imatch'
                            match_title = _('This logfile pattern matches but another matched first.')
                    else:
                        match_img   = 'nmatch'
                        match_title = _('This logfile pattern does not match the given string.')
                else:
                    # rule does not match
                    reason_class = 'noreason'
                    match_img   = 'nmatch'
                    match_title = _('The rule conditions do not match.')

                table.row(css=reason_class)
                table.cell(_('Match'))
                html.icon(match_title, "rule%s" % match_img)

                cls = ''
                if match_class == 'match first':
                    cls = 'svcstate state%d' % logwatch.level_state(state)
                table.cell(_('State'), logwatch.level_name(state), css=cls)
                table.cell(_('Pattern'), html.render_tt(pattern))
                table.cell(_('Comment'), html.render_text(comment))
                table.cell(_('Matched line'), disp_match_txt)

            table.row(fixed=True)
            table.cell(colspan=5)
            edit_url = watolib.folder_preserving_link([
                ("mode", "edit_rule"),
                ("varname", "logwatch_rules"),
                ("rulenr", rulenr),
                ("host", self._hostname),
                ("item", watolib.mk_repr(self._item)),
                ("rule_folder", folder.path())])
            html.icon_button(edit_url, _("Edit this rule"), "edit")

            table.end()
            html.end_foldable_container()




#.
#   .--Check Plugins-------------------------------------------------------.
#   |     ____ _               _      ____  _             _                |
#   |    / ___| |__   ___  ___| | __ |  _ \| |_   _  __ _(_)_ __  ___      |
#   |   | |   | '_ \ / _ \/ __| |/ / | |_) | | | | |/ _` | | '_ \/ __|     |
#   |   | |___| | | |  __/ (__|   <  |  __/| | |_| | (_| | | | | \__ \     |
#   |    \____|_| |_|\___|\___|_|\_\ |_|   |_|\__,_|\__, |_|_| |_|___/     |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Catalog of check plugins                                             |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeCheckPlugins(WatoMode):
    @classmethod
    def name(cls):
        return "check_plugins"


    @classmethod
    def permissions(cls):
        return []


    def _from_vars(self):
        self._search = get_search_expression()
        self._topic  = html.var("topic")
        if self._topic and not self._search:
            if not re.match("^[a-zA-Z0-9_./]+$", self._topic):
                raise Exception("Invalid topic")

            self._path = tuple(self._topic.split("/")) # e.g. [ "hw", "network" ]
        else:
            self._path = tuple()

        for comp in self._path:
            ID().validate_value(comp, None) # Beware against code injection!

        self._manpages = self._get_check_catalog()
        self._titles = man_pages.man_page_catalog_titles()

        self._has_second_level = None
        if self._topic and not self._search:
            for t, has_second_level, title, helptext in self._man_page_catalog_topics():
                if t == self._path[0]:
                    self._has_second_level = has_second_level
                    self._topic_title = title
                    break

            if len(self._path) == 2:
                self._topic_title = self._titles.get(self._path[1], self._path[1])


    def title(self):
        if self._topic and not self._search:
            heading = "%s - %s" % ( _("Catalog of Check Plugins"), self._topic_title )
        elif self._search:
            heading = html.render_text("%s: %s" % (_("Check plugins matching"), self._search))
        else:
            heading = _("Catalog of Check Plugins")
        return heading


    def buttons(self):
        global_buttons()
        if self._topic:
            if len(self._path) == 2:
                back_url = html.makeuri([("topic", self._path[0])])
            else:
                back_url = html.makeuri([("topic", "")])
            html.context_button(_("Back"), back_url, "back")


    def page(self):
        html.help(_("This catalog of check plugins gives you a complete listing of all plugins "
                    "that are shipped with your Check_MK installation. It also allows you to "
                    "access the rule sets for configuring the parameters of the checks and to "
                    "manually create services in case you cannot or do not want to rely on the "
                    "automatic service discovery."))

        search_form( "%s: " % _("Search for check plugins"), "check_plugins" )

        # The maxium depth of the catalog paths is 3. The top level is being rendered
        # like the WATO main menu. The second and third level are being rendered like
        # the global settings.

        if self._topic and not self._search:
            self._render_manpage_topic()

        elif self._search:
            for path, manpages in self._get_manpages_after_search():
                self._render_manpage_list(manpages, path, self._titles.get(path, path))

        else:
            menu = MainMenu()
            for topic, has_second_level, title, helptext in self._man_page_catalog_topics():
                menu.add_item(MenuItem(
                    mode_or_url=html.makeuri([("topic", topic)]),
                    title=title,
                    icon="plugins_" + topic,
                    permission=None,
                    description=helptext
                ))
            menu.show()


    def _get_manpages_after_search(self):
        collection  = {}
        handled_check_names = set([])

        # searches in {"name" : "asd", "title" : "das", ...}
        def get_matched_entry( entry ):
            if type( entry ) == dict:
                name = entry.get( "name", "" )
                if type( name ) == str:
                    name = name.decode( "utf8" )

                title = entry.get( "title", "" )
                if type( title ) == str:
                    title = title.decode( "utf8" )
                if self._search in name.lower() or self._search in title.lower():
                    return entry

            return None

        def check_entries( key, entries ):
            if type( entries ) == list:
                these_matches = []
                for entry in entries:
                    match = get_matched_entry( entry )
                    if match:
                        these_matches.append( match )

                if these_matches:
                    collection.setdefault( key, [] )
                    # avoid duplicates due to the fact that a man page can have more than
                    # one places in the global tree of man pages.
                    for match in these_matches:
                        name = match.get("name")
                        if name and name in handled_check_names:
                            continue # avoid duplicate
                        else:
                            collection[key].append(match)
                            if name:
                                handled_check_names.add(name)

            elif type(entries) == dict:
                for k, subentries in entries.items():
                    check_entries( k, subentries )

        for key, entries in self._manpages.items():
            check_entries( key, entries )

        return collection.items()


    def _get_check_catalog(self):
        def path_prefix_matches(p, op):
            if op and not p:
                return False
            elif not op:
                return True
            else:
                return p[0] == op[0] and path_prefix_matches(p[1:], op[1:])

        def strip_manpage_entry(entry):
            return dict([ (k,v) for (k,v) in entry.items() if k in [
                "name", "agents", "title"
            ]])

        tree = {}
        if len(self._path) > 0:
            only_path = tuple(self._path)
        else:
            only_path = ()

        for path, entries in man_pages.load_man_page_catalog().items():
            if not path_prefix_matches(path, only_path):
                continue
            subtree = tree
            for component in path[:-1]:
                subtree = subtree.setdefault(component, {})
            subtree[path[-1]] = map(strip_manpage_entry, entries)

        for p in only_path:
            tree = tree[p]

        return tree


    def _render_manpage_topic(self):
        if type(self._manpages) == list:
            self._render_manpage_list(self._manpages, self._path[-1], self._topic_title)
            return

        if len(self._path) == 1 and self._has_second_level:
            # For some topics we render a second level in the same optic as the first level
            menu = MainMenu()
            for path_comp, subnode in self._manpages.items():
                url = html.makeuri([("topic", "%s/%s" % (self._path[0], path_comp))])
                title = self._titles.get(path_comp, path_comp)
                helptext = self._get_check_plugin_stats(subnode)

                menu.add_item(MenuItem(
                    mode_or_url=url,
                    title=title,
                    icon="check_plugins",
                    permission=None,
                    description=helptext,
                ))
            menu.show()

        else:
            # For the others we directly display the tables
            entries = []
            for path_comp, subnode in self._manpages.items():
                title = self._titles.get(path_comp, path_comp)
                entries.append((title, subnode, path_comp))

            entries.sort(cmp = lambda a,b: cmp(a[0].lower(), b[0].lower()))

            for title, subnode, path_comp in entries:
                self._render_manpage_list(subnode, path_comp, title)


    def _get_check_plugin_stats(self, subnode):
        if type(subnode) == list:
            num_cats = 1
            num_plugins = len(subnode)
        else:
            num_cats = len(subnode)
            num_plugins = 0
            for subcat in subnode.values():
                num_plugins += len(subcat)

        text = ""
        if num_cats > 1:
            text += "%d %s<br>" % (num_cats, _("sub categories"))
        text += "%d %s" % (num_plugins, _("check plugins"))
        return text


    def _render_manpage_list(self, manpage_list, path_comp, heading):
        def translate(t):
            return self._titles.get(t, t)

        html.h2(heading)
        table.begin(searchable=False, sortable=False, css="check_catalog")
        for entry in sorted(manpage_list, cmp=lambda a,b: cmp(a["title"], b["title"])):
            if type(entry) != dict:
                continue
            table.row()
            url = html.makeuri([("mode", "check_manpage"), ("check_type", entry["name"]), ("back", html.makeuri([]))])
            table.cell(_("Type of Check"), "<a href='%s'>%s</a>" % (url, entry["title"]), css="title")
            table.cell(_("Plugin Name"), "<tt>%s</tt>" % entry["name"], css="name")
            table.cell(_("Agents"), ", ".join(map(translate, sorted(entry["agents"]))), css="agents")
        table.end()


    def _man_page_catalog_topics(self):
        # topic, has_second_level, title, description
        return [
            ("hw", True, _("Appliances, other dedicated hardware"),
                _("Switches, load balancers, storage, UPSes, "
                  "environmental sensors, etc. ")),

            ("os", True, _("Operating systems"),
                _("Plugins for operating systems, things "
                  "like memory, CPU, filesystems, etc.")),

            ("app", False, _("Applications"),
                _("Monitoring of applications such as "
                  "processes, services or databases")),

            ("agentless", False, _("Networking checks without agent"),
                _("Plugins that directly check networking "
                  "protocols like HTTP or IMAP")),

            ("generic", False,  _("Generic check plugins"),
               _("Plugins for local agent extensions or "
                 "communication with the agent in general")),
        ]



@mode_registry.register
class ModeCheckManPage(WatoMode):
    @classmethod
    def name(cls):
        return "check_manpage"


    @classmethod
    def permissions(cls):
        return []


    def _from_vars(self):
        self._check_type = html.var("check_type")

        # TODO: There is one check "sap.value-groups" which will be renamed to "sap.value_groups".
        # As long as the old one is available, allow a minus here.
        if not re.match("^[-a-zA-Z0-9_.]+$", self._check_type):
            raise MKUserError(None, "Invalid check type")

        # TODO: remove call of automation and then the automation. This can be done once the check_info
        # data is also available in the "cmk." module because the get-check-manpage automation not only
        # fetches the man page. It also contains info from check_info. What a hack.
        self._manpage = watolib.check_mk_local_automation("get-check-manpage", [ self._check_type ])
        if self._manpage == None:
            raise MKUserError(None, _("There is no manpage for this check."))


    def title(self):
        return _("Check plugin manual page") + " - " + self._manpage["header"]["title"]


    def buttons(self):
        global_buttons()
        path = self._manpage["header"]["catalog"]

        if html.var("back"):
            back_url = html.var("back")
            html.context_button(_("Back"), back_url, "back")

        html.context_button(_("All Check Plugins"), html.makeuri_contextless([("mode", "check_plugins")]), "check_plugins")

        if self._check_type.startswith("check_"):
            command = "check_mk_active-" + self._check_type[6:]
        else:
            command = "check_mk-" + self._check_type

        url = html.makeuri_contextless([("view_name", "searchsvc"), ("check_command", command), ("filled_in", "filter")], filename="view.py")
        html.context_button(_("Find usage"), url, "status")


    # TODO
    # We could simply detect on how many hosts and services this plugin
    # is currently in use (Livestatus query) and display this information
    # together with a link for searching. Then we can remove the dumb context
    # button, that will always be shown - even if the plugin is not in use.
    def page(self):
        html.open_table(class_=["data", "headerleft"])

        html.open_tr()
        html.th(_("Title"))
        html.open_td()
        html.b(self._manpage["header"]["title"])
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Name of plugin"))
        html.open_td()
        html.tt(self._check_type)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Description"))
        html.td(self._manpage_text(self._manpage["header"]["description"]))
        html.close_tr()

        def show_ruleset(varname):
            if watolib.g_rulespecs.exists(varname):
                rulespec = watolib.g_rulespecs.get(varname)
                url = html.makeuri_contextless([("mode", "edit_ruleset"), ("varname", varname)])
                param_ruleset = html.render_a(rulespec.title, url)
                html.open_tr()
                html.th(_("Parameter rule set"))
                html.open_td()
                html.icon_button(url, _("Edit parameter rule set for this check type"), "check_parameters")
                html.write(param_ruleset)
                html.close_td()
                html.close_tr()
                html.open_tr()
                html.th(_("Example for Parameters"))
                html.open_td()
                vs = rulespec.valuespec
                vs.render_input("dummy", vs.default_value())
                html.close_td()
                html.close_tr()

        if self._manpage["type"] == "check_mk":
            html.open_tr()
            html.th(_("Service name"))
            html.td(HTML(self._manpage["service_description"].replace("%s", "&#9744;")))
            html.close_tr()

            if self._manpage.get("group"):
                group = self._manpage["group"]
                varname = "checkgroup_parameters:" + group
                show_ruleset(varname)

        else:
            varname = "active_checks:" + self._check_type[6:]
            show_ruleset(varname)

        html.close_table()


    def _manpage_text(self, text):
        html_code = text.replace("<br>", "\n")\
                        .replace("<", "&lt;")\
                        .replace(">", "&gt;")
        html_code = re.sub("{(.*?)}", "<tt>\\1</tt>", html_code)
        html_code = re.sub("\n\n+", "<p>", html_code)
        return html_code


#.
#   .--Icons---------------------------------------------------------------.
#   |                       ___                                            |
#   |                      |_ _|___ ___  _ __  ___                         |
#   |                       | |/ __/ _ \| '_ \/ __|                        |
#   |                       | | (_| (_) | | | \__ \                        |
#   |                      |___\___\___/|_| |_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

@mode_registry.register
class ModeIcons(WatoMode):
    @classmethod
    def name(cls):
        return "icons"


    @classmethod
    def permissions(cls):
        return ["icons"]


    def title(self):
        return _('Manage Icons')


    def buttons(self):
        back_url = html.var("back")
        if back_url:
            html.context_button(_("Back"), back_url, "back")
        else:
            home_button()


    def _load_custom_icons(self):
        s = IconSelector()
        return s.available_icons(only_local=True)


    def _vs_upload(self):
        return Dictionary(
            title = _('Icon'),
            optional_keys = False,
            render = "form",
            elements = [
                ('icon', ImageUpload(
                    title = _('Icon'),
                    allow_empty = False,
                    max_size = (80, 80),
                    validate = self._validate_icon,
                )),
                ('category', DropdownChoice(
                    title = _('Category'),
                    choices = config.wato_icon_categories,
                    no_preselect = True,
                ))
            ]
        )


    def _validate_icon(self, value, varprefix):
        file_name = value[0]
        if os.path.exists("%s/share/check_mk/web/htdocs/images/icon_%s" % (cmk.paths.omd_root, file_name)) \
           or os.path.exists("%s/share/check_mk/web/htdocs/images/icons/%s" % (cmk.paths.omd_root, file_name)):
            raise MKUserError(varprefix, _('Your icon conflicts with a Check_MK builtin icon. Please '
                                           'choose another name for your icon.'))


    def action(self):
        if html.has_var("_delete"):
            icon_name = html.var("_delete")
            if icon_name in self._load_custom_icons():
                c = wato_confirm(_("Confirm Icon deletion"),
                                 _("Do you really want to delete the icon <b>%s</b>?") % icon_name)
                if c:
                    os.remove("%s/local/share/check_mk/web/htdocs/images/icons/%s.png" %
                                                        (cmk.paths.omd_root, icon_name))
                elif c == False:
                    return ""
                else:
                    return

        elif html.has_var("_do_upload"):
            vs_upload = self._vs_upload()
            icon_info = vs_upload.from_html_vars('_upload_icon')
            vs_upload.validate_value(icon_info, '_upload_icon')
            self._upload_icon(icon_info)


    def _upload_icon(self, icon_info):
        # Add the icon category to the PNG comment
        from PIL import Image, PngImagePlugin
        from StringIO import StringIO
        im = Image.open(StringIO(icon_info['icon'][2]))
        im.info['Comment'] = icon_info['category']
        meta = PngImagePlugin.PngInfo()
        for k,v in im.info.iteritems():
            if isinstance(v, (str, unicode)):
                meta.add_text(k, v, 0)

        # and finally save the image
        dest_dir = "%s/local/share/check_mk/web/htdocs/images/icons" % cmk.paths.omd_root
        store.makedirs(dest_dir)
        try:
            file_name = os.path.basename(icon_info['icon'][0])
            im.save(dest_dir+'/'+file_name, 'PNG', pnginfo=meta)
        except IOError, e:
            # Might happen with interlaced PNG files and PIL version < 1.1.7
            raise MKUserError(None, _('Unable to upload icon: %s') % e)


    def page(self):
        html.h3(_("Upload Icon"))
        html.p(_("Allowed are single PNG image files with a maximum size of 80x80 px."))

        html.begin_form('upload_form', method='POST')
        self._vs_upload().render_input('_upload_icon', None)
        html.button('_do_upload', _('Upload'), 'submit')

        html.hidden_fields()
        html.end_form()

        icons = sorted(self._load_custom_icons().items())
        table.begin("icons", _("Custom Icons"))
        for icon_name, category_name in icons:
            table.row()

            table.cell(_("Actions"), css="buttons")
            delete_url = make_action_link([("mode", "icons"), ("_delete", icon_name)])
            html.icon_button(delete_url, _("Delete this Icon"), "delete")

            table.cell(_("Icon"), html.render_icon(icon_name), css="buttons")
            table.cell(_("Name"), icon_name)
            table.cell(_("Category"), IconSelector.category_alias(category_name))
        table.end()


#.
#   .--Passwords-----------------------------------------------------------.
#   |           ____                                     _                 |
#   |          |  _ \ __ _ ___ _____      _____  _ __ __| |___             |
#   |          | |_) / _` / __/ __\ \ /\ / / _ \| '__/ _` / __|            |
#   |          |  __/ (_| \__ \__ \\ V  V / (_) | | | (_| \__ \            |
#   |          |_|   \__,_|___/___/ \_/\_/ \___/|_|  \__,_|___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Store and share passwords for use in configured checks               |
#   '----------------------------------------------------------------------'




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
        for root, dirs, files in os.walk(cmk.paths.agents_dir):
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
            html.div(render.bytes(file_size), style="width:60px;", class_="rulecount")
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
    for folder_path, folder in watolib.Folder.all_folders().items():
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
        else:
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
            for host_name, host in hosts.items():
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
                    what = "folder"

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

            forms.section(_u(attr.title()), checkbox=checkbox_code, id="attr_" + attrname)
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
                tdclass, content = attr.paint(value, "")
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
        _("There are different places in Check_MK where an admin, the user of the configuration "
          "GUI, can use the GUI to add executable code to Check_MK. For example when configuring "
          "datasource programs, the user inserts a command line for gathering monitoring data. "
          "This command line is then executed during monitoring by Check_MK. Another example is "
          "the upload of extension packages (MKPs). All these functions have in "
          "common that the user provides data that is executed by Check_MK later. "
          "If you want to ensure that your WATO users can not \"inject\" arbitrary executables "
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
    "wato_ajax_profile_repl"    : lambda: ModeAjaxProfileReplication().handle_page(),

    "automation_login"          : lambda: ModeAutomationLogin().page(),
    "noauth:automation"         : lambda: ModeAutomation().page(),
    "ajax_set_foldertree"       : lambda: ModeAjaxSetFoldertree().handle_page(),
    "wato_ajax_diag_host"       : lambda: ModeAjaxDiagHost().handle_page(),
    "wato_ajax_execute_check"   : lambda: ModeAjaxExecuteCheck().handle_page(),
    "fetch_agent_output"        : lambda: PageFetchAgentOutput().page(),
    "download_agent_output"     : lambda: PageDownloadAgentOutput().page(),
    "ajax_popup_move_to_folder" : lambda: ModeAjaxPopupMoveToFolder().page(),
    "ajax_backup_job_state"     : lambda: ModeAjaxBackupJobState().page(),
}
for path, page_func in _wato_pages.items():
    cmk.gui.pages.register_page_handler(path, page_func)
