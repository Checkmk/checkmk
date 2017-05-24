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

# [2] Global variables
# At the beginning of each page some global variables are set:
#
#
# g_html_head_open -> True, if the HTML head has already been rendered.

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

import sys, pprint, socket, re, time, datetime,  \
       shutil, math, fcntl, random, glob, \
       base64, csv
import subprocess
import traceback
import i18n
import config, table, multitar, userdb, weblib, login
from hashlib import sha256
from lib import *
from log import logger
from valuespec import *
import forms
import backup
import modules as multisite_modules
from watolib import *

import cmk.paths
import cmk.store as store
import cmk.man_pages as man_pages
from cmk.regex import escape_regex_chars, regex
from cmk.defines import short_service_state_name
import cmk.render as render

if cmk.is_managed_edition():
    import managed
else:
    managed = None


try:
    import simplejson as json
except ImportError:
    import json

g_html_head_open = False
display_options  = None

wato_styles = [ "pages", "wato", "status" ]

# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock=False):
    if with_wato_lock:
        lock_exclusive()

    create_sample_config()
    init_watolib_datastructures()

    if with_wato_lock:
        unlock_exclusive()


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

def page_handler():
    global g_html_head_open
    g_html_head_open = False

    if not config.wato_enabled:
        raise MKGeneralException(_("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
                                   " in your <tt>multisite.mk</tt> if you want to use WATO."))

    if cmk.is_managed_edition() and not managed.is_provider(config.current_customer):
        raise MKGeneralException(_("Check_MK can only be configured on "
                                   "the managers central site."))

    current_mode = html.var("mode") or "main"
    modeperms, modefunc = get_mode_function(current_mode)

    weblib.prepare_display_options(globals())

    if display_options.disabled(display_options.N):
        html.add_body_css_class("inline")

    # If we do an action, we aquire an exclusive lock on the complete
    # WATO.
    if html.is_transaction():
        lock_exclusive()

    try:
        init_wato_datastructures(with_wato_lock=not html.is_transaction())
    except:
        # Snapshot must work in any case
        if current_mode == 'snapshot':
            pass
        else:
            raise

    if modefunc == None:
        html.header(_("Sorry"), stylesheets=wato_styles,
                    show_body_start=display_options.enabled(display_options.H),
                    show_top_heading=display_options.enabled(display_options.T))

        if display_options.enabled(display_options.B):
            html.begin_context_buttons()
            home_button()
            html.end_context_buttons()

        html.message(_("This module has not yet been implemented."))

        html.footer(display_options.enabled(display_options.Z),
                    display_options.enabled(display_options.H))
        return

    # Check general permission for this mode
    if modeperms != None and not config.user.may("wato.seeall"):
        ensure_mode_permissions(modeperms)

    # Do actions (might switch mode)
    action_message = None
    if html.is_transaction():
        try:
            config.user.need_permission("wato.edit")

            # Even if the user has seen this mode because auf "seeall",
            # he needs an explicit access permission for doing changes:
            if config.user.may("wato.seeall"):
                if modeperms:
                    ensure_mode_permissions(modeperms)

            if is_read_only_mode_enabled() and not may_override_read_only_mode():
                raise MKUserError(None, read_only_message())

            result = modefunc("action")
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
                    if g_html_head_open:
                        html.close_div()
                        html.footer()
                    return
                modeperms, modefunc = get_mode_function(newmode)
                current_mode = newmode
                html.set_var("mode", newmode) # will be used by makeuri

                # Check general permissions for the new mode
                if modeperms != None and not config.user.may("wato.seeall"):
                    for pname in modeperms:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.user.need_permission(pname)

        except MKUserError, e:
            action_message = "%s" % e
            html.add_user_error(e.varname, action_message)

        except MKAuthException, e:
            action_message = e.reason
            html.add_user_error(None, e.reason)

    # Title
    html.header(modefunc("title"), javascripts=["wato"], stylesheets=wato_styles,
                show_body_start=display_options.enabled(display_options.H),
                show_top_heading=display_options.enabled(display_options.T))
    html.open_div(class_="wato")

    try:
        if display_options.enabled(display_options.B):
            # Show contexts buttons
            html.begin_context_buttons()
            modefunc("buttons")
            for inmode, buttontext, target in extra_buttons:
                if inmode == current_mode:
                    if hasattr(target, '__call__'):
                        target = target()
                        if not target:
                            continue
                    if '/' == target[0] or target.startswith('../') or '://' in target:
                        html.context_button(buttontext, target)
                    else:
                        html.context_button(buttontext, folder_preserving_link([("mode", target)]))
            html.end_context_buttons()

        if not html.is_transaction() or (is_read_only_mode_enabled() and may_override_read_only_mode()):
            show_read_only_warning()

        # Show outcome of action
        if html.has_user_errors():
            html.show_error(action_message)
        elif action_message:
            html.message(action_message)

        # Show content
        modefunc("content")

    except MKGeneralException:
        raise

    except MKInternalError:
        html.unplug()
        raise

    except MKAuthException:
        raise

    except Exception, e:
        html.unplug()
        html.show_error(traceback.format_exc().replace('\n', '<br />'))

    html.close_div()
    if is_sidebar_reload_needed():
        html.reload_sidebar()

    if config.wato_use_git and html.is_transaction():
        do_git_commit()

    html.footer(display_options.enabled(display_options.Z),
                display_options.enabled(display_options.H))


def get_mode_function(mode):
    modeperms, modefunc = modes.get(mode, ([], None))
    if modefunc == None:
        raise MKGeneralException(_("No such WATO module '<tt>%s</tt>'") % html.attrencode(mode))

    if type(modefunc) != type(lambda: None):
        mode_class = modefunc
        modefunc = mode_class.create_mode_function()

    if modeperms != None and not config.user.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    return modeperms, modefunc


def ensure_mode_permissions(modeperms):
    for pname in modeperms:
        if '.' not in pname:
            pname = "wato." + pname
        config.user.need_permission(pname)


class WatoMode(object):
    def __init__(self):
        super(WatoMode, self).__init__()


    @classmethod
    def create_mode_function(cls):
        mode_object = cls()
        def mode_function(phase):
            if phase == "title":
                return mode_object.title()
            elif phase == "buttons":
                return mode_object.buttons()
            elif phase == "action":
                return mode_object.action()
            else:
                return mode_object.handle_page()
        return mode_function


    def title(self):
        return _("(Untitled module)")


    def buttons(self):
        global_buttons()


    def action(self):
        pass


    def page(self):
        return _("(This module is not yet implemented)")


    def handle_page(self):
        return self.page()



class WatoWebApiMode(WatoMode):
    def webapi_request(self):
        return html.get_request()


    def handle_page(self):
        try:
            action_response = self.page()
            response = { "result_code": 0, "result": action_response }
        except MKException, e:
            response = { "result_code": 1, "result": "%s" % e }

        except Exception, e:
            if config.debug:
                raise
            log_exception()
            response = { "result_code": 1, "result": "%s" % e }

        html.write(json.dumps(response))


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

def mode_folder(phase):
    folder = Folder.current()

    if phase == "title":
        return folder.title()

    elif phase == "buttons":
        global_buttons()
        if folder.is_disk_folder():
            if config.user.may("wato.rulesets") or config.user.may("wato.seeall"):
                html.context_button(_("Rulesets"),        folder_preserving_link([("mode", "ruleeditor")]), "rulesets")
                html.context_button(_("Manual Checks"),   folder_preserving_link([("mode", "static_checks")]), "static_checks")
            if folder.may("read"):
                html.context_button(_("Folder Properties"), folder.edit_url(backfolder=folder), "edit")
            if not folder.locked_subfolders() and config.user.may("wato.manage_folders") and folder.may("write"):
                html.context_button(_("New folder"),        folder.url([("mode", "newfolder")]), "newfolder")
            if not folder.locked_hosts() and config.user.may("wato.manage_hosts") and folder.may("write"):
                html.context_button(_("New host"),    folder.url([("mode", "newhost")]), "new")
                html.context_button(_("New cluster"), folder.url([("mode", "newcluster")]), "new_cluster")
                html.context_button(_("Bulk import"), folder.url([("mode", "bulk_import")]), "bulk_import")
            if config.user.may("wato.services"):
                html.context_button(_("Bulk discovery"), folder.url([("mode", "bulkinventory"), ("all", "1")]),
                            "inventory")
            if config.user.may("wato.rename_hosts"):
                html.context_button(_("Bulk renaming"), folder.url([("mode", "bulk_rename_host")]), "rename_host")
            html.context_button(_("Custom attributes"), folder_preserving_link([("mode", "host_attrs")]), "custom_attr")
            if not folder.locked_hosts() and config.user.may("wato.parentscan") and folder.may("write"):
                html.context_button(_("Parent scan"), folder.url([("mode", "parentscan"), ("all", "1")]),
                            "parentscan")
            folder_status_button()
            if config.user.may("wato.random_hosts"):
                html.context_button(_("Random Hosts"), folder.url([("mode", "random_hosts")]), "random")
            html.context_button(_("Search"), folder_preserving_link([("mode", "search")]), "search")
        else:
            html.context_button(_("Back"), folder.parent().url(), "back")
            html.context_button(_("Refine Search"), folder.url([("mode", "search")]), "search")


    elif phase == "action":
        if html.var("_search"): # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.var("_delete_folder"):
            if html.transaction_valid():
                return delete_subfolder_after_confirm(folder, html.var("_delete_folder"))
            return

        elif html.has_var("_move_folder_to"):
            if html.check_transaction():
                what_folder = Folder.folder(html.var("_ident"))
                target_folder = Folder.folder(html.var("_move_folder_to"))
                Folder.current().move_subfolder_to(what_folder, target_folder)
            return


        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.var("_delete_host")
        if delname and Folder.current().has_host(delname):
            return delete_host_after_confirm(delname)

        # Move single hosts to other folders
        if html.has_var("_move_host_to"):
            hostname = html.var("_ident")
            if hostname:
                target_folder = Folder.folder(html.var("_move_host_to"))
                Folder.current().move_hosts([hostname], target_folder)
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
            return delete_hosts_after_confirm(selected_host_names)

        # Move
        elif html.var("_bulk_move"):
            target_folder_path = html.var("bulk_moveto", html.var("_top_bulk_moveto"))
            if target_folder_path == "@":
                raise MKUserError("bulk_moveto", _("Please select the destination folder"))
            target_folder = Folder.folder(target_folder_path)
            Folder.current().move_hosts(selected_host_names, target_folder)
            return None, _("Moved %d hosts to %s") % (len(selected_host_names), target_folder.title())

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
            return move_to_imported_folders(selected_host_names)

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"

    else:
        folder.show_breadcrump()

        if not folder.may("read"):
            html.message(HTML('<img class=authicon src="images/icon_autherr.png"> %s' % html.attrencode(folder.reason_why_may_not("read"))))

        folder.show_locking_information()
        show_subfolders_of(folder)
        if folder.may("read"):
            show_hosts(folder)

        if not folder.has_hosts():
            if folder.is_search_folder():
                html.message(_("No matching hosts found."))
            elif not folder.has_subfolders() and folder.may("write"):
                show_empty_folder_menu(folder)


def delete_subfolder_after_confirm(folder, subfolder_name):
    subfolder = folder.subfolder(subfolder_name)
    msg = _("Do you really want to delete the folder %s?") % subfolder.title()
    if not config.wato_hide_filenames:
        msg += _(" Its directory is <tt>%s</tt>.") % subfolder.filesystem_path()
    num_hosts = subfolder.num_hosts_recursively()
    if num_hosts:
        msg += _(" The folder contains <b>%d</b> hosts, which will also be deleted!") % num_hosts
    c = wato_confirm(_("Confirm folder deletion"), msg)

    if c:
        folder.delete_subfolder(subfolder_name)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload


def show_empty_folder_menu(folder):
    menu_items = []
    if not folder.locked_hosts():
        menu_items.extend([
        ("newhost", _("Create new host"), "new", "hosts",
          _("Add a new host to the monitoring (agent must be installed)")),
        ("newcluster", _("Create new cluster"), "new_cluster", "hosts",
          _("Use Check_MK clusters if an item can move from one host "
            "to another at runtime"))])
    if not folder.locked_subfolders():
        menu_items.extend([
        ("newfolder", _("Create new folder"), "newfolder", "hosts",
          _("Folders group your hosts, can inherit attributes and can have permissions."))
        ])
    render_main_menu(menu_items)



def show_subfolders_of(folder):
    if folder.has_subfolders():
        html.open_div(class_="folders") # This won't hurt even if there are no visible subfolders
        for subfolder in folder.visible_subfolders_sorted_by_title():
            show_subfolder(subfolder)
        html.close_div()
        html.div('', class_="folder_foot")


def show_subfolder(subfolder):
    html.open_div(class_=["floatfolder", "unlocked" if subfolder.may("read") else "locked"],
                  id_="folder_%s" % subfolder.name(),
                  onclick="wato_open_folder(event, \'%s\');" % subfolder.url())
    show_subfolder_hoverarea(subfolder)
    show_subfolder_infos(subfolder)
    show_subfolder_title(subfolder)
    html.close_div() # floatfolder


def show_subfolder_hoverarea(subfolder):
    # Only make folder openable when permitted to edit
    if subfolder.may("read"):
        html.open_div(class_="hoverarea", onmouseover="wato_toggle_folder(event, this, true);",
                                          onmouseout="wato_toggle_folder(event, this, false);")
        show_subfolder_buttons(subfolder)
        html.close_div() # hoverarea
    else:
        html.img("images/icon_autherr.png", class_=["icon", "autherr"],
                 title=html.strip_tags(subfolder.reason_why_may_not("read")))
        html.div('', class_="hoverarea")


def show_subfolder_title(subfolder):
    title = subfolder.title()
    if not config.wato_hide_filenames:
        title += ' (%s)' % subfolder.name()

    html.open_div(class_="title", title=title)
    if subfolder.may("read"):
        html.a(subfolder.title(), href=subfolder.url())
    else:
        html.write_text(subfolder.title())
    html.close_div()


def show_subfolder_buttons(subfolder):
    show_subfolder_edit_button(subfolder)

    if not subfolder.locked_subfolders() and not subfolder.locked():
        if subfolder.may("write") and config.user.may("wato.manage_folders"):
            show_move_to_folder_action(subfolder)
            show_subfolder_delete_button(subfolder)


def show_subfolder_edit_button(subfolder):
    html.icon_button(
        subfolder.edit_url(subfolder.parent()),
        _("Edit the properties of this folder"),
        "edit",
        id = 'edit_' + subfolder.name(),
        cssclass = 'edit',
        style = 'display:none',
    )


def show_subfolder_delete_button(subfolder):
    html.icon_button(
        make_action_link([("mode", "folder"), ("_delete_folder", subfolder.name())]),
        _("Delete this folder"),
        "delete",
        id = 'delete_' + subfolder.name(),
        cssclass = 'delete',
        style = 'display:none',
    )


def show_subfolder_infos(subfolder):
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


def show_hosts(folder):
    if not folder.has_hosts():
        return

    show_checkboxes = html.var('show_checkboxes', '0') == '1'

    hostnames = folder.hosts().keys()
    hostnames.sort(cmp = lambda a, b: cmp(num_split(a), num_split(b)))
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
            html.text_input(top and "search" or "search")
            html.button("_search", _("Search"))
            html.set_focus("search")
        table.cell(css="bulkactions", colspan=colspan-3)
        html.write_text(' ' + _("Selected hosts:\n"))

        if not folder.locked_hosts():
            if config.user.may("wato.manage_hosts"):
                html.button("_bulk_delete", _("Delete"))
            if config.user.may("wato.edit_hosts"):
                html.button("_bulk_edit", _("Edit"))
                html.button("_bulk_cleanup", _("Cleanup"))
        if config.user.may("wato.services"):
            html.button("_bulk_inventory", _("Discovery"))
        if not folder.locked_hosts():
            if config.user.may("wato.parentscan"):
                html.button("_parentscan", _("Parentscan"))
            if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
                host_bulk_move_to_folder_combo(folder, top)
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

        host = folder.host(hostname)
        effective = host.effective_attributes()

        if effective.get("imported_folder"):
            at_least_one_imported = True

        if num == 11:
            more_than_ten_items = True


    # Compute colspan for bulk actions
    colspan = 6
    for attr, topic in all_host_attributes():
        if attr.show_in_table():
            colspan += 1
    if not folder.locked_hosts() and config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
        colspan += 1
    if show_checkboxes:
        colspan += 1
    if folder.is_search_folder():
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
        return '<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' % (c, display_name)

    host_errors = folder.host_validation_errors()
    rendered_hosts = []

    # Now loop again over all hosts and display them
    for hostname in hostnames:
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        host = folder.host(hostname)
        rendered_hosts.append(hostname)
        effective = host.effective_attributes()

        table.row()

        # Column with actions (buttons)

        if show_checkboxes:
            table.cell("<input type=button class=checkgroup name=_toggle_group"
                       " onclick=\"toggle_all_rows();\" value=\"X\" />", sortable=False)
            # Use CSS class "failed" in order to provide information about
            # selective toggling inventory-failed hosts for Javascript
            html.input(name="_c_%s" % hostname, type_="checkbox", value=colspan,
                       class_="failed" if host.discovery_failed() else None)
            html.label("", "_c_%s" % hostname)

        table.cell(_("Actions"), css="buttons", sortable=False)
        show_host_actions(host)

        # Hostname with link to details page (edit host)
        table.cell(_("Hostname"))
        errors = host_errors.get(hostname,[]) + host.validation_errors()
        if errors:
            msg = _("Warning: This host has an invalid configuration: ")
            msg += ", ".join(errors)
            html.icon(msg, "validation_error")
            html.write("&nbsp;")

        if host.is_offline():
            html.icon(_("This host is disabled"), "disabled")
            html.write("&nbsp;")

        if host.is_cluster():
            html.icon(_("This host is a cluster of %s") % ", ".join(host.cluster_nodes()), "cluster")
            html.write("&nbsp;")

        html.a(hostname, href=host.edit_url())

        # Show attributes
        for attr, topic in all_host_attributes():
            if attr.show_in_table():
                attrname = attr.name()
                if attrname in host.attributes():
                    tdclass, tdcontent = attr.paint(host.attributes()[attrname], hostname)
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                table.cell(attr.title(), tdcontent, css=tdclass)

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
        table.cell(_("Permissions"), ", ".join(map(render_contact_group, permitted_groups)))
        table.cell(_("Contact Groups"), ", ".join(map(render_contact_group, host_contact_groups)))

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
        if folder.is_search_folder():
            table.cell(_("Folder"))
            html.a(host.folder().alias_path(), href=host.folder().url())

    if config.user.may("wato.edit_hosts") or config.user.may("wato.manage_hosts"):
        bulk_actions(at_least_one_imported, False, not search_shown, colspan, show_checkboxes)

    table.end()
    html.hidden_fields()
    html.end_form()

    selected = weblib.get_rowselection('wato-folder-/' + folder.path())

    row_count = len(rendered_hosts)
    headinfo = "%d %s" % (row_count, row_count == 1 and _("host") or _("hosts"))
    html.javascript("update_headinfo('%s');" % headinfo)

    if show_checkboxes:
        html.javascript(
            'g_page_id = "wato-folder-%s";\n'
            'g_selection = "%s";\n'
            'g_selected_rows = %s;\n'
            'init_rowselect();' % ('/' + folder.path(), weblib.selection_id(), json.dumps(selected))
        )


def show_host_actions(host):
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
        if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
            show_move_to_folder_action(host)

        if config.user.may("wato.manage_hosts"):
            if config.user.may("wato.clone_hosts"):
                html.icon_button(host.clone_url(), _("Create a clone of this host"), "insert")
            delete_url  = make_action_link([("mode", "folder"), ("_delete_host", host.name())])
            html.icon_button(delete_url, _("Delete this host"), "delete")


def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        Folder.current().delete_hosts([delname])
        # Delete host files
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload


def delete_hosts_after_confirm(host_names):
    c = wato_confirm(_("Confirm deletion of %d hosts") % len(host_names),
                     _("Do you really want to delete the %d selected hosts?") % len(host_names))
    if c:
        Folder.current().delete_hosts(host_names)
        return "folder", _("Successfully deleted %d hosts") % len(host_names)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload


# Create list of all hosts that are select with checkboxes in the current file.
# This is needed for bulk operations.
def get_hostnames_from_checkboxes(filterfunc = None):
    show_checkboxes = html.var("show_checkboxes") == "1"
    if show_checkboxes:
        selected = weblib.get_rowselection('wato-folder-/' + Folder.current().path())
    search_text = html.var("search")

    selected_host_names = []
    for host_name, host in sorted(Folder.current().hosts().items()):
        if (not search_text or (search_text.lower() in host_name.lower())) \
            and (not show_checkboxes or ('_c_' + host_name) in selected):
                if filterfunc == None or \
                   filterfunc(host):
                    selected_host_names.append(host_name)
    return selected_host_names


def get_hosts_from_checkboxes(filterfunc = None):
    folder = Folder.current()
    return [ folder.host(host_name) for host_name in get_hostnames_from_checkboxes(filterfunc) ]


def show_move_to_folder_action(obj):
    if isinstance(obj, Host):
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


# Renders the popup menu contents for either moving a host or a folder to another folder
def ajax_popup_move_to_folder():
    what     = html.var("what")
    ident    = html.var("ident")
    back_url = html.var("back_url")

    if what == "host":
        what_title = _("host")
        obj = Host.host(ident)
        choices = obj.folder().choices_for_moving_host()

    elif what == "folder":
        what_title = _("folder")
        obj = Folder.folder(ident)
        choices = obj.choices_for_moving_folder()

    else:
        return

    if not back_url or not back_url.startswith("wato.py"):
        raise MKUserError("back_url", _("Invalid back URL provided."))

    html.span(_('Move this %s to:') % what_title)

    if choices:
        choices = [("@", _("(select target folder)"))] + choices
        html.select("_host_move_%s" % ident, choices, "@",
            "location.href='%s&_ident=%s&_move_%s_to=' + this.value;" % (back_url, ident, what),
            attrs={'size': '10'})
    else:
        html.write_text(_("No valid target folder."))


# FIXME: Cleanup
def host_bulk_move_to_folder_combo(folder, top):
    choices = folder.choices_for_moving_host()
    if len(choices):
        choices = [("@", _("(select target folder)"))] + choices
        html.button("_bulk_move", _("Move:"))
        field_name = 'bulk_moveto'
        if top:
            field_name = '_top_bulk_moveto'
            if html.has_var('bulk_moveto'):
                html.javascript('update_bulk_moveto("%s")' % html.var('bulk_moveto', ''))
        html.select(field_name, choices, "@",
                     onchange = "update_bulk_moveto(this.value)",
                     attrs = {'class': 'bulk_moveto'})
    else:
        html.write_text(_("No valid target folder."))


def move_to_imported_folders(host_names_to_move):
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
        host = Folder.current().host(host_name)
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
        target_folder = create_target_folder_from_aliaspath(imported_folder)
        Folder.current().move_hosts(host_names, target_folder)

    return None, _("Successfully moved hosts to their original folder destinations.")


def create_target_folder_from_aliaspath(aliaspath):
    # The alias path is a '/' separated path of folder titles.
    # An empty path is interpreted as root path. The actual file
    # name is the host list with the name "Hosts".
    if aliaspath == "" or aliaspath == "/":
        folder = Folder.root_folder()
    else:
        parts = aliaspath.strip("/").split("/")
        folder = Folder.root_folder()
        while len(parts) > 0:
            # Look in current folder for subfolder with the target name
            subfolder = folder.subfolder_by_title(parts[0])
            if subfolder:
                folder = subfolder
            else:
                name = create_wato_foldername(parts[0], folder)
                folder = folder.create_subfolder(name, parts[0], {})
            parts = parts[1:]

    return folder

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

def mode_editfolder(phase, new):
    if new:
        page_title = _("Create new folder")
        name, title = None, None
    else:
        page_title = _("Folder Properties")
        name  = Folder.current().name()
        title = Folder.current().title()


    if phase == "title":
        return page_title


    elif phase == "buttons":
        if html.has_var("backfolder"):
            back_folder = Folder.folder(html.var("backfolder"))
        else:
            back_folder = Folder.current()
        html.context_button(_("Back"), back_folder.url(), "back")


    elif phase == "action":
        if not html.check_transaction():
            return "folder"

        # Title
        title = TextUnicode().from_html_vars("title")
        TextUnicode(allow_empty = False).validate_value(title, "title")
        title_changed = not new and title != Folder.current().title()

        # OS filename
        if new:
            if not config.wato_hide_filenames:
                name = html.var("name", "").strip()
                check_wato_foldername("name", name)
            else:
                name = create_wato_foldername(title)

        attributes = collect_attributes("folder")
        if new:
            Folder.current().create_subfolder(name, title, attributes)
        else:
            Folder.current().edit(title, attributes)

        # Edit icon on subfolder preview should bring user back to parent folder
        if html.has_var("backfolder"):
            Folder.set_current(Folder.folder(html.var("backfolder")))
        return "folder"


    else:
        Folder.current().show_breadcrump()
        Folder.current().need_permission("read")

        if not new and Folder.current().locked():
            Folder.current().show_locking_information()

        html.begin_form("edit_host", method = "POST")

        # title
        forms.header(_("Title"))
        forms.section()
        TextUnicode().render_input("title", title)
        html.set_focus("title")

        # folder name (omit this for root folder)
        if new or not Folder.current().is_root():
            if not config.wato_hide_filenames:
                forms.section(_("Internal directory name"))
                if new:
                    html.text_input("name")
                else:
                    html.write_text(name)
                html.help(_("This is the name of subdirectory where the files and "
                    "other folders will be created. You cannot change this later."))

        # Attributes inherited to hosts
        if new:
            attributes = {}
            parent = Folder.current()
            myself = None
        else:
            attributes = Folder.current().attributes()
            parent = Folder.current().parent()
            myself = Folder.current()

        configure_attributes(new, {"folder": myself}, "folder", parent, myself)

        forms.end()
        if new or not Folder.current().locked():
            html.button("save", _("Save & Finish"), "submit")
        html.hidden_fields()
        html.end_form()


def ajax_set_foldertree():
    config.user.save_file("foldertree", (html.var('topic'), html.var('target')))


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

def mode_edit_host(phase, new, is_cluster):
    hostname = html.var("host") # may be empty in new/clone mode
    clonename = html.var("clone")

    # clone
    if clonename:
        if not Folder.current().has_host(clonename):
            raise MKGeneralException(_("You called this page with an invalid host name."))

        if not config.user.may("wato.clone_hosts"):
            raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))

        mode = "clone"
        title = _("Create clone of %s") % clonename
        host = Folder.current().host(clonename)
        is_cluster = host.is_cluster()

    # edit
    elif not new:
        if not Folder.current().has_host(hostname):
            raise MKGeneralException(_("You called this page with an invalid host name."))

        mode = "edit"
        title = _("Properties of host") + " " + hostname
        host = Folder.current().host(hostname)
        is_cluster = host.is_cluster()

    # new
    else:
        mode = "new"
        if is_cluster:
            title = _("Create new cluster")
        else:
            title = _("Create new host")
        host = None


    if phase == "title":
        return title


    elif phase == "buttons":
        html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        if mode == "edit":
            host_status_button(hostname, "hoststatus")

            html.context_button(_("Services"),
                  folder_preserving_link([("mode", "inventory"), ("host", hostname)]), "services")
            if config.user.may('wato.agents'):
                html.context_button(_("Monitoring Agent"),
                  folder_preserving_link([("mode", "agent_of_host"), ("host", hostname)]), "agents")
            if config.user.may('wato.rulesets'):
                html.context_button(_("Parameters"),
                  folder_preserving_link([("mode", "object_parameters"), ("host", hostname)]), "rulesets")
                if is_cluster:
                    html.context_button(_("Clustered Services"),
                      folder_preserving_link([("mode", "edit_ruleset"), ("varname", "clustered_services")]), "rulesets")

            if not Folder.current().locked_hosts():
                if config.user.may("wato.rename_hosts"):
                    html.context_button(is_cluster and _("Rename cluster") or _("Rename host"),
                      folder_preserving_link([("mode", "rename_host"), ("host", hostname)]), "rename_host")
                html.context_button(is_cluster and _("Delete cluster") or _("Delete host"),
                      html.makeactionuri([("delete", "1")]), "delete")

            if not is_cluster:
                html.context_button(_("Diagnostic"),
                      folder_preserving_link([("mode", "diag_host"), ("host", hostname)]), "diagnose")
            html.context_button(_("Update DNS Cache"),
                      html.makeactionuri([("_update_dns_cache", "1")]), "update")
        return


    elif phase == "action":
        if html.var("_update_dns_cache"):
            if html.check_transaction():
                config.user.need_permission("wato.update_dns_cache")
                num_updated, failed_hosts = check_mk_automation(host.site_id(), "update-dns-cache", [])
                infotext = _("Successfully updated IP addresses of %d hosts.") % num_updated
                if failed_hosts:
                    infotext += "<br><br><b>Hostnames failed to lookup:</b> " + ", ".join(["<tt>%s</tt>" % h for h in failed_hosts])
                return None, infotext
            else:
                return None


        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_host_after_confirm(hostname)

        return action_edit_host(mode, hostname, is_cluster)


    # Show outcome of host validation. Do not validate new hosts
    errors = None
    if new:
        Folder.current().show_breadcrump()
    else:
        errors = validate_all_hosts([hostname]).get(hostname, []) + host.validation_errors()

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
        html.close_ul
        html.close_p()

        if html.form_submitted():
            html.br()
            html.b(_("Your changes have been saved nevertheless."))
        html.close_td()

        html.close_tr()
        html.close_table()
        html.close_div()

    lock_message = ""
    if Folder.current().locked_hosts():
        if Folder.current().locked_hosts() == True:
            lock_message = _("Host attributes locked (You cannot edit this host)")
        else:
            lock_message = Folder.current().locked_hosts()
    if len(lock_message) > 0:
        html.div(lock_message, class_="info")

    html.begin_form("edit_host", method="POST")
    html.prevent_password_auto_completion()

    # host name
    forms.header(_("General Properties"))
    if hostname and mode == "edit":
        forms.section(_("Hostname"), simple=True)
        html.write_text(hostname)
    else:
        forms.section(_("Hostname"))
        Hostname().render_input("host", "")
        html.set_focus("host")

    # Cluster: nodes
    if is_cluster:
        forms.section(_("Nodes"))
        vs_cluster_nodes().render_input("nodes", host and host.cluster_nodes() or [])
        html.help(_('Enter the host names of the cluster nodes. These '
                   'hosts must be present in WATO. '))

    configure_attributes(new, {hostname: host}, "host" if not is_cluster else "cluster",
                         parent = Folder.current())

    forms.end()
    if not Folder.current().locked_hosts():
        html.button("services", _("Save & go to Services"), "submit")
        html.button("save", _("Save & Finish"), "submit")
        if not is_cluster:
            html.button("diag_host", _("Save & Test"), "submit")
    html.hidden_fields()
    html.end_form()


def vs_cluster_nodes():
    return ListOfStrings(
        valuespec = TextAscii(size = 19),
        orientation = "horizontal",
    )


# Called by mode_edit_host() for new/clone/edit
def action_edit_host(mode, hostname, is_cluster):
    attributes = collect_attributes("host" if not is_cluster else "cluster")

    if is_cluster:
        cluster_nodes = vs_cluster_nodes().from_html_vars("nodes")
        vs_cluster_nodes().validate_value(cluster_nodes, "nodes")
        if len(cluster_nodes) < 1:
            raise MKUserError("nodes_0", _("The cluster must have at least one node"))
        for nr, cluster_node in enumerate(cluster_nodes):
            if cluster_node == hostname:
                raise MKUserError("nodes_%d" % nr, _("The cluster can not be a node of it's own"))

            if not Host.host_exists(cluster_node):
                raise MKUserError("nodes_%d" % nr, _("The node <b>%s</b> does not exist "
                                  " (must be a host that is configured with WATO)") % cluster_node)
    else:
        cluster_nodes = None

    if mode != "edit" and not html.transaction_valid():
        return "folder"

    if mode != "edit":
        Hostname().validate_value(hostname, "host")

    if html.check_transaction():
        if mode == "edit":
            Host.host(hostname).edit(attributes, cluster_nodes)
        else:
            Folder.current().create_hosts([(hostname, attributes, cluster_nodes)])

    host = Folder.current().host(hostname)

    go_to_services = html.var("services")
    go_to_diag     = html.var("diag_host")


    if mode != "edit": # new/clone
        if host.tag('agent') != 'ping':
            create_msg = _('Successfully created the host. Now you should do a '
                           '<a href="%s">service discovery</a> in order to auto-configure '
                           'all services to be checked on this host.') % \
                            folder_preserving_link([("mode", "inventory"), ("host", hostname)])
        else:
            create_msg = None


        if go_to_services:
            return "inventory"
        elif go_to_diag:
            html.set_var("_try", "1")
            return "diag_host", create_msg
        else:
            return "folder", create_msg

    else:
        if go_to_services:
            return "inventory"
        elif go_to_diag:
            html.set_var("_try", "1")
            return "diag_host"
        else:
            return "folder"


def check_new_host_name(varname, host_name):
    if not host_name:
        raise MKUserError(varname, _("Please specify a host name."))
    elif Folder.current().has_host(host_name):
        raise MKUserError(varname, _("A host with this name already exists in this folder."))
    validate_host_uniqueness(varname, host_name)
    Hostname().validate_value(host_name, varname)


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

def mode_bulk_rename_host(phase):

    if not config.user.may("wato.rename_hosts"):
        raise MKGeneralException(_("You don't have the right to rename hosts"))

    if phase == "title":
        return _("Bulk renaming of hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        renaming_config = HostnameRenamingConfig().from_html_vars("")
        HostnameRenamingConfig().validate_value(renaming_config, "")
        renamings = collect_host_renamings(renaming_config)

        if not renamings:
            return None, _("No matching host names")

        warning = renaming_collision_error(renamings)
        if warning:
            return None, warning


        message = _("<b>Do you really want to rename to following hosts? This involves a restart of the monitoring core!</b>")
        message += "<table>"
        for folder, host_name, target_name in renamings:
            message += u"<tr><td>%s</td><td> → %s</td></tr>" % (host_name, target_name)
        message += "</table>"

        c = wato_confirm(_("Confirm renaming of %d hosts") % len(renamings), HTML(message))
        if c:
            actions, auth_problems = rename_hosts(renamings) # Already activates the changes!
            confirm_all_local_changes() # All activated by the underlying rename automation
            action_txt =  "".join([ "<li>%s</li>" % a for a in actions ])
            message = _("Renamed %d hosts at the following places:<br><ul>%s</ul>") % (len(renamings), action_txt)
            if auth_problems:
                message += _("The following hosts could not be renamed because of missing permissions: %s") % ", ".join([
                    "%s (%s)" % (host_name, reason) for (host_name, reason) in auth_problems
                ])
            return "folder", HTML(message)
        elif c == False: # not yet confirmed
            return ""
        else:
            return None # browser reload

    else:
        html.begin_form("bulk_rename_host", method = "POST")
        HostnameRenamingConfig().render_input("", {})
        html.button("_start", _("Bulk Rename"))
        html.hidden_fields()
        html.end_form()


def renaming_collision_error(renamings):
    name_collisions = set()
    new_names = [ new_name for (folder, old_name, new_name) in renamings ]
    all_host_names = Host.all().keys()
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

    return None


def collect_host_renamings(renaming_config):
    return recurse_hosts_for_renaming(Folder.current(), renaming_config)


def recurse_hosts_for_renaming(folder, renaming_config):
    entries = []
    for host_name, host in folder.hosts().items():
        target_name = host_renamed_into(host_name, renaming_config)
        if target_name and host.may("write"):
            entries.append((folder, host_name, target_name))
    if renaming_config["recurse"]:
        for subfolder in folder.all_subfolders().values():
            entries += recurse_hosts_for_renaming(subfolder, renaming_config)
    return entries


def host_renamed_into(hostname, renaming_config):
    prefix_regex = regex(renaming_config["match_hostname"])
    if not prefix_regex.match(hostname):
        return None

    new_hostname = hostname
    for operation in renaming_config["renamings"]:
        new_hostname = host_renaming_operation(operation, new_hostname)

    if new_hostname != hostname:
        return new_hostname
    else:
        return None

def host_renaming_operation(operation, hostname):
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



def HostnameRenamingConfig():
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
                  HostnameRenaming(),
                  title = _("Renaming Operations"),
                  add_label = _("Add renaming"),
                  allow_empty = False,
            )),
        ],
        optional_keys = [],
    )

def HostnameRenaming(**kwargs):
    help = kwargs.get("help")
    title = kwargs.get("title")
    return CascadingDropdown(
        title = title,
        help = help,
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


def mode_rename_host(phase):
    host_name = html.var("host")

    if not Folder.current().has_host(host_name):
        raise MKGeneralException(_("You called this page with an invalid host name."))

    if not config.user.may("wato.rename_hosts"):
        raise MKGeneralException(_("You don't have the right to rename hosts"))


    host = Folder.current().host(host_name)
    host.need_permission("write")


    if phase == "title":
        return _("Rename %s %s") % (host.is_cluster() and _("Cluster") or _("Host"), host_name)

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Host Properties"), host.edit_url(), "back")
        return

    elif phase == "action":
        if get_number_of_pending_changes():
            raise MKUserError("newname", _("You cannot rename a host while you have pending changes."))

        newname = html.var("newname")
        check_new_host_name("newname", newname)
        c = wato_confirm(_("Confirm renaming of host"),
                         _("Are you sure you want to rename the host <b>%s</b> into <b>%s</b>? "
                           "This involves a restart of the monitoring core!") %
                         (host_name, newname))
        if c:
            # Creating pending entry. That makes the site dirty and that will force a sync of
            # the config to that site before the automation is being done.
            actions, auth_problems = rename_hosts([(Folder.current(), host.name(), newname)])
            confirm_all_local_changes() # All activated by the underlying rename automation
            html.set_var("host", newname)
            action_txt =  "".join([ "<li>%s</li>" % a for a in actions ])
            return "edit_host", HTML(_("Renamed host <b>%s</b> into <b>%s</b> at the following places:<br><ul>%s</ul>") % (
                                 host_name, newname, action_txt))
        elif c == False: # not yet confirmed
            return ""
        return

    html.help(_("The renaming of hosts is a complex operation since a host's name is being "
               "used as a unique key in various places. It also involves stopping and starting "
               "of the monitoring core. You cannot rename a host while you have pending changes."))

    html.begin_form("rename_host", method="POST")
    forms.header(_("Rename to host %s") % host_name)
    forms.section(_("Current name"))
    html.write_text(host_name)
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
        in_folder = Folder.root_folder()

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
        rulesets = FolderRulesets(folder)
        rulesets.load()

        changed = False
        for varname, ruleset in rulesets.get_rulesets().items():
            for rule_folder, rulenr, rule in ruleset.get_rules():
                # TODO: Move to rule?
                if rename_host_in_list(rule.host_list, oldname, newname):
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

    rename_host_in_folder_rules(Folder.root_folder())
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
                    if rename_host_in_list(rule[key], oldname, newname):
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

    rules = load_notification_rules()
    num_changed = rename_in_event_rules(rules)
    if num_changed:
        actions += [ "notify_global" ] * num_changed
        save_notification_rules(rules)

    try:
        rules = load_alert_handler_rules() # only available in CEE
    except:
        rules = None

    if rules:
        num_changed = rename_in_event_rules(rules)
        if num_changed:
            actions += [ "alert_rules" ] * num_changed
            save_alert_handler_rules(rules)

    # Notification channels of flexible notifications also can have host conditions
    for userid, user in users.items():
        method = user.get("notification_method")
        if method and type(method) == tuple and method[0] == "flexible":
            channels_changed = 0
            for channel in method[1]:
                if channel.get("only_hosts"):
                    num_changed = rename_host_in_list(channel["only_hosts"], oldname, newname)
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

    if users_changed:
        return [ "favorites" ] * total_changed
    else:
        return []


def rename_host_in_bi(oldname, newname):
    return BIHostRenamer().rename_host(oldname, newname)


def rename_hosts_in_check_mk(renamings):
    action_counts = {}
    for site_id, name_pairs in group_renamings_by_site(renamings).items():
        site = config.site(site_id)
        message = _("Renamed host %s") % ", ".join(
            [_("%s into %s") % (oldname, newname) for (oldname, newname) in name_pairs])

        # Restart is done by remote automation (below), so don't do it during rename/sync
        # The sync is automatically done by the remote automation call
        add_change("renamed-hosts", message, sites=[site_id], need_restart=False)

        new_counts = check_mk_automation(site_id, "rename-hosts", [], name_pairs)

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
def rename_hosts(renamings):

    actions = []
    all_hosts = Host.all()

    # 1. Fix WATO configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    for folder, oldname, newname in renamings:
        try:
            this_host_actions = []
            this_host_actions += rename_host_in_folder(folder, oldname, newname)
            this_host_actions += rename_host_as_cluster_node(all_hosts, oldname, newname)
            this_host_actions += rename_host_in_parents(oldname, newname)
            this_host_actions += rename_host_in_rulesets(folder, oldname, newname)
            this_host_actions += rename_host_in_bi(oldname, newname)
            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException, e:
            auth_problems.append((oldname, e))

    # 2. Check_MK stuff ------------------------------------------------
    action_counts = rename_hosts_in_check_mk(successful_renamings)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    for folder, oldname, newname in successful_renamings:
        actions += rename_host_in_event_rules(oldname, newname)
        actions += rename_host_in_multisite(oldname, newname)

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    call_hook_hosts_changed(Folder.root_folder())

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

def mode_object_parameters(phase):
    hostname = html.var("host") # may be empty in new/clone mode
    host = Folder.current().host(hostname)
    if host is None:
        raise MKGeneralException(_('The given host does not exist.'))
    host.need_permission("read")
    service = html.get_unicode_input("service")

    if phase == "title":
        title = _("Parameters of") + " " + hostname
        if service:
            title += " / " + service
        return title

    elif phase == "buttons":
        if service:
            prefix = _("Host-")
        else:
            prefix = ""
        html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        if service:
            service_status_button(hostname, service)
        else:
            host_status_button(hostname, "hoststatus")
        html.context_button(prefix + _("Properties"), folder_preserving_link([("mode", "edit_host"), ("host", hostname)]), "edit")
        html.context_button(_("Services"), folder_preserving_link([("mode", "inventory"), ("host", hostname)]), "services")
        if not host.is_cluster():
            html.context_button(prefix + _("Diagnostic"),
              folder_preserving_link([("mode", "diag_host"), ("host", hostname)]), "diagnose")
        return

    elif phase == "action":
        return

    all_rulesets = AllRulesets()
    all_rulesets.load()

    def render_rule_reason(title, title_url, reason, reason_url, is_default, setting):
        if title_url:
            title = '<a href="%s">%s</a>' % (title_url, title)
        forms.section(title)

        if reason:
            reason = '<a href="%s">%s</a>' % (reason_url, reason)

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


    # For services we make a special handling the for origin and parameters
    # of that service!
    if service:
        serviceinfo = check_mk_automation(host.site_id(), "analyse-service", [hostname, service])
        if serviceinfo:
            forms.header(_("Check Origin and Parameters"), isopen = True, narrow=True, css="rulesettings")
            origin = serviceinfo["origin"]
            origin_txt = {
                "active"  : _("Active check"),
                "static"  : _("Manual check"),
                "auto"    : _("Inventorized check"),
                "classic" : _("Classical check"),
            }[origin]
            render_rule_reason(_("Type of check"), None, "", "", False, origin_txt)

            # First case: discovered checks. They come from var/check_mk/autochecks/HOST.
            if origin ==  "auto":
                checkgroup = serviceinfo["checkgroup"]
                checktype = serviceinfo["checktype"]
                if not checkgroup:
                    render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

                # Logwatch needs a special handling, since it is not configured
                # via checkgroup_parameters but via "logwatch_rules" in a special
                # WATO module.
                elif checkgroup == "logwatch":
                    rulespec = g_rulespecs.get("logwatch_rules")
                    output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                            serviceinfo["item"], serviceinfo["parameters"])

                else:
                    # Note: some discovered checks have a check group but
                    # *no* ruleset for discovered checks. One example is "ps".
                    # That can be configured as a manual check or created by
                    # inventory. But in the later case all parameters are set
                    # by the inventory. This will be changed in a later version,
                    # but we need to address it anyway.
                    grouprule = "checkgroup_parameters:" + checkgroup
                    if not g_rulespecs.exists(grouprule):
                        try:
                            rulespec = g_rulespecs.get("static_checks:" + checkgroup)
                        except KeyError:
                            rulespec = None

                        if rulespec:
                            url = folder_preserving_link([('mode', 'edit_ruleset'), ('varname', "static_checks:" + checkgroup), ('host', hostname)])
                            render_rule_reason(_("Parameters"), url, _("Determined by discovery"), None, False,
                                       rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))
                        else:
                            render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

                    else:
                        rulespec = g_rulespecs.get(grouprule)
                        output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                                serviceinfo["item"], serviceinfo["parameters"])

            elif origin == "static":
                checkgroup = serviceinfo["checkgroup"]
                checktype = serviceinfo["checktype"]
                if not group:
                    html.write_text(_("This check is not configurable via WATO"))
                else:
                    rulespec = g_rulespecs.get("static_checks:" + checkgroup)
                    itemspec = rulespec.item_spec
                    if itemspec:
                        item_text = itemspec.value_to_text(serviceinfo["item"])
                        title = rulespec.item_spec.title()
                    else:
                        item_text = serviceinfo["item"]
                        title = _("Item")
                    render_rule_reason(title, None, "", "", False, item_text)
                    output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                            serviceinfo["item"], PARAMETERS_OMIT)
                    html.write(rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))
                    html.close_td()
                    html.close_tr()
                    html.close_table()


            elif origin == "active":
                checktype = serviceinfo["checktype"]
                rulespec = g_rulespecs.get("active_checks:" + checktype)
                output_analysed_ruleset(all_rulesets, rulespec, hostname, None, serviceinfo["parameters"])

            elif origin == "classic":
                rule_nr  = serviceinfo["rule_nr"]
                rules    = all_rulesets.get("custom_checks").get_rules()
                rule_folder, rule_index, rule = rules[rule_nr]

                url = folder_preserving_link([('mode', 'edit_ruleset'), ('varname', "custom_checks"), ('host', hostname)])
                forms.section('<a href="%s">%s</a>' % (url, _("Command Line")))
                url = folder_preserving_link([
                    ('mode', 'edit_rule'),
                    ('varname', "custom_checks"),
                    ('rule_folder', rule_folder.path()),
                    ('rulenr', rule_index),
                    ('host', hostname)])

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


    last_maingroup = None
    for groupname in sorted(g_rulespecs.get_host_groups()):
        maingroup = groupname.split("/")[0]
        for rulespec in sorted(g_rulespecs.get_by_group(groupname), key = lambda x: x.title):
            if (rulespec.item_type == 'service') == (not service):
                continue # This rule is not for hosts/services

            # Open form for that group here, if we know that we have at least one rule
            if last_maingroup != maingroup:
                last_maingroup = maingroup
                rulegroup = get_rulegroup(maingroup)
                forms.header(rulegroup.title, isopen = maingroup == "monconf", narrow=True, css="rulesettings")
                html.help(rulegroup.help)

            output_analysed_ruleset(all_rulesets, rulespec, hostname, service)

    forms.end()


PARAMETERS_UNKNOWN = []
PARAMETERS_OMIT = []
def output_analysed_ruleset(all_rulesets, rulespec, hostname, service, known_settings=None):
    if known_settings is None:
        known_settings = PARAMETERS_UNKNOWN

    def rule_url(rule):
        return folder_preserving_link([
            ('mode',        'edit_rule'),
            ('varname',     varname),
            ('rule_folder', rule.folder.path()),
            ('rulenr',      rule.index()),
            ('host',        hostname),
            ('item',        mk_repr(service) if service else ''),
        ])

    varname = rulespec.name
    valuespec = rulespec.valuespec

    url = folder_preserving_link([
        ('mode', 'edit_ruleset'),
        ('varname', varname),
        ('host', hostname),
        ('item', mk_repr(service)),
    ])

    forms.section('<a href="%s">%s</a>' % (url, rulespec.title))

    ruleset = all_rulesets.get(varname)
    setting, rules = ruleset.analyse_ruleset(hostname, service)

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
    if known_settings is PARAMETERS_OMIT:
        return

    # Special handling for logwatch: The check parameter is always None. The actual
    # patterns are configured in logwatch_rules. We do not have access to the actual
    # patterns here but just to the useless "None". In order not to complicate things
    # we simply display nothing here.
    elif varname == "logwatch_rules":
        pass

    elif known_settings is not PARAMETERS_UNKNOWN:
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
            if rulespec.factory_default is not Rulespec.NO_FACTORY_DEFAULT \
                and rulespec.factory_default is not Rulespec.FACTORY_DEFAULT_UNUSED:
                fd = rulespec.factory_default.copy()
                fd.update(setting)
                setting = fd

        if valuespec and not rules: # show the default value
            if rulespec.factory_default is Rulespec.FACTORY_DEFAULT_UNUSED:
                # Some rulesets are ineffective if they are empty
                html.write_text(_("(unused)"))

            elif rulespec.factory_default is not Rulespec.NO_FACTORY_DEFAULT:
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
            if ruleset.match_type() in ( "all", "list" ):
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

def diag_host_tests():
    return [
        ('ping',          _('Ping')),
        ('agent',         _('Agent')),
        ('snmpv1',        _('SNMPv1')),
        ('snmpv2',        _('SNMPv2c')),
        ('snmpv2_nobulk', _('SNMPv2c (without Bulkwalk)')),
        ('snmpv3',        _('SNMPv3')),
        ('traceroute',    _('Traceroute')),
    ]


def mode_diag_host(phase):
    hostname = html.var("host")
    if not hostname:
        raise MKGeneralException(_('The hostname is missing.'))

    host = Folder.current().host(hostname)
    host.need_permission("read")

    if phase == 'title':
        return _('Diagnostic of host') + " " + hostname

    elif phase == 'buttons':
        html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        host_status_button(hostname, "hoststatus")
        html.context_button(_("Properties"), host.edit_url(), "edit")
        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"), host.params_url(), "rulesets")
        html.context_button(_("Services"), host.services_url(), "services")
        return

    vs_host = Dictionary(
        required_keys = ['hostname'],
        elements = [
            ('hostname', FixedValue(hostname,
                title = _('Hostname'),
                allow_empty = False
            )),
            ('ipaddress', IPv4Address(
                title = _('IP address'),
                allow_empty = False
            )),
            ('snmp_community', Password(
                title = _("SNMPv1/2 community"),
                allow_empty = False
            )),
            ('snmp_v3_credentials',
                SNMPCredentials(default_value = None, only_v3 = True)
            ),
        ]
    )

    vs_rules = Dictionary(
        optional_keys = False,
        elements = [
            ('agent_port', Integer(
                minvalue = 1,
                maxvalue = 65535,
                default_value = 6556,
                title = _("Check_MK Agent Port (<a href=\"%s\">Rules</a>)") % \
                    folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'agent_ports')]),
                help = _("This variable allows to specify the TCP port to "
                         "be used to connect to the agent on a per-host-basis.")
            )),
            ('snmp_timeout', Integer(
                title = _("SNMP-Timeout (<a href=\"%s\">Rules</a>)") % \
                    folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                help = _("After a request is sent to the remote SNMP agent we will wait up to this "
                         "number of seconds until assuming the answer get lost and retrying."),
                default_value = 1,
                minvalue = 1,
                maxvalue = 60,
                unit = _("sec"),
            )),
            ('snmp_retries', Integer(
                title = _("SNMP-Retries (<a href=\"%s\">Rules</a>)") % \
                    folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                default_value = 5,
                minvalue = 0,
                maxvalue = 50,
            )),
            ('datasource_program', TextAscii(
                title = _("Datasource Program (<a href=\"%s\">Rules</a>)") % \
                    folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'datasource_programs')]),
                help = _("For agent based checks Check_MK allows you to specify an alternative "
                         "program that should be called by Check_MK instead of connecting the agent "
                         "via TCP. That program must output the agent's data on standard output in "
                         "the same format the agent would do. This is for example useful for monitoring "
                         "via SSH.") + monitoring_macro_help(),
            ))
        ]
    )

    if host.is_cluster():
        raise MKGeneralException(_('This page does not support cluster hosts.'))

    if phase == 'action':
        if not html.check_transaction():
            return

        if html.var('_save'):
            # Save the ipaddress and/or community
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

            host.update_attributes(new)
            html.del_all_vars()
            html.set_var("host", hostname)
            html.set_var("folder", Folder.current().path())
            return "edit_host", return_message
        return

    html.open_div(class_="diag_host")
    html.open_table()
    html.open_tr()
    html.open_td()
    html.begin_form('diag_host', method = "POST")
    forms.header(_('Host Properties'))

    forms.section(legend = False)
    html.prevent_password_auto_completion()

    # The diagnose page shows both snmp variants at the same time
    # We need to analyse the preconfigured community and set either the
    # snmp_community or the snmp_v3_credentials
    vs_dict = {}
    for key, value in host.attributes().items():
        if key == "snmp_community" and type(value) == tuple:
            vs_dict["snmp_v3_credentials"] = value
            continue
        vs_dict[key] = value

    vs_host.render_input("vs_host", vs_dict)
    html.help(vs_host.help())

    forms.end()

    html.open_div(style="margin-bottom:10px")
    html.button("_save", _("Save & Exit"))
    html.close_div()

    forms.header(_('Options'))

    value = {}
    forms.section(legend = False)
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
        for ident, title in diag_host_tests():
            html.h3(title)
            html.open_table(class_=["data", "test"])
            html.open_tr(class_=["data", "odd0"])

            html.open_td(class_="icons")
            html.open_div()
            html.img("images/icon_reload.png", class_="icon", id="%s_img" % ident)
            html.open_a(href="javascript:start_host_diag_test(\'%s\', \'%s\');" % (ident, hostname))
            html.img("images/icon_reload.png", class_=["icon", "retry"], id_="%s_retry" % ident, title=_('Retry this test'))
            html.close_a()
            html.close_div()
            html.close_td()

            html.open_td()
            html.div('', class_="log", id_="%s_log" % ident)
            html.close_td()

            html.close_tr()
            html.close_table()
            html.javascript('start_host_diag_test("%s", "%s")' % (ident, hostname))

    html.close_td()
    html.close_tr()
    html.close_table()
    html.close_div()


def ajax_diag_host():
    try:
        init_wato_datastructures(with_wato_lock=True)

        if not config.user.may('wato.diag_host'):
            raise MKAuthException(_('You are not permitted to perform this action.'))

        hostname = html.var("host")
        if not hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        host = Host.host(hostname)

        if not host:
            raise MKGeneralException(_('The given host does not exist.'))
        if host.is_cluster():
            raise MKGeneralException(_('This view does not support cluster hosts.'))

        host.need_permission("read")

        _test = html.var('_test')
        if not _test:
            raise MKGeneralException(_('The test is missing.'))

        # Execute a specific test
        if _test not in dict(diag_host_tests()).keys():
            raise MKGeneralException(_('Invalid test.'))

        args = [""] * 12
        for idx, what in enumerate ([ 'ipaddress',
                                      'snmp_community',
                                      'agent_port',
                                      'snmp_timeout',
                                      'snmp_retries',
                                      'datasource_program' ]):
            args[idx] = html.var(what, "")

        if html.var("snmpv3_use"):
            snmpv3_use = { "0": "noAuthNoPriv",
                           "1": "authNoPriv",
                           "2": "authPriv",
                         }.get(html.var("snmpv3_use"))
            args[6] = snmpv3_use
            if snmpv3_use != "noAuthNoPriv":
                snmpv3_auth_proto = { "0": "md5", "1": "sha" }.get(html.var("snmpv3_auth_proto"))
                args[7] = snmpv3_auth_proto
                args[8] = html.var("snmpv3_security_name")
                args[9] = html.var("snmpv3_security_password")
                if snmpv3_use == "authPriv":
                    snmpv3_privacy_proto = { "0": "DES", "1": "AES" }.get(html.var("snmpv3_privacy_proto"))
                    args[10] = snmpv3_privacy_proto
                    args[11] = html.var("snmpv3_privacy_password")
            else:
                args[8] = html.var("snmpv3_security_name")

        result = check_mk_automation(host.site_id(), "diag-host", [hostname, _test] + args)
        # API is defined as follows: Two data fields, separated by space.
        # First is the state: 0 or 1, 0 means success, 1 means failed.
        # Second is treated as text output
        html.write_text("%s %s" % (result[0], result[1]))
    except Exception, e:
        html.write_text("1 %s" % _("Exception: %s") % traceback.format_exc())



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

class ModeDiscovery(WatoMode):
    SERVICE_ADD     = "add"
    SERVICE_REMOVE  = "remove"
    SERVICE_DISABLE = "disable"
    SERVICE_ENABLE  = "enable"

    def __init__(self):
        super(ModeDiscovery, self).__init__()
        self._from_vars()


    def _from_vars(self):
        self._host_name = html.var("host")
        self._host = Folder.current().host(self._host_name)
        if not self._host:
            raise MKGeneralException(_("You called this page with an invalid host name."))

        self._host.need_permission("read")

        if config.user.may("wato.services"):
            self._cache_options   = [ '@scan' ] if html.var("_scan") else [ '@noscan' ]

            if html.has_var("_show_checkboxes"):
                config.user.save_file("discovery_checkboxes", html.var("_show_checkboxes") == "1")

        else:
            self._cache_options   = [ '@noscan' ]

        self._show_checkboxes = config.user.may("wato.services") \
                                and config.user.load_file("discovery_checkboxes", False)

        if html.has_var("_hide_parameters"):
            config.user.save_file("parameter_column", html.var("_hide_parameters") == "no")


    def title(self):
        title = _("Services of host %s") % self._host_name
        if html.var("_scan"):
            title += _(" (live scan)")
        else:
            title += _(" (might be cached data)")
        return title


    def buttons(self):
        global_buttons()

        html.context_button(_("Folder"),
            folder_preserving_link([("mode", "folder")]), "back")

        host_status_button(self._host_name, "host")
        html.context_button(_("Properties"), folder_preserving_link([("mode", "edit_host"),
                                                    ("host", self._host_name)]), "edit")

        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"),
                                folder_preserving_link([("mode", "object_parameters"),
                                                        ("host", self._host_name)]), "rulesets")

            if self._host.is_cluster():
                html.context_button(_("Clustered Services"),
                  folder_preserving_link([("mode", "edit_ruleset"),
                                          ("varname", "clustered_services")]), "rulesets")

        if not self._host.is_cluster():
            # only display for non cluster hosts
            html.context_button(_("Diagnostic"),
                  folder_preserving_link([("mode", "diag_host"),
                                          ("host", self._host_name)]), "diagnose")


    def action(self):
        if html.check_transaction():
            return self._do_discovery()


    def _do_discovery(self):
        host     = self._host
        hostname = self._host.name()

        config.user.need_permission("wato.services")

        if html.var("_refresh"):
            #message = self._refresh_discovery()
            self._refresh_discovery()

        else:
            check_table = sorted(check_mk_automation(host.site_id(), "try-inventory",
                                               self._cache_options + [hostname]))

            checks, to_disable, to_enable = {}, [], []
            for check_source, check_type, checkgroup, item, paramstring, params, \
                descr, state, output, perfdata in check_table:

                state = self._get_service_state(check_source, check_type, item)

                if state == ModeDiscovery.SERVICE_ADD:
                    checks[(check_type, item)] = paramstring

                elif state == ModeDiscovery.SERVICE_DISABLE:
                    to_disable.append(descr)

                elif state == ModeDiscovery.SERVICE_ENABLE:
                    to_enable.append(descr)
                    checks[(check_type, item)] = paramstring

                elif state in [ ModeDiscovery.SERVICE_ENABLE, ModeDiscovery.SERVICE_REMOVE ]:
                    to_enable.append(descr)
                    if state == ModeDiscovery.SERVICE_ENABLE:
                        checks[(check_type, item)] = paramstring

            self._save_services(checks)
            self._save_host_service_enable_disable_rules(to_enable, to_disable)

        if not host.locked():
            host.clear_discovery_failed()

        #return "folder", message
        return


    def _save_services(self, checks):
        check_mk_automation(self._host.site_id(), "set-autochecks", [self._host.name()], checks)
        message = _("Saved check configuration of host '%s' with %d services") % \
                    (self._host.name(), len(checks))

        add_service_change(self._host, "set-autochecks", message)


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

        rulesets = AllRulesets()
        rulesets.load()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = Ruleset("ignored_services")

        service_patterns = [ ("%s$" % s) for s in services ]
        self._remove_from_rule_of_host(ruleset, service_patterns, value=not value)

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        for service in services[:]:
            value_without_host_rule = ruleset.analyse_ruleset(self._host.name(), service)[0]
            if (value == False and value_without_host_rule in [None, False]) \
               or value == value_without_host_rule:
                services.remove(service)

        service_patterns = [ ("%s$" % s) for s in services ]
        self._update_rule_of_host(ruleset, service_patterns, value=value)

        rulesets.save_folder(self._host.folder())


    def _remove_from_rule_of_host(self, ruleset, service_patterns, value):
        other_rule = self._get_rule_of_host(ruleset, value)
        if other_rule:
            disable_patterns = set(other_rule.item_list).difference(service_patterns)
            other_rule.item_list = sorted(list(disable_patterns))

            if not other_rule.item_list:
                ruleset.delete_rule(other_rule)


    def _update_rule_of_host(self, ruleset, service_patterns, value):
        folder = self._host.folder()

        rule = self._get_rule_of_host(ruleset, value)
        if rule:
            rule.item_list = sorted(list(set(service_patterns).union(rule.item_list)))

            if not rule.item_list:
                ruleset.delete_rule(rule)

        elif service_patterns:
            rule = Rule.create(folder, ruleset, [self._host.name()],
                               sorted(service_patterns))
            rule.value = value
            ruleset.prepend_rule(folder, rule)


    def _get_rule_of_host(self, ruleset, value):
        for folder, index, rule in ruleset.get_rules():
            if rule.is_discovery_rule_of(self._host.name()) and rule.value == value:
                return rule
        return None


    def _get_service_state(self, check_source, check_type, item):
        def _is_checked(check_source, check_type, item):
            if not self._show_checkboxes:
                return True

            return html.get_checkbox(self._checkbox_name(check_source, check_type, item))

        is_checked = _is_checked(check_source, check_type, item)

        # In case of single object actions the checkboxes are not respected, but the identity
        # of the services in the action url is constructed like the values produced by checkboxes.
        is_target_object = html.has_var(self._checkbox_name(check_source, check_type, item))

        if check_source == "new":
            if html.has_var("_fixall"):
                return ModeDiscovery.SERVICE_ADD # Fixall does not care about the checkboxes

            if html.has_var("_bulk_new_to_old") and is_checked:
                return ModeDiscovery.SERVICE_ADD

            if html.has_var("_new_to_old") and is_target_object:
                return ModeDiscovery.SERVICE_ADD

            if html.has_var("_bulk_new_to_disabled") and is_checked:
                return ModeDiscovery.SERVICE_DISABLE

            if html.has_var("_new_to_disabled") and is_target_object:
                return ModeDiscovery.SERVICE_DISABLE

            return ModeDiscovery.SERVICE_REMOVE

        elif check_source == "vanished":
            if html.has_var("_fixall"):
                return ModeDiscovery.SERVICE_REMOVE # Fixall does not care about the checkboxes

            if html.has_var("_bulk_vanished_to_new") and is_checked:
                return ModeDiscovery.SERVICE_REMOVE

            if html.has_var("_vanished_to_new") and is_target_object:
                return ModeDiscovery.SERVICE_REMOVE

            if html.has_var("_bulk_vanished_to_disabled") and is_checked:
                return ModeDiscovery.SERVICE_DISABLE

            if html.has_var("_old_vanished_disabled") and is_target_object:
                return ModeDiscovery.SERVICE_DISABLE

            return ModeDiscovery.SERVICE_ADD

        elif check_source == "old":
            if html.has_var("_bulk_old_to_new") and is_checked:
                return ModeDiscovery.SERVICE_REMOVE

            if html.has_var("_old_to_new") and is_target_object:
                return ModeDiscovery.SERVICE_REMOVE

            if html.has_var("_bulk_old_to_disabled") and is_checked:
                return ModeDiscovery.SERVICE_DISABLE

            if html.has_var("_old_to_disabled") and is_target_object:
                return ModeDiscovery.SERVICE_DISABLE

            return ModeDiscovery.SERVICE_ADD

        elif check_source == "ignored":
            if html.has_var("_bulk_%s_to_old" % check_source) and is_checked:
                return ModeDiscovery.SERVICE_ENABLE

            if html.has_var("_%s_to_old" % check_source) and is_target_object:
                return ModeDiscovery.SERVICE_ENABLE

            if html.has_var("_bulk_%s_to_new" % check_source) and is_checked:
                return ModeDiscovery.SERVICE_REMOVE

            if html.has_var("_%s_to_new" % check_source) and is_target_object:
                return ModeDiscovery.SERVICE_REMOVE

            return ModeDiscovery.SERVICE_DISABLE

        elif check_source in [ "clustered_old", "clustered_new" ]:
            return ModeDiscovery.SERVICE_ADD

        return ModeDiscovery.SERVICE_REMOVE


    def _refresh_discovery(self):
        hostname = self._host.name()
        counts, failed_hosts = check_mk_automation(self._host.site_id(), "inventory",
                                                   [ "@scan", "refresh", hostname ])
        count_added, count_removed, count_kept, count_new = counts[hostname]

        message = _("Refreshed check configuration of host '%s' with %d services") % \
                    (hostname, count_added)

        add_service_change(self._host, "refresh-autochecks", message)

        return message


    def page(self):
        self._service_tables()


    def _service_tables(self):
        host      = self._host
        hostname  = self._host.name()

        try:
            check_table = self._get_check_table()
        except Exception, e:
            log_exception()
            if config.debug:
                raise
            retry_link = html.render_a(
                content=_("Retry discovery while ignoring this error (Result might be incomplete)."),
                href=html.makeuri([("ignoreerrors", "1"), ("_scan", html.var("_scan"))])
            )
            html.show_warning("<b>%s</b>: %s<br><br>%s" %
                              (_("Service discovery failed for this host"), e, retry_link))
            return

        html.begin_form("checks", method = "POST")
        self._show_action_buttons(check_table)

        if html.var("_scan"):
            html.hidden_field("_scan", "on", add_var=True)

        table.begin(css="data", searchable=False, limit=None, sortable=False)

        checks_by_source = self._checks_by_source(check_table)

        for check_source, show_bulk_actions, title, help_text in self._check_sources():
            checks = checks_by_source.get(check_source, [])
            if not checks:
                continue

            if check_source == "new":
                icon = "undecided"
            elif check_source == "ignored":
                icon = "disabled"
            elif check_source == "old":
                icon = "monitored"
            else:
                icon = None
            if icon:
                grouptitle = html.render_icon(icon + "_service") + " " + title
            else:
                grouptitle = title

            table.groupheader(grouptitle + html.render_help(help_text))

            if show_bulk_actions and len(checks) > 10:
                self._bulk_actions(check_source, collect_headers=False)

            for check in sorted(checks, key=lambda c: c[6]):
                self._check_row(check, show_bulk_actions)

            if show_bulk_actions:
                self._bulk_actions(check_source, collect_headers="finished")

        table.end()

        html.hidden_fields()
        html.end_form()


    def _check_sources(self):
        return [
            # check_source, show bulk actions, title
            ("new",           True,  _("Undecided services (currently not monitored)"),
            _("These services have been found by the service discovery but are not yet added "
              "to the monitoring. You should either decide to monitor them or to permanently "
              "disable them. If you are sure that they are just transitional, just leave them "
              "until they vanish.")), # undecided
            ("vanished",      True,  _("Vanished services (monitored, but no longer exist)"),
            _("These services had been added to the monitoring by a previous discovery "
              "but the actual items that are monitored are not present anymore. This might "
              "be due to a real failure. In that case you should leave them in the monitoring. "
              "If the actually monitored things are really not relevant for the monitoring "
              "anymore then you should remove them in order to avoid UNKNOWN services in the "
              "monitoring.")),
            ("old",           True,  _("Monitored services"),
            _("These services had been found by a discovery and are currently configured "
              "to be monitored.")),
            ("ignored",       True,  _("Disabled services"),
            _("These services are being discovered but have been disabled by creating a rule "
              "in the rule set <i>Disabled services</i> oder <i>Disabled checks</i>.")),
            ("active",        False, _("Active checks"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call classical check plugins. They have been added by a rule in the section "
              "<i>Active checks</i> or implicitely by Check_MK.")),
            ("manual",        False, _("Manual checks"),
            _("These services have not been found by the discovery but have been added "
              "manually by a rule in the WATO module <i>Manual checks</i>.")),
            ("legacy",        False, _("Legacy services (defined in main.mk)"),
            _("These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
              "in <tt>main.mk</tt> or a similar configuration file.")),
            ("custom",        False, _("Custom checks (defined via rule)"),
            _("These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
              "call a classical check plugin, that you have installed yourself.")),
            ("clustered_old", False, _("Monitored clustered services (located on cluster host)"),
            _("These services have been found on this host but have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>.")),
            ("clustered_new", False, _("Undecided clustered services"),
            _("These services have been found on this host and have been mapped to "
              "a cluster host by a rule in the set <i>Clustered services</i>, but are not "
              "yet added to the active monitoring. Please either add them or permanently disable "
              "them.")),
        ]


    def _check_row(self, check, show_bulk_actions):
        check_source, check_type, checkgroup, item, paramstring, params, \
            descr, state, output, perfdata = check

        statename = short_service_state_name(state, "")
        if statename == "":
            statename = short_service_state_name(-1)
            stateclass = "state svcstate statep"
            state = 0 # for tr class
        else:
            stateclass = "state svcstate state%s" % state

        table.row(css="data", state=state)

        self._show_bulk_checkbox(check_source, check_type, item, show_bulk_actions)
        self._show_actions(check)

        table.cell(_("State"), statename, css=stateclass)
        table.cell(_("Service"), html.attrencode(descr))
        table.cell(_("Status detail"))
        if check_source in ("custom", "active"):
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

        ctype = "check_" + check_type if check_source == "active" else check_type
        manpage_url = folder_preserving_link([("mode", "check_manpage"),
                                              ("check_type", ctype)])
        table.cell(_("Check plugin"),
                   html.render_a(content=ctype, href=manpage_url))

        if self._show_parameter_column():
            table.cell(_("Check parameters"))
            self._show_check_parameters(check_source, check_type, checkgroup, params)


    def _show_actions(self, check):
        check_source, check_type, checkgroup, item, paramstring, params, \
            descr, state, output, perfdata = check

        def to_disabled_button():
            url = html.makeactionuri([
                ("_%s_to_disabled" % check_source, "1"),
                (self._checkbox_name(check_source, check_type, item), ""),
            ])
            html.icon_button(url, _("Move to disabled services"), "service_to_disabled", ty="icon")


        def to_enabled_button():
            url = html.makeactionuri([
                ("_%s_to_old" % check_source, "1"),
                (self._checkbox_name(check_source, check_type, item), ""),
            ])
            html.icon_button(url, _("Move to monitored services"), "service_to_monitored", ty="icon")


        def to_removed_button():
            url = html.makeactionuri([
                ("_%s_to_new" % check_source, "1"),
                (self._checkbox_name(check_source, check_type, item), ""),
            ])
            html.icon_button(url, _("Remove from monitoring"),
                "service_to_removed", ty="icon")


        def to_undecided_button():
            url = html.makeactionuri([
                ("_%s_to_new" % check_source, "1"),
                (self._checkbox_name(check_source, check_type, item), ""),
            ])
            html.icon_button(url, _("Move to undecided services"),
                "service_to_undecided", ty="icon")


        def rulesets_button():
            # Link to list of all rulesets affecting this service
            params_url = folder_preserving_link([("mode", "object_parameters"),
                                    ("host", self._host_name),
                                    ("service", descr)])
            html.icon_button(params_url,
                _("View and edit the parameters for this service"), "rulesets")

        def check_parameters_button():
            ruleset_name = self._get_ruleset_name(check_source, check_type, checkgroup)
            if ruleset_name is None:
                return

            url = folder_preserving_link([("mode", "edit_ruleset"),
                             ("varname", ruleset_name),
                             ("host", self._host_name),
                             ("item", mk_repr(item))])
            html.icon_button(url,
                _("Edit and analyze the check parameters of this service"), "check_parameters")

        def disabled_services_button():
            url = folder_preserving_link([("mode", "edit_ruleset"),
                             ("varname", "ignored_services"),
                             ("host", self._host_name),
                             ("item", mk_repr(descr))])
            html.icon_button(url, _("Edit and analyze the disabled services rules"), "rulesets")


        table.cell(css="buttons")
        if check_source == "new":
            to_enabled_button()
            if may_edit_ruleset("ignored_services"):
                to_disabled_button()

        elif check_source == "ignored":
            if may_edit_ruleset("ignored_services"):
                to_enabled_button()
                to_undecided_button()
                disabled_services_button()

        elif check_source == "old":
            to_undecided_button()
            if may_edit_ruleset("ignored_services"):
                to_disabled_button()

        elif check_source == "vanished":
            to_removed_button()
            if may_edit_ruleset("ignored_services"):
                to_disabled_button()

        else:
            html.empty_icon()
            html.empty_icon()

        if check_source not in [ "new", "ignored" ] and config.user.may('wato.rulesets'):
            rulesets_button()
            check_parameters_button()


    def _show_parameter_column(self):
        return config.user.load_file("parameter_column", False)


    def _show_check_parameters(self, check_source, check_type, checkgroup, params):
        varname = self._get_ruleset_name(check_source, check_type, checkgroup)
        if varname and g_rulespecs.exists(varname):
            rulespec = g_rulespecs.get(varname)
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


    def _get_ruleset_name(self, check_source, check_type, checkgroup):
        if checkgroup == "logwatch":
            return "logwatch_rules"
        elif checkgroup:
            return "checkgroup_parameters:" + checkgroup
        elif check_source == "active":
            return "active_checks:" + check_type
        else:
            return None


    def _show_bulk_checkbox(self, check_source, check_type, item, show_bulk_actions):
        if not self._show_checkboxes:
            return

        if not show_bulk_actions:
            table.cell(css="checkbox")
            return

        table.cell("<input type=button class=checkgroup name=_toggle_group"
                   " onclick=\"toggle_group_rows(this);\" value=\"X\" />", sortable=False,
                   css="checkbox")

        html.checkbox(self._checkbox_name(check_source,check_type, item),
            True, add_attr = ['title="%s"' % _('Temporarily ignore this service')])


    # This function returns the HTTP variable name to use for a service. This needs to be unique
    # for each host. Since this text is used as variable name, it must not contain any umlauts
    # or other special characters that are disallowed by html.parse_field_storage(). Since item
    # may contain such chars, we need to use some encoded form of it. Simple escaping/encoding
    # like we use for values of variables is not enough here.
    def _checkbox_name(self, check_source, check_type, item):
        return "_%s_%s_%s" % (check_source, check_type, hash(item))


    # We first try using the cache (if the user has not pressed Full Scan).
    # If we do not find any data, we omit the cache and immediately try
    # again without using the cache.
    def _get_check_table(self):
        # Read current check configuration
        error_options = not html.var("ignoreerrors") and [ "@raiseerrors" ] or []

        options = self._cache_options + error_options + [ self._host_name ]
        check_table = check_mk_automation(self._host.site_id(), "try-inventory", options)

        if not check_table and self._cache_options != []:
            check_table = check_mk_automation(self._host.site_id(), "try-inventory",
                                              [ '@scan', self._host_name ])
            html.set_var("_scan", "on")

        return sorted(check_table)


    def _checks_by_source(self, check_table):
        by_source = {}
        for entry in check_table:
            entries = by_source.setdefault(entry[0], [])
            entries.append(entry)
        return by_source


    def _show_action_buttons(self, check_table):
        if not config.user.may("wato.services"):
            return

        fixall = 0
        for entry in check_table:
            if entry[0] == 'new':
                fixall += 1
                break

        for entry in check_table:
            if entry[0] == 'vanished':
                fixall += 1
                break

        if fixall == 2:
            html.button("_fixall", _("Fix all missing/vanished"))

        if self._already_has_services(check_table):
            html.button("_refresh", _("Automatic refresh (tabula rasa)"))

        html.buttonlink(html.makeuri([("_scan", "yes")]), _("Full scan"),
                  title=_("Fetch new data from the host and ignore caches"))


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


    def _already_has_services(self, check_table):
        for check in check_table:
            if check[0] in [ "old", "vanished" ]:
                return True
        return False


    def _bulk_actions(self, check_source, collect_headers):
        if not config.user.may("wato.services"):
            return

        table.row(collect_headers=collect_headers, fixed=True)

        table.cell(css="bulkactions service_discovery", colspan=self._bulk_action_colspan())

        if self._show_checkboxes:
            label = _("selected services")
        else:
            label = _("all services")

        if check_source == "new":
            html.button("_bulk_new_to_old",   _("Monitor"),
                help=_("Move %s to enabled services") % label)
            html.button("_bulk_new_to_disabled", _("Disable"),
                help=_("Move %s to disabled services") % label)

        elif check_source == "vanished":
            html.button("_bulk_vanished_to_new", _("Remove"),
                help=_("Move %s to new services") % label)
            html.button("_bulk_vanished_to_disabled", _("Disable"),
                help=_("Move %s to disabled services") % label)

        elif check_source == "old":
            html.button("_bulk_old_to_new", _("Move to undecided"),
                help=_("Move %s to new services") % label)
            html.button("_bulk_old_to_disabled", _("Disable"),
                help=_("Move %s to new services") % label)

        elif check_source == "ignored":
            html.button("_bulk_ignored_to_old", _("Monitor"),
                help=_("Move %s to enabled services") % label)
            html.button("_bulk_ignored_to_new", _("Move to undecided"),
                help=_("Move %s to new services") % label)


    def _bulk_action_colspan(self):
        colspan = 5
        if self._show_parameter_column():
            colspan += 1
        if self._show_checkboxes:
            colspan += 1
        return colspan



class ModeFirstDiscovery(ModeDiscovery):
    pass


class ModeAjaxExecuteCheck(WatoWebApiMode):
    def __init__(self):
        super(ModeAjaxExecuteCheck, self).__init__()
        self._from_vars()


    def _from_vars(self):
        # TODO: Validate the site
        self._site      = html.var("site")

        self._host_name = html.var("host")
        self._host      = Folder.current().host(self._host_name)
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
            state, output = check_mk_automation(self._site, "active-check",
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

def mode_search(phase):
    if phase == "title":
        return _("Search for hosts below %s") % Folder.current().title()

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Folder"), Folder.current().url(), "back")
        return

    elif phase == "action":
        return "folder"

    Folder.current().show_breadcrump()

    ## # Show search form
    html.begin_form("edit_host", method="GET")
    html.prevent_password_auto_completion()
    forms.header(_("General Properties"))
    forms.section(_("Hostname"))
    html.text_input("host_search_host")
    html.set_focus("host_search_host")

    # Attributes
    configure_attributes(False, {}, "host_search", parent = None, varprefix="host_search_")

    # Button
    forms.end()
    html.button("_local", _("Search in %s") % Folder.current().title(), "submit")
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

class ModeBulkImport(WatoMode):
    _upload_tmp_path = cmk.paths.tmp_dir + "/host-import"

    def __init__(self):
        super(ModeBulkImport, self).__init__()
        self._csv_reader = None
        self._params = None


    def title(self):
        return _("Bulk host import")


    def buttons(self):
        html.context_button(_("Abort"), folder_preserving_link([("mode", "folder")]), "abort")
        if html.has_var("file_id"):
            html.context_button(_("Back"), folder_preserving_link([("mode", "bulk_import")]), "back")


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
        if not os.path.exists(self._upload_tmp_path):
            make_nagios_directories(self._upload_tmp_path)

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
                Folder.current().create_hosts([(host_name, attributes, None)])
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
            weblib.set_rowselection('wato-folder-/' + Folder.current().path(), selected, 'set')
            html.set_var('mode', 'bulkinventory')
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
            header = len(headers) > col_num and headers[col_num] or None
            table.cell(html.attrencode(header))
            attribute_varname = "attribute_%d" % col_num
            if html.var(attribute_varname):
                attribute_method = html.var("attribute_varname")
            else:
                attribute_method = self._try_detect_default_attribute(attributes, header)
                html.del_var(attribute_varname)

            html.select("attribute_%d" % col_num, attributes, attribute_method, attrs={"autocomplete": "off"})

        # Render sample rows
        for row in rows:
            table.row()
            for cell in row:
                table.cell(None, html.attrencode(cell))

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
            ("ipaddress",       _("IPv4 Address")),
            ("ipv6address",     _("IPv6 Address")),
            ("snmp_community",  _("SNMP Community")),
        ]

        # Add tag groups
        for entry in configured_host_tags():
            attributes.append(("tag_" + entry[0], _("Tag: %s") % entry[1]))

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
                score = key_match_score > title_match_score and key_match_score or title_match_score

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

def mode_bulk_discovery(phase):
    if phase == "title":
        return _("Bulk Service Discovery")

    elif phase == "buttons":
        html.context_button(_("Folder"), Folder.current().url(), "back")
        return

    elif phase == "action":
        if html.var("_item"):
            if not html.check_transaction():
                html.write(json.dumps([ 'failed', 0, 0, 0, 0, 0, 0, ]) + "\n")
                html.write_text(_("Error during discovery: Maximum number of retries reached. "
                                  "You need to restart the bulk service discovery"))
                return ""

            how = html.var("how")
            try:
                site_id, folderpath, hostnamesstring = html.var("_item").split("|")
                hostnames = hostnamesstring.split(";")
                num_hosts = len(hostnames)
                num_skipped_hosts = 0
                num_failed_hosts = 0
                folder = Folder.folder(folderpath)
                arguments = [how,] + hostnames
                if html.var("use_cache"):
                    arguments = [ "@cache" ] + arguments
                if html.var("do_scan"):
                    arguments = [ "@scan" ] + arguments
                if not html.get_checkbox("ignore_errors"):
                    arguments = [ "@raiseerrors" ] + arguments

                timeout = html.request_timeout() - 2

                unlock_exclusive() # Avoid freezing WATO when hosts do not respond timely
                counts, failed_hosts = check_mk_automation(site_id, "inventory",
                                                           arguments, timeout=timeout)
                lock_exclusive()
                Folder.invalidate_caches()
                folder = Folder.folder(folderpath)

                # sum up host individual counts to have a total count
                sum_counts = [ 0, 0, 0, 0 ] # added, removed, kept, new
                result_txt = ''
                for hostname in hostnames:
                    sum_counts[0] += counts[hostname][0]
                    sum_counts[1] += counts[hostname][1]
                    sum_counts[2] += counts[hostname][2]
                    sum_counts[3] += counts[hostname][3]
                    host = folder.host(hostname)
                    if hostname in failed_hosts:
                        reason = failed_hosts[hostname]
                        if reason == None:
                            result_txt += _("%s: discovery skipped: host not monitored<br>") % hostname
                            num_skipped_hosts += 1
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
                    msg = _("Error during inventory of %s on site %s<div class=exc>%s</div") % \
                                     (", ".join(hostnames), site_id, e)
                else:
                    msg = _("Error during inventory of %s<div class=exc>%s</div>") % (", ".join(hostnames), e)
                if config.debug:
                    msg += "<br><pre>%s</pre><br>" % html.attrencode(traceback.format_exc().replace("\n", "<br>"))
                result += msg
            html.write(result)
            return ""
        return


    # interactive progress is *not* done in action phase. It
    # renders the page content itself.

    def recurse_hosts(folder, recurse, only_failed):
        entries = []
        for host_name, host in folder.hosts().items():
            if not only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if recurse:
            for subfolder in folder.all_subfolders().values():
                entries += recurse_hosts(subfolder, recurse, only_failed)
        return entries

    config.user.need_permission("wato.services")

    if html.get_checkbox("only_failed_invcheck"):
        restrict_to_hosts = find_hosts_with_failed_inventory_check()
    else:
        restrict_to_hosts = None

    if html.get_checkbox("only_ok_agent"):
        skip_hosts = find_hosts_with_failed_agent()
    else:
        skip_hosts = []

    # 'all' not set -> only inventorize checked hosts
    hosts_to_discover = []

    if not html.var("all"):
        complete_folder = False
        if html.get_checkbox("only_failed"):
            filterfunc = lambda host: host.discovery_failed()
        else:
            filterfunc = None

        for host_name in get_hostnames_from_checkboxes(filterfunc):
            if restrict_to_hosts and host_name not in restrict_to_hosts:
                continue
            if host_name in skip_hosts:
                continue
            host = Folder.current().host(host_name)
            host.need_permission("write")
            hosts_to_discover.append( (host.site_id(), host.folder(), host_name) )

    # all host in this folder, maybe recursively. New: we always group
    # a bunch of subsequent hosts of the same folder into one item.
    # That saves automation calls and speeds up mass inventories.
    else:
        complete_folder = True
        entries = recurse_hosts(Folder.current(), html.get_checkbox("recurse"), html.get_checkbox("only_failed"))
        items = []
        hostnames = []
        current_folder = None
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
    items = []
    hosts_in_this_item = 0
    bulk_size = int(html.var("bulk_size", 10))

    for site_id, folder, host_name in hosts_to_discover:
        if not items or (site_id, folder) != current_site_and_folder or hosts_in_this_item >= bulk_size:
            items.append("%s|%s|%s" % (site_id, folder.path(), host_name))
            hosts_in_this_item = 1
        else:
            items[-1] += ";" + host_name
            hosts_in_this_item += 1
        current_site_and_folder = site_id, folder


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
        html.begin_form("bulkinventory", method = "POST")
        html.hidden_fields()

        # Mode of action
        html.open_p()
        if not complete_folder:
            html.write_text(_("You have selected <b>%d</b> hosts for bulk discovery. ") % len(hosts_to_discover))
        html.write_text(_("Check_MK service discovery will automatically find and configure "
                          "services to be checked on your hosts."))
        forms.header(_("Bulk Discovery"))
        forms.section(_("Mode"))
        html.radiobutton("how", "new",     True,  _("Add unmonitored services") + "<br>")
        html.radiobutton("how", "remove",  False, _("Remove vanished services") + "<br>")
        html.radiobutton("how", "fixall",  False, _("Add unmonitored & remove vanished services") + "<br>")
        html.radiobutton("how", "refresh", False, _("Refresh all services (tabula rasa)") + "<br>")

        forms.section(_("Selection"))
        if complete_folder:
            html.checkbox("recurse", True, label=_("Include all subfolders"))
            html.br()
        html.checkbox("only_failed", False, label=_("Only include hosts that failed on previous discovery"))
        html.br()
        html.checkbox("only_failed_invcheck", False, label=_("Only include hosts with a failed discovery check"))
        html.br()
        html.checkbox("only_ok_agent", False, label=_("Exclude hosts where the agent is unreachable"))

        forms.section(_("Performance options"))
        html.checkbox("use_cache", True, label=_("Use cached data if present"))
        html.br()
        html.checkbox("do_scan", True, label=_("Do full SNMP scan for SNMP devices"))
        html.br()
        html.write_text(_("Number of hosts to handle at once:") + " ")
        html.number_input("bulk_size", 10, size=3)

        forms.section(_("Error handling"))
        html.checkbox("ignore_errors", True, label=_("Ignore errors in single check plugins"))

        # Start button
        forms.end()
        html.button("_start", _("Start"))


def find_hosts_with_failed_inventory_check():
    import sites
    return sites.live().query_column(
        "GET services\n"
        "Filter: description = Check_MK inventory\n" # FIXME: Remove this one day
        "Filter: description = Check_MK Discovery\n"
        "Or: 2\n"
        "Filter: state > 0\n"
        "Columns: host_name")

def find_hosts_with_failed_agent():
    import sites
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

def mode_bulk_edit(phase):
    if phase == "title":
        return _("Bulk edit hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            config.user.need_permission("wato.edit_hosts")

            changed_attributes = collect_attributes("bulk")
            host_names = get_hostnames_from_checkboxes()
            for host_name in host_names:
                host = Folder.current().host(host_name)
                host.update_attributes(changed_attributes)
                # call_hook_hosts_changed() is called too often.
                # Either offer API in class Host for bulk change or
                # delay saving until end somehow

            return "folder", _("Edited %d hosts") % len(host_names)
        return

    host_names = get_hostnames_from_checkboxes()
    hosts = dict([(host_name, Folder.current().host(host_name)) for host_name in host_names])
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
    configure_attributes(False, hosts, "bulk", parent = Folder.current())
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

def mode_bulk_cleanup(phase):
    folder = Folder.current()

    if phase == "title":
        return _("Bulk removal of explicit attributes")

    elif phase == "buttons":
        html.context_button(_("Back"), folder.url(), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            config.user.need_permission("wato.edit_hosts")
            to_clean = bulk_collect_cleaned_attributes()
            if "contactgroups" in to_clean:
                folder.need_permission("write")

            hosts = get_hosts_from_checkboxes()

            # Check all permissions before doing any edit
            for host in hosts:
                host.need_permission("write")

            for host in hosts:
                host.clean_attributes(to_clean)

            return "folder"
        return

    hosts = get_hosts_from_checkboxes()

    html.p(_("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
             "explicit attribute values from hosts. The hosts will then inherit attributes "
             "configured at the host list or folders or simply fall back to the builtin "
             "default values.") % len(hosts))

    html.begin_form("bulkcleanup", method = "POST")
    forms.header(_("Attributes to remove from hosts"))
    if not select_attributes_for_bulk_cleanup(folder, hosts):
        forms.end()
        html.write_text(_("The selected hosts have no explicit attributes"))
    else:
        forms.end()
        html.button("_save", _("Save & Finish"))
    html.hidden_fields()
    html.end_form()


def bulk_collect_cleaned_attributes():
    to_clean = []
    for attr, topic in all_host_attributes():
        attrname = attr.name()
        if html.get_checkbox("_clean_" + attrname) == True:
            to_clean.append(attrname)
    return to_clean


def select_attributes_for_bulk_cleanup(folder, hosts):
    num_shown = 0
    for attr, topic in all_host_attributes():
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
        container = folder
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
def mode_parentscan(phase):
    if phase == "title":
        return _("Parent scan")

    elif phase == "buttons":
        html.context_button(_("Folder"), Folder.current().url(), "back")
        return

    # Ignored during initial form display
    settings = {
        "where"          : html.var("where"),
        "alias"          : html.get_unicode_input("alias", "").strip() or None,
        "recurse"        : html.get_checkbox("recurse"),
        "select"         : html.var("select"),
        "timeout"        : saveint(html.var("timeout")) or 8,
        "probes"         : saveint(html.var("probes")) or 2,
        "max_ttl"        : saveint(html.var("max_ttl")) or 10,
        "force_explicit" : html.get_checkbox("force_explicit"),
        "ping_probes"    : saveint(html.var("ping_probes")) or 0,
    }

    if phase == "action":
        if html.var("_item"):
            try:
                folderpath, host_name = html.var("_item").split("|")
                folder = Folder.folder(folderpath)
                host = folder.host(host_name)
                site_id = host.site_id()
                params = map(str, [ settings["timeout"], settings["probes"], settings["max_ttl"], settings["ping_probes"] ])
                gateways = check_mk_automation(site_id, "scan-parents", params + [host_name])
                gateway, state, skipped_gateways, error = gateways[0]

                if state in [ "direct", "root", "gateway" ]:
                    message, pconf, gwcreat = \
                        configure_gateway(state, site_id, host, gateway)
                else:
                    message = error
                    pconf = False
                    gwcreat = False

                # Possible values for state are:
                # failed, dnserror, garbled, root, direct, notfound, gateway
                counts = [ 'continue',
                    1,                                           # Total hosts
                    gateway and 1 or 0,                          # Gateways found
                    state in [ "direct", "root" ] and 1 or 0,    # Directly reachable hosts
                    skipped_gateways,                            # number of failed PING probes
                    state == "notfound" and 1 or 0,              # No gateway found
                    pconf and 1 or 0,                            # New parents configured
                    gwcreat and 1 or 0,                          # Gateway hosts created
                    state in [ "failed", "dnserror", "garbled" ] and 1 or 0, # Errors
                ]
                result = "%s\n%s: %s<br>\n" % (json.dumps(counts), host_name, message)

            except Exception, e:
                result = json.dumps([ 'failed', 1, 0, 0, 0, 0, 0, 1 ]) + "\n"
                if site_id:
                    msg = _("Error during parent scan of %s on site %s: %s") % (host_name, site_id, e)
                else:
                    msg = _("Error during parent scan of %s: %s") % (host_name, e)
                if config.debug:
                    msg += "<br><pre>%s</pre>" % html.attrencode(traceback.format_exc().replace("\n", "<br>"))
                result += msg + "\n<br>"
            html.write(result)
            return ""
        return


    config.user.need_permission("wato.parentscan")

    # interactive progress is *not* done in action phase. It
    # renders the page content itself.

    # select: 'noexplicit' -> no explicit parents
    #         'no'         -> no implicit parents
    #         'ignore'     -> not important
    def include_host(host, select):
        if select == 'noexplicit' and host.has_explicit_attribute("parents"):
            return False
        elif select == 'no':
            if host.effective_attribute("parents"):
                return False
        return True


    def recurse_hosts(folder, recurse, select):
        entries = []
        for host in folder.hosts().values():
            if include_host(host, select):
                entries.append(host)

        if recurse:
            for subfolder in folder.all_subfolders().values():
                entries += recurse_hosts(subfolder, recurse, select)
        return entries


    # 'all' not set -> only scan checked hosts in current folder, no recursion
    if not html.var("all"):
        complete_folder = False
        items = []
        for host in get_hosts_from_checkboxes():
            if include_host(host, settings["select"]):
                items.append("%s|%s" % (host.folder().path(), host.name()))

    # all host in this folder, maybe recursively
    else:
        complete_folder = True
        entries = recurse_hosts(Folder.current(), settings["recurse"], settings["select"])
        items = []
        for host in entries:
            items.append("%s|%s" % (host.folder().path(), host.name()))


    if html.var("_start"):
        # Persist settings
        config.user.save_file("parentscan", settings)


        # Start interactive progress
        interactive_progress(
            items,
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

    else:
        html.begin_form("parentscan", method = "POST")
        html.hidden_fields()

        # Mode of action
        html.open_p()
        if not complete_folder:
            html.write_text(_("You have selected <b>%d</b> hosts for parent scan. ") % len(items))
        html.p(_("The parent scan will try to detect the last gateway "
                 "on layer 3 (IP) before a host. This will be done by "
                 "calling <tt>traceroute</tt>. If a gateway is found by "
                 "that way and its IP address belongs to one of your "
                 "monitored hosts, that host will be used as the hosts "
                 "parent. If no such host exists, an artifical ping-only "
                 "gateway host will be created if you have not disabled "
                 "this feature."))

        forms.header(_("Settings for Parent Scan"))

        settings = config.user.load_file("parentscan", {
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
        if complete_folder:
            html.checkbox("recurse", settings["recurse"], label=_("Include all subfolders"))
            html.br()
        html.radiobutton("select", "noexplicit", settings["select"] == "noexplicit",
                _("Skip hosts with explicit parent definitions (even if empty)") + "<br>")
        html.radiobutton("select", "no",  settings["select"] == "no",
                _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>")
        html.radiobutton("select", "ignore",  settings["select"] == "ignore",
                _("Scan all hosts") + "<br>")

        # Performance
        forms.section(_("Performance"))
        html.open_table()
        html.open_tr()
        html.open_td()
        html.write_text(_("Timeout for responses") + ":")
        html.close_td()
        html.open_td()
        html.number_input("timeout", settings["timeout"], size=2)
        html.write_text(_("sec"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of probes per hop") + ":")
        html.close_td()
        html.open_td()
        html.number_input("probes", settings["probes"], size=2)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Maximum distance (TTL) to gateway") + ":")
        html.close_td()
        html.open_td()
        html.number_input("max_ttl", settings["max_ttl"], size=2)
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
        html.number_input("ping_probes", settings.get("ping_probes", 5), size=2)
        html.close_td()
        html.close_tr()
        html.close_table()

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox("force_explicit",
            settings["force_explicit"], label=_("Force explicit setting for parents even if setting matches that of the folder"))

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write_text(_("Create gateway hosts in"))
        html.open_ul()

        html.radiobutton("where", "subfolder", settings["where"] == "subfolder",
                _("in the subfolder <b>%s/Parents</b>") % Folder.current_disk_folder().title())

        html.br()
        html.radiobutton("where", "here", settings["where"] == "here",
                _("directly in the folder <b>%s</b>") % Folder.current_disk_folder().title())
        html.br()
        html.radiobutton("where", "there", settings["where"] == "there",
                _("in the same folder as the host"))
        html.br()
        html.radiobutton("where", "nowhere", settings["where"] == "nowhere",
                _("do not create gateway hosts"))
        html.close_ul()
        html.write_text(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", settings["alias"])

        # Start button
        forms.end()
        html.button("_start", _("Start"))


def configure_gateway(state, site_id, host, gateway):
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
                gw_folder = Folder.current_disk_folder()

            elif where == "subfolder":
                current = Folder.current_disk_folder()
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
                (parents and ",".join(parents) or _("none")), False, gwcreat


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
def mode_random_hosts(phase):
    if phase == "title":
        return _("Random Hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), Folder.current().url(), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            count = int(html.var("count"))
            folders = int(html.var("folders"))
            levels = int(html.var("levels"))
            created = create_random_hosts(Folder.current(), count, folders, levels)
            return "folder", _("Created %d random hosts.") % created
        else:
            return "folder"

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


def create_random_hosts(folder, count, folders, levels):
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
            total_created += create_random_hosts(subfolder, count, folders, levels - 1)
        return total_created

#.
#   .--Auditlog------------------------------------------------------------.
#   |                    _                 __ _ _                          |
#   |                   | |    ___   __ _ / _(_) | ___                     |
#   |                   | |   / _ \ / _` | |_| | |/ _ \                    |
#   |                   | |__| (_) | (_| |  _| | |  __/                    |
#   |                   |_____\___/ \__, |_| |_|_|\___|                    |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Handling of the audit logfiles                                       |
#   '----------------------------------------------------------------------'

class ModeAuditLog(WatoMode):
    log_path = audit_log_path

    def __init__(self):
        self._options  = self._vs_audit_log_options().default_value()
        super(ModeAuditLog, self).__init__()


    def title(self):
        return _("Audit log")


    def buttons(self):
        changelog_button()
        home_button()
        if self._log_exists() and config.user.may("wato.auditlog") and config.user.may("wato.edit"):
            html.context_button(_("Download"),
                html.makeactionuri([("_action", "csv")]), "download")
            if config.user.may("wato.edit"):
                html.context_button(_("Clear Log"),
                    html.makeactionuri([("_action", "clear")]), "trash")


    def _log_exists(self):
        return os.path.exists(self.log_path)


    def action(self):
        if html.var("_action") == "clear":
            config.user.need_permission("wato.auditlog")
            config.user.need_permission("wato.edit")
            return self._clear_audit_log_after_confirm()

        vs_options = self._vs_audit_log_options()
        value = vs_options.from_html_vars("options")
        vs_options.validate_value(value, "options")
        self._options = value

        if html.var("_action") == "csv":
            config.user.need_permission("wato.auditlog")
            return self._export_audit_log()


    def page(self):
        audit = self._parse_audit_log()

        if not audit:
            html.show_info(_("The audit log is empty."))

        elif self._options["display"] == "daily":
            self._display_daily_audit_log(audit)

        else:
            self._display_multiple_days_audit_log(audit)


    def _display_daily_audit_log(self, log):
        log, times = self._get_next_daily_paged_log(log)

        self._display_audit_log_options()

        self._display_page_controls(*times)

        if display_options.enabled(display_options.T):
            html.h3(_("Audit log for %s") % render.date(times[0]))

        self._display_log(log)

        self._display_page_controls(*times)


    def _display_multiple_days_audit_log(self, log):
        log = self._get_multiple_days_log_entries(log)

        self._display_audit_log_options()

        if display_options.enabled(display_options.T):
            html.h3(_("Audit log for %s and %d days ago") %
                    (render.date(self._get_start_date()),
                    self._options["display"][1]))

        self._display_log(log)


    def _display_log(self, log):
        table.begin(css="data wato auditlog audit", limit=None,
                    sortable=False, searchable=False)
        even = "even"
        for t, linkinfo, user, action, text in log:
            table.row()
            table.cell(_("Object"), self._render_logfile_linkinfo(linkinfo))
            table.cell(_("Time"), html.render_nobr(render.date_and_time(float(t))))
            user = user == '-' and ('<i>%s</i>' % _('internal')) or user
            table.cell(_("User"), html.attrencode(user), css="nobreak")

            # This must not be attrencoded: The entries are encoded when writing to the log.
            table.cell(_("Change"), text.replace("\\n", "<br>\n"), css="fill")
        table.end()


    def _get_next_daily_paged_log(self, log):
        start = self._get_start_date()

        while True:
            log_today, times = self._paged_log_from(log, start)
            if len(log) == 0 or len(log_today) > 0:
                return log_today, times
            else: # No entries today, but log not empty -> go back in time
                start -= 24 * 3600


    def _get_start_date(self):
        if self._options["start"] == "now":
            return int(time.time()) / 86400 * 86400
        else:
            return int(self._options["start"][1])


    def _get_multiple_days_log_entries(self, log):
        start_time = self._get_start_date() + 86399
        end_time   = start_time \
                     - ((self._options["display"][1] * 86400) + 86399)

        logs = []

        for entry in log:
            if entry[0] <= start_time and entry[0] >= end_time:
                logs.append(entry)

        return logs


    def _paged_log_from(self, log, start):
        start_time, end_time = self._get_timerange(start)
        previous_log_time = None
        next_log_time     = None
        first_log_index   = None
        last_log_index    = None
        for index, (t, linkinfo, user, action, text) in enumerate(log):
            if t >= end_time:
                # This log is too new
                continue
            elif first_log_index is None \
                  and t < end_time \
                  and t >= start_time:
                # This is a log for this day. Save the first index
                if first_log_index is None:
                    first_log_index = index

                    # When possible save the timestamp of the previous log
                    if index > 0:
                        next_log_time = int(log[index - 1][0])

            elif t < start_time and last_log_index is None:
                last_log_index = index
                # This is the next log after this day
                previous_log_time = int(log[index][0])
                # Finished!
                break

        if last_log_index is None:
            last_log_index = len(log)

        return log[first_log_index:last_log_index], (start_time, end_time, previous_log_time, next_log_time)


    def _display_page_controls(self, start_time, end_time, previous_log_time, next_log_time):
        html.open_div(class_="paged_controls")

        def time_url_args(t):
            return [
                ("options_p_start_1_day",   time.strftime("%d", time.localtime(t))),
                ("options_p_start_1_month", time.strftime("%m", time.localtime(t))),
                ("options_p_start_1_year",  time.strftime("%Y", time.localtime(t))),
                ("options_p_start_sel",     "1"),
            ]

        if next_log_time is not None:
            html.icon_button(html.makeactionuri([
                ("options_p_start_sel", "0"),
            ]), _("Most recent events"), "start")

            html.icon_button(html.makeactionuri(time_url_args(next_log_time)),
               "%s: %s" % (_("Newer events"), render.date(next_log_time)),
               "back")
        else:
            html.empty_icon_button()
            html.empty_icon_button()

        if previous_log_time is not None:
            html.icon_button(html.makeactionuri(time_url_args(previous_log_time)),
                "%s: %s" % (_("Older events"), render.date(previous_log_time)),
                "forth")
        else:
            html.empty_icon_button()

        html.close_div()


    def _get_timerange(self, t):
        st    = time.localtime(int(t))
        start = int(time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
        end   = start + 86399
        return start, end


    def _display_audit_log_options(self):
        if display_options.disabled(display_options.C):
            return

        valuespec = self._vs_audit_log_options()

        html.begin_form("options", method="GET")
        valuespec.render_input("options", {}, form=True)

        html.button("options", _("Apply"))
        html.hidden_fields()
        html.end_form()


    def _vs_audit_log_options(self):
        return Dictionary(
            title = _("Options"),
            elements = [
                ("filter_regex", RegExp(
                    title = _("Filter pattern (RegExp)"),
                    mode = "infix",
                )),
                ("start", CascadingDropdown(
                    title = _("Start log from"),
                    default_value = "now",
                    orientation = "horizontal",
                    choices = [
                        ("now",  _("Current date")),
                        ("time", _("Specific date"), AbsoluteDate()),
                    ],
                )),
                ("display", CascadingDropdown(
                    title = _("Display mode of entries"),
                    default_value = "daily",
                    orientation = "horizontal",
                    choices = [
                        ("daily",          _("Daily paged display")),
                        ("number_of_days", _("Number of days from now (single page)"), Integer(
                            minval = 1,
                            unit = _("days"),
                            default_value = 1,
                            allow_empty = False,
                        )),
                    ],
                )),
            ],
            optional_keys = [],
        )


    def _clear_audit_log_after_confirm(self):
        c = wato_confirm(_("Confirm deletion of audit log"),
                         _("Do you really want to clear the audit log?"))
        if c:
            self._clear_audit_log()
            return None, _("Cleared audit log.")
        elif c == False: # not yet confirmed
            return ""
        else:
            return None # browser reload


    def _clear_audit_log(self):
        if not os.path.exists(self.log_path):
            return

        newpath = self.log_path + time.strftime(".%Y-%m-%d")
        if os.path.exists(newpath):
            n = 1
            while True:
                n += 1
                with_num = newpath + "-%d" % n
                if not os.path.exists(with_num):
                    newpath = with_num
                    break

        os.rename(self.log_path, newpath)



    def _render_logfile_linkinfo(self, linkinfo):
        if ':' in linkinfo: # folder:host
            path, host_name = linkinfo.split(':', 1)
            if Folder.folder_exists(path):
                folder = Folder.folder(path)
                if host_name:
                    if folder.has_host(host_name):
                        host = folder.host(host_name)
                        url = host.edit_url()
                        title = host_name
                    else:
                        return host_name
                else: # only folder
                    url = folder.url()
                    title = folder.title()
            else:
                return linkinfo
        else:
            return ""

        return '<a href="%s">%s</a>' % (url, html.attrencode(title))


    def _export_audit_log(self):
        html.set_output_format("csv")

        if self._options["display"] == "daily":
            filename = "wato-auditlog-%s_%s.csv" % (render.date(time.time()), render.time_of_day(time.time()))
        else:
            filename = "wato-auditlog-%s_%s_days.csv" % (render.date(time.time()), self._options["display"][1])
        html.write(filename)

        html.req.headers_out['Content-Disposition'] = 'attachment; filename=%s' % filename

        titles = (
            _('Date'),
            _('Time'),
            _('Linkinfo'),
            _('User'),
            _('Action'),
            _('Text'),
        )
        html.write(','.join(titles) + '\n')
        for t, linkinfo, user, action, text in self._parse_audit_log():
            if linkinfo == '-':
                linkinfo = ''

            if self._filter_entry(user, action, text):
                continue

            html.write_text(','.join((render.date(int(t)), render.time_of_day(int(t)), linkinfo,
                                 user, action, '"' + text + '"')) + '\n')
        return False


    def _parse_audit_log(self):
        if not os.path.exists(self.log_path):
            return []

        entries = []
        for line in file(self.log_path):
            line = line.rstrip().decode("utf-8")
            splitted = line.split(None, 4)

            if len(splitted) == 5 and splitted[0].isdigit():
                splitted[0] = int(splitted[0])

                user, action, text = splitted[2:]
                if self._filter_entry(user, action, text):
                    continue

                entries.append(splitted)

        entries.reverse()

        return entries


    def _filter_entry(self, user, action, text):
        if not self._options["filter_regex"]:
            return False

        for val in [user, action, text]:
            if re.search(self._options["filter_regex"], val):
                return False

        return True


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


class ModeActivateChanges(WatoMode, ActivateChanges):
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
            html.context_button(_("Site Configuration"), folder_preserving_link([("mode", "sites")]), "sites")

        if config.user.may("wato.auditlog"):
            html.context_button(_("Audit Log"), folder_preserving_link([("mode", "auditlog")]), "auditlog")


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
            domains=ConfigDomain.enabled_domains(),
            need_restart=True)

        self._extract_snapshot(file_to_restore)
        execute_activate_changes([ d.ident for d in ConfigDomain.enabled_domains() ])

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
        self._extract_from_file(snapshot_dir + snapshot_file, backup_domains)


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
            status = get_snapshot_status(snapshot_file)
            if status['type'] == 'automatic' and not status['broken']:
                return snapshot_file


    # TODO: Remove once new changes mechanism has been implemented
    def _get_snapshots(self):
        snapshots = []
        try:
            for f in os.listdir(snapshot_dir):
                if os.path.isfile(snapshot_dir + f):
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
            host = Host.host(ident)
            if host:
                url = host.edit_url()
                title = host.name()

        elif ty == "Folder":
            if Folder.folder_exists(ident):
                folder = Folder.folder(ident)
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
                edit_url = folder_preserving_link([("mode", "edit_site"), ("edit", site_id)])
                html.icon_button(edit_url, _("Edit the properties of this site"), "edit")

            # State
            if can_activate_all and need_sync:
                html.icon_button(url="javascript:void(0)",
                    id="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    help=_("This site is not update and needs a replication. Start it now."),
                    icon="need_replicate",
                    onclick="activate_changes(\"site\", \"%s\")" % site_id, ty="icon")

            if can_activate_all and need_restart:
                html.icon_button(url="javascript:void(0)",
                    id="activate_%s" % site_id,
                    cssclass=["activate_site"],
                    help=_("This site needs a restart for activating the changes. Start it now."),
                    icon="need_restart",
                    onclick="activate_changes(\"site\", \"%s\")" % site_id, ty="icon")

            if can_activate_all and not need_action:
                html.icon(_("This site is up-to-date."), "siteuptodate")

            site_url = site.get("multisiteurl")
            if site_url:
                html.icon_button(site_url, _("Open this site's local web user interface"), "url", target="_blank")

            table.cell(_("Site"), site.get("alias", site_id))

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

        manager = ActivateChangesManager()
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

        manager = ActivateChangesManager()
        manager.load()
        manager.load_activation(activation_id)

        return manager.get_state()



def do_activate_changes_automation():
    verify_slave_site_config(html.var("site_id"))

    try:
        domains = ast.literal_eval(html.var("domains"))
    except SyntaxError:
        raise MKAutomationException(_("Garbled automation response: '%s'") % html.var("domains"))

    return execute_activate_changes(domains)


automation_commands["activate-changes"] = do_activate_changes_automation

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
        termvars = finishvars;

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
    finish_url = folder_preserving_link([("mode", "folder")] + finishvars)
    term_url = folder_preserving_link([("mode", "folder")] + termvars)

    # Reserve a certain amount of transids for the progress scheduler
    # Each json item requires one transid. Additionally, each "Retry failed hosts" eats
    # up another one. We reserve 20 additional transids for the retry function
    # Note: The "retry option" ignores the bulk size
    transids = []
    for i in range(len(items) + 20):
        transids.append(html.fresh_transid())

    html.javascript(('progress_scheduler("%s", "%s", 50, %s, %s, "%s", %s, %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json.dumps(items), json.dumps(transids), finish_url,
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


class SiteBackupJobs(backup.Jobs):
    def __init__(self):
        super(SiteBackupJobs, self).__init__(backup.site_config_path())


    def _apply_cron_config(self):
        p = subprocess.Popen(["omd", "restart", "crontab"],
                         close_fds=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, stdin=open(os.devnull))
        if p.wait() != 0:
            raise MKGeneralException(_("Failed to apply the cronjob config: %s") % p.stderr.read())



class SiteBackupTargets(backup.Targets):
    def __init__(self):
        super(SiteBackupTargets, self).__init__(backup.site_config_path())



class ModeBackup(backup.PageBackup, WatoMode):
    def title(self):
        return _("Site backup")


    def jobs(self):
        return SiteBackupJobs()


    def keys(self):
        return SiteBackupKeypairStore()


    def home_button(self):
        home_button()



class ModeBackupTargets(backup.PageBackupTargets, WatoMode):
    def __init__(self):
        super(ModeBackupTargets, self).__init__()


    def title(self):
        return _("Site backup targets")


    def targets(self):
        return SiteBackupTargets()


    def jobs(self):
        return SiteBackupJobs()


    def page(self):
        self.targets().show_list()
        backup.SystemBackupTargetsReadOnly().show_list(editable=False, title=_("System global targets"))



class ModeEditBackupTarget(backup.PageEditBackupTarget, WatoMode):
    def targets(self):
        return SiteBackupTargets()



class ModeEditBackupJob(backup.PageEditBackupJob, WatoMode):
    def jobs(self):
        return SiteBackupJobs()


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



class ModeBackupJobState(backup.PageBackupJobState, WatoMode):
    def jobs(self):
        return SiteBackupJobs()



class ModeAjaxBackupJobState(WatoMode):
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



class ModeBackupKeyManagement(SiteBackupKeypairStore, backup.PageBackupKeyManagement, WatoMode):
    def jobs(self):
        return SiteBackupJobs()



class ModeBackupEditKey(SiteBackupKeypairStore, backup.PageBackupEditKey, WatoMode):
    pass


class ModeBackupUploadKey(SiteBackupKeypairStore, backup.PageBackupUploadKey, WatoMode):
    def _upload_key(self, key_file, value):
        log_audit(None, "upload-backup-key",
                  _("Uploaded backup key '%s'") % value["alias"])
        super(ModeBackupUploadKey, self)._upload_key(key_file, value)


class ModeBackupDownloadKey(SiteBackupKeypairStore, backup.PageBackupDownloadKey, WatoMode):
    def _file_name(self, key_id, key):
        return "Check_MK-%s-%s-backup_key-%s.pem" % (backup.hostname(), config.omd_site(), key_id)


class ModeBackupRestore(backup.PageBackupRestore, WatoMode):
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


class CheckTypeSelection(DualListChoice):
    def __init__(self, **kwargs):
        DualListChoice.__init__(self, rows=25, **kwargs)

    def get_elements(self):
        checks = check_mk_local_automation("get-check-information")
        elements = [ (cn, (cn + " - " + c["title"])[:60]) for (cn, c) in checks.items()]
        elements.sort()
        return elements


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

def mode_main(phase):
    if phase == "title":
        return _("WATO - Check_MK's Web Administration Tool")

    elif phase == "buttons":
        changelog_button()
        return

    elif phase == "action":
        return

    render_main_menu(modules)

def render_main_menu(some_modules, columns = 2):
    html.open_div(class_="mainmenu")
    for nr, (mode_or_url, title, icon, permission, subtitle) in enumerate(some_modules):
        if permission:
            if "." not in permission:
                permission = "wato." + permission
            if not config.user.may(permission) and not config.user.may("wato.seeall"):
                continue

        if '?' in mode_or_url or '/' in mode_or_url or mode_or_url.endswith(".py"):
            url = mode_or_url
        else:
            url = folder_preserving_link([("mode", mode_or_url)])

        html.open_a(href=url, onfocus="if (this.blur) this.blur();")
        html.img("images/icon_%s.png" % icon)
        html.div(title, class_="title")
        html.div(subtitle, class_="subtitle")
        html.close_a()

    html.close_div()

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

def add_ldap_change(action_name, text):
    add_change(action_name, text, domains=[ConfigDomainGUI],
        sites=get_login_sites())


def mode_ldap_config(phase):
    title = _("LDAP Connections")

    if phase == "title":
        return title

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Users"), folder_preserving_link([("mode", "users")]), "users")
        html.context_button(_("New Connection"), folder_preserving_link([("mode", "edit_ldap_connection")]), "new")
        return

    connections = userdb.load_connection_config()
    if phase == "action":
        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            connection = connections[nr]
            c = wato_confirm(_("Confirm deletion of LDAP connection"),
                             _("Do you really want to delete the LDAP connection <b>%s</b>?") %
                               (connection["id"]))
            if c:
                add_ldap_change("delete-ldap-connection",
                    _("Deleted LDAP connection %s") % (connection["id"]))
                del connections[nr]
                userdb.save_connection_config(connections)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                connection = connections[from_pos]
                add_ldap_change("move-ldap-connection",
                    _("Changed position of LDAP connection %s to %d") % (connection["id"], to_pos))
                del connections[from_pos] # make to_pos now match!
                connections[to_pos:to_pos] = [connection]
                userdb.save_connection_config(connections)
        return

    userdb.ldap_test_module()

    table.begin()
    for nr, connection in enumerate(connections):
        table.row()

        table.cell(_("Actions"), css="buttons")
        edit_url   = folder_preserving_link([("mode", "edit_ldap_connection"), ("id", connection["id"])])
        delete_url = make_action_link([("mode", "ldap_config"), ("_delete", nr)])
        drag_url   = make_action_link([("mode", "ldap_config"), ("_move", nr)])

        html.icon_button(edit_url, _("Edit this LDAP connection"), "edit")
        html.element_dragger("tr", base_url=drag_url)
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


def validate_ldap_connection_id(value, varprefix):
    if value in [ c['id'] for c in config.user_connections ]:
        raise MKUserError(varprefix, _("This ID is already user by another connection. Please choose another one."))


def vs_ldap_connection(new, connection_id):
    general_elements = []

    if new:
        id_element = ("id", TextAscii(
            title = _("ID"),
            help = _("The ID of the connection must be a unique text. It will be used as an internal key "
                     "when objects refer to the connection."),
            allow_empty = False,
            size = 12,
            validate = validate_ldap_connection_id,
        ))
    else:
        id_element = ("id", FixedValue(connection_id,
            title = _("ID"),
        ))

    general_elements += [ id_element ]

    if cmk.is_managed_edition():
        general_elements += managed.customer_choice_element()

    general_elements += rule_option_elements()

    connection_elements = [
        ("server", TextAscii(
            title = _("LDAP Server"),
            help = _("Set the host address of the LDAP server. Might be an IP address or "
                     "resolvable hostname."),
            allow_empty = False,
            attrencode = True,
        )),
        ('failover_servers', ListOfStrings(
            title = _('Failover Servers'),
            help = _('When the connection to the first server fails with connect specific errors '
                     'like timeouts or some other network related problems, the connect mechanism '
                     'will try to use this server instead of the server configured above. If you '
                     'use persistent connections (default), the connection is being used until the '
                     'LDAP is not reachable or the local webserver is restarted.'),
            allow_empty = False,
        )),
        ("directory_type", DropdownChoice(
            title = _("Directory Type"),
            help  = _("Select the software the LDAP directory is based on. Depending on "
                      "the selection e.g. the attribute names used in LDAP queries will "
                      "be altered."),
            choices = [
                ("ad",                 _("Active Directory")),
                ("openldap",           _("OpenLDAP")),
                ("389directoryserver", _("389 Directory Server")),
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
            help   = _("Connect to the LDAP server with a SSL encrypted connection. You might need "
                       "to configure the OpenLDAP installation on your monitoring server to accept "
                       "the certificates of the LDAP server. This is normally done via system wide "
                       "configuration of the CA certificate which signed the certificate of the LDAP "
                       "server. Please refer to the <a target=\"_blank\" "
                       "href=\"https://mathias-kettner.com/checkmk_multisite_ldap_integration.html\">"
                       "documentation</a> for details."),
            value  = True,
            totext = _("Encrypt the network connection using SSL."),
        )),
        ("no_persistent", FixedValue(
            title  = _("No persistent connection"),
            help   = _("The connection to the LDAP server is not persisted."),
            value  = True,
            totext = _("Don't use persistent LDAP connections."),
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
            regex = re.compile('^[A-Z0-9.-]+(?:\.[A-Z]{2,24})?$', re.I),
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
                     "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"),
            size = 80,
            default_value = lambda: userdb.ldap_filter_of_connection(connection_id, 'users', False),
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
            default_value = lambda: userdb.ldap_attr_of_connection(connection_id, 'user_id'),
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
            forth = lambda x: x == "skip" and "keep" or x
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
            default_value = lambda: userdb.ldap_filter_of_connection(connection_id, 'groups', False),
            attrencode = True,
        )),
        ("group_member", TextAscii(
            title = _("Member Attribute"),
            help  = _("The attribute used to identify users group memberships."),
            default_value = lambda: userdb.ldap_attr_of_connection(connection_id, 'member'),
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
            elements = lambda: userdb.ldap_attribute_plugins_elements(connection_id),
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

    return Dictionary(
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
            'no_persistent', 'port', 'use_ssl', 'bind', 'page_size', 'response_timeout', 'failover_servers',
            'user_filter', 'user_filter_group', 'user_id', 'lower_user_ids', 'connect_timeout', 'version',
            'group_filter', 'group_member', 'suffix',
        ],
        validate = validate_ldap_connection,
    )


def validate_ldap_connection(value, varprefix):
    for role_id, group_specs in value["active_plugins"].get("groups_to_roles", {}).items():
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


def mode_edit_ldap_connection(phase):
    connection_id = html.var("id")
    connections = userdb.load_connection_config()
    connection_cfg = {}
    if connection_id == None:
        new = True
    else:
        new = False
        for nr, c in enumerate(connections):
            if c['id'] == connection_id:
                connection_cfg = c
                connection_nr = nr
        if not connection_cfg:
            raise MKUserError(None, _("The given connection does not exist."))

    if phase == "title":
        if new:
            return _("Create new LDAP Connection")
        else:
            return _("Edit LDAP Connection: %s") % html.attrencode(connection_id)

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Back"), folder_preserving_link([("mode", "ldap_config")]), "back")
        return

    vs = vs_ldap_connection(new, connection_id)

    if phase == 'action':
        if not html.check_transaction():
            return

        connection_cfg = vs.from_html_vars("connection")
        vs.validate_value(connection_cfg, "connection")

        if new:
            connections.insert(0, connection_cfg)
            connection_id = connection_cfg["id"]
        else:
            connection_cfg["id"] = connection_id
            connections[connection_nr] = connection_cfg

        if new:
            log_what = "new-ldap-connection"
            log_text = _("Created new LDAP connection")
        else:
            log_what = "edit-ldap-connection"
            log_text = _("Changed LDAP connection %s") % connection_id
        add_ldap_change(log_what, log_text)

        userdb.save_connection_config(connections)
        config.user_connections = connections # make directly available on current page
        if html.var("_save"):
            return "ldap_config"
        else:
            # Fix the case where a user hit "Save & Test" during creation
            html.set_var('id', connection_id)
            return

    #
    # Regular page rendering
    #

    html.open_div(id_="ldap")
    html.open_table()
    html.open_tr()

    html.open_td()
    html.begin_form("connection", method="POST")
    html.prevent_password_auto_completion()
    vs.render_input("connection", connection_cfg)
    vs.set_focus("connection")
    html.button("_save", _("Save"))
    html.button("_test", _("Save & Test"))
    html.hidden_fields()
    html.end_form()
    html.close_td()

    html.open_td(style="padding-left:10px;")
    html.h2(_('Diagnostics'))
    if not html.var('_test') or not connection_id:
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
        def test_connect(connection, address):
            conn, msg = connection.connect_server(address)
            if conn:
                return (True, _('Connection established. The connection settings seem to be ok.'))
            else:
                return (False, msg)

        def test_user_base_dn(connection, address):
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

        def test_user_count(connection, address):
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

        def test_group_base_dn(connection, address):
            if not connection.has_group_base_dn_configured():
                return (False, _('The Group Base DN is not configured, not fetching any groups.'))
            connection.connect(enforce_new = True, enforce_server = address)
            if connection.group_base_dn_exists():
                return (True, _('The Group Base DN could be found.'))
            else:
                return (False, _('The Group Base DN could not be found.'))

        def test_group_count(connection, address):
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

        def test_groups_to_roles(connection, address):
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

        tests = [
            (_('Connection'),          test_connect),
            (_('User Base-DN'),        test_user_base_dn),
            (_('Count Users'),         test_user_count),
            (_('Group Base-DN'),       test_group_base_dn),
            (_('Count Groups'),        test_group_count),
            (_('Sync-Plugin: Roles'),  test_groups_to_roles),
        ]

        connection = userdb.get_connection(connection_id)
        for address in connection.servers():
            html.h3("%s: %s" % (_('Server'), address))
            table.begin('test', searchable = False)

            for title, test_func in tests:
                table.row()
                try:
                    state, msg = test_func(connection, address)
                except Exception, e:
                    state = False
                    msg = _('Exception: %s') % html.attrencode(e)

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

def mode_globalvars(phase):
    search = get_search_expression()

    if phase == "title":
        if search:
            return _("Global Settings matching %s") % html.attrencode(search)
        else:
            return _("Global Settings")

    elif phase == "buttons":
        global_buttons()

        if config.user.may("wato.set_read_only"):
            html.context_button(_("Read only mode"), folder_preserving_link([("mode", "read_only")]), "read_only")

        if cmk.is_managed_edition():
            cme_global_settings_buttons()

        return

    # Get default settings of all configuration variables of interest in the domain
    # "check_mk". (this also reflects the settings done in main.mk)
    default_values = check_mk_local_automation("get-configuration", [], get_check_mk_config_var_names())
    current_settings = load_configuration_settings()

    if phase == "action":
        varname = html.var("_varname")
        action = html.var("_action")
        if varname:
            domain, valuespec, need_restart, allow_reset, in_global_settings = configvars()[varname]
            def_value = default_values.get(varname, valuespec.default_value())

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
                if varname in current_settings:
                    current_settings[varname] = not current_settings[varname]
                else:
                    current_settings[varname] = not def_value
                msg = _("Changed Configuration variable %s to %s.") % (varname,
                    current_settings[varname] and "on" or "off")
                save_global_settings(current_settings)

                add_change("edit-configvar", msg, domains=[domain],
                    need_restart=need_restart)

                if action == "_reset":
                    return "globalvars", msg
                else:
                    return "globalvars"
            elif c == False:
                return ""
            else:
                return None
        else:
            return

    group_names = global_config_variable_groups()
    render_global_configuration_variables(group_names, default_values, current_settings, search=search)


def global_config_variable_groups(show_all=False):
    group_names = []

    for group_name, group_vars in configvar_groups().items():
        add = False
        for domain, varname, valuespec in group_vars:
            if not show_all and (not configvars()[varname][4]
                                 or not domain.in_global_settings):
                continue # do not edit via global settings

            add = True
            break

        if add:
            group_names.append(group_name)

    return group_names


def render_global_configuration_variables(group_names, default_values, current_settings,
                                          search=None, edit_mode="edit_configvar"):

    group_names.sort(cmp=lambda a,b: cmp(configvar_order().get(a, 999),
                                         configvar_order().get(b, 999)))

    search_form(_("Search for settings:"))

    at_least_one_painted = False
    html.open_div(class_="globalvars")
    for group_name in group_names:
        header_is_painted = False # needed for omitting empty groups

        for domain, varname, valuespec in configvar_groups()[group_name]:
            if domain == ConfigDomainCore and varname not in default_values:
                if config.debug:
                    raise MKGeneralException("The configuration variable <tt>%s</tt> is unknown to "
                                          "your local Check_MK installation" % varname)
                else:
                    continue

            if not configvar_show_in_global_settings(varname):
                continue

            help_text  = valuespec.help() or ''
            title_text = valuespec.title()

            if search and search not in group_name.lower() \
                    and search not in domain.ident.lower() \
                      and search not in varname \
                      and search not in help_text.lower() \
                      and search not in title_text.lower():
                continue # skip variable when search is performed and nothing matches
            at_least_one_painted = True

            if not header_is_painted:
                # always open headers when searching
                forms.header(group_name, isopen=search)
                header_is_painted = True

            default_value = default_values.get(varname, valuespec.default_value())

            edit_url = folder_preserving_link([("mode", edit_mode),
                                               ("varname", varname),
                                               ("site", html.var("site", ""))])
            title = HTML('<a href="%s" class=%s title="%s">%s</a>' % \
                    (edit_url, varname in current_settings and '"modified"' or '""',
                     html.strip_tags(help_text), title_text))

            if varname in current_settings:
                to_text = valuespec.value_to_text(current_settings[varname])
            else:
                to_text = valuespec.value_to_text(default_value)

            # Is this a simple (single) value or not? change styling in these cases...
            simple = True
            if '\n' in to_text or '<td>' in to_text:
                simple = False
            forms.section(title, simple=simple)

            if varname in current_settings:
                value = current_settings[varname]
                modified_cls = "modified"
            else:
                value = default_value
                modified_cls = None

            if is_a_checkbox(valuespec):
                html.open_div(class_=["toggle_switch_container", modified_cls])
                html.toggle_switch(
                    enabled=value,
                    help=_("Immediately toggle this setting"),
                    href=html.makeactionuri([("_action", "toggle"), ("_varname", varname)]),
                    class_=modified_cls
                )
                html.close_div()

            else:
                html.a(HTML(to_text), href=edit_url, class_=modified_cls)

        if header_is_painted:
            forms.end()
    if not at_least_one_painted and search:
        html.message(_('Did not find any global setting matching your search.'))
    html.close_div()


def mode_edit_configvar(phase, what = 'globalvars'):
    siteid = html.var("site")
    if siteid:
        configured_sites = load_sites()
        site = configured_sites[siteid]

    if phase == "title":
        if what == 'mkeventd':
            return _("Event Console Configuration")
        elif siteid:
            return _("Site-specific global configuration for %s") % siteid
        else:
            return _("Global configuration settings for Check_MK")

    elif phase == "buttons":
        if what == 'mkeventd':
            html.context_button(_("Abort"), folder_preserving_link([("mode", "mkeventd_config")]), "abort")
        elif siteid:
            html.context_button(_("Abort"), folder_preserving_link([("mode", "edit_site_globals"), ("site", siteid)]), "abort")
        else:
            html.context_button(_("Abort"), folder_preserving_link([("mode", "globalvars")]), "abort")
        return

    varname = html.var("varname")
    try:
        domain, valuespec, need_restart, allow_reset, in_global_settings = configvars()[varname]
    except KeyError:
        raise MKGeneralException(_("The global setting \"%s\" does not exist.") % varname)

    if siteid:
        current_settings = site.setdefault("globals", {})
    else:
        current_settings = load_configuration_settings()

    is_on_default = varname not in current_settings

    if phase == "action":
        if html.var("_reset"):
            if not is_a_checkbox(valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset this configuration variable "
                      "back to its default value?"))
                if c == False:
                    return ""
                elif c == None:
                    return None
            elif not html.check_transaction():
                return

            try:
                del current_settings[varname]
            except KeyError:
                pass

            msg = _("Resetted configuration variable %s to its default.") % varname
        else:
            new_value = get_edited_value(valuespec)
            current_settings[varname] = new_value
            msg = HTML(_("Changed global configuration variable %s to %s.") \
                  % (varname, valuespec.value_to_text(new_value)))

        if what == 'mkeventd':
            need_restart = None

        if siteid:
            save_sites(configured_sites, activate=False)
            if siteid == config.omd_site():
                save_site_global_settings(current_settings)
            add_change("edit-configvar", msg, sites=[siteid], domains=[domain], need_restart=need_restart)

            return "edit_site_globals"
        else:
            save_global_settings(current_settings)

            sites = None
            if what == 'mkeventd':
                sites = get_event_console_sync_sites()

            add_change("edit-configvar", msg, domains=[domain], need_restart=need_restart, sites=sites)

            if what == 'mkeventd':
                return 'mkeventd_config'
            else:
                return "globalvars"

    check_mk_vars = check_mk_local_automation("get-configuration", [], [varname])

    if varname in current_settings:
        value = current_settings[varname]
    else:
        if siteid:
            globalsettings = load_configuration_settings()
            check_mk_vars.update(globalsettings)
        value = check_mk_vars.get(varname, valuespec.default_value())

    if siteid:
        defvalue = check_mk_vars.get(varname, valuespec.default_value())
    else:
        defvalue = valuespec.default_value()


    html.begin_form("value_editor", method="POST")
    forms.header(valuespec.title())
    if not config.wato_hide_varnames:
        forms.section(_("Configuration variable:"))
        html.tt(varname)

    forms.section(_("Current setting"))
    valuespec.render_input("ve", value)
    valuespec.set_focus("ve")
    html.help(valuespec.help())

    forms.section(_("Default setting"))
    if is_on_default:
        html.write_text(_("This variable is at factory settings."))
    else:
        curvalue = current_settings[varname]
        if curvalue == defvalue:
            html.write_text(_("Your setting and factory settings are identical."))
        else:
            html.write(valuespec.value_to_text(defvalue))

    forms.end()
    html.button("save", _("Save"))
    if allow_reset and not is_on_default:
        curvalue = current_settings[varname]
        html.button("_reset", curvalue == defvalue and _("Remove explicit setting") or _("Reset to default"))
    html.hidden_fields()
    html.end_form()



#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   | Mode for editing host-, service- and contact groups                  |
#   '----------------------------------------------------------------------'

class ModeGroups(WatoMode):
    type_name = None

    def __init__(self):
        super(ModeGroups, self).__init__()
        self._load_groups()


    def _load_groups(self):
        all_groups = userdb.load_group_information()
        self._groups = all_groups.setdefault(self.type_name, {})


    def buttons(self):
        global_buttons()


    def action(self):
        if html.var('_delete'):
            delname = html.var("_delete")
            usages = find_usages_of_group(delname, self.type_name)

            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this %s group.") % self.type_name,
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            confirm_txt = _('Do you really want to delete the %s group "%s"?') % (self.type_name, delname)

            c = wato_confirm(_("Confirm deletion of group \"%s\"") % delname, confirm_txt)
            if c:
                delete_group(delname, self.type_name)
                self._load_groups()
            elif c == False:
                return ""

        return None


    def _page_no_groups(self):
        html.div(_("No groups are defined yet."), class_="info")


    def _collect_additional_data(self):
        pass


    def _show_row_cells(self, name, group):
        table.cell(_("Actions"), css="buttons")
        edit_url   = folder_preserving_link([("mode", "edit_%s_group" % self.type_name), ("edit", name)])
        delete_url = html.makeactionuri([("_delete", name)])
        clone_url  = folder_preserving_link([("mode", "edit_%s_group" % self.type_name), ("clone", name)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy of this group"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), group['alias'])


    def page(self):
        sorted_groups = self._groups.items()
        sorted_groups.sort(cmp = lambda a,b: cmp(a[1]['alias'], b[1]['alias']))
        if len(sorted_groups) == 0:
            return self._page_no_groups()

        self._collect_additional_data()

        table.begin(self.type_name + "groups")
        for name, group in sorted_groups:
            table.row()
            self._show_row_cells(name, group)
        table.end()


class ModeEditGroup(WatoMode):
    type_name = None

    def __init__(self):
        super(ModeEditGroup, self).__init__()

        self.name    = None
        self._new    = False
        self._groups = {}
        self.group   = {}

        self._load_groups()
        self._from_vars()


    def _load_groups(self):
        all_groups = userdb.load_group_information()
        self._groups = all_groups.setdefault(self.type_name, {})


    def _from_vars(self):
        self.name = html.var("edit") # missing -> new group
        self._new = self.name == None

        if self._new:
            clone_group = html.var("clone")
            if clone_group:
                self.name = clone_group

                self.group = self._get_group(self.name)
            else:
                self.group = {}
        else:
            self.group = self._get_group(self.name)

        self.group.setdefault("alias", self.name)


    def _get_group(self, group_name):
        try:
            return self._groups[self.name]
        except KeyError:
            raise MKUserError(None, _("This group does not exist."))


    def buttons(self):
        html.context_button(_("All groups"),
            folder_preserving_link([("mode", "%s_groups" % self.type_name)]), "back")


    def _determine_additional_group_data(self):
        pass


    def action(self):
        if not html.check_transaction():
            return "%s_groups" % self.type_name

        alias = html.get_unicode_input("alias").strip()
        if not alias:
            raise MKUserError("alias", _("Please specify an alias name."))

        self.group = {
            "alias": alias
        }

        self._determine_additional_group_data()

        if self._new:
            self.name = html.var("name").strip()
            add_group(self.name, self.type_name, self.group)
        else:
            edit_group(self.name, self.type_name, self.group)

        return "%s_groups" % self.type_name


    def _show_extra_page_elements(self):
        pass


    def page(self):
        html.begin_form("group")
        forms.header(_("Properties"))
        forms.section(_("Name"), simple = not self._new)
        html.help(_("The name of the group is used as an internal key. It cannot be "
                     "changed later. It is also visible in the status GUI."))
        if self._new:
            html.text_input("name", self.name)
            html.set_focus("name")
        else:
            html.write_text(self.name)
            html.set_focus("alias")

        forms.section(_("Alias"))
        html.help(_("An Alias or description of this group."))
        html.text_input("alias", self.group["alias"])

        self._show_extra_page_elements()

        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()



class ModeHostgroups(ModeGroups):
    type_name = "host"

    def title(self):
        return _("Host Groups")


    def buttons(self):
        super(ModeHostgroups, self).buttons()
        html.context_button(_("Service groups"), folder_preserving_link([("mode", "service_groups")]), "hostgroups")
        html.context_button(_("New host group"), folder_preserving_link([("mode", "edit_host_group")]), "new")
        html.context_button(_("Rules"), folder_preserving_link([("mode", "edit_ruleset"), ("varname", "host_groups")]), "rulesets")



class ModeServicegroups(ModeGroups):
    type_name = "service"

    def title(self):
        return _("Service Groups")


    def buttons(self):
        super(ModeServicegroups, self).buttons()
        html.context_button(_("Host groups"), folder_preserving_link([("mode", "host_groups")]), "servicegroups")
        html.context_button(_("New service group"), folder_preserving_link([("mode", "edit_service_group")]), "new")
        html.context_button(_("Rules"), folder_preserving_link([("mode", "edit_ruleset"), ("varname", "service_groups")]), "rulesets")



class ModeContactgroups(ModeGroups):
    type_name = "contact"


    def title(self):
        self._members = {}
        return _("Contact Groups")


    def buttons(self):
        super(ModeContactgroups, self).buttons()
        html.context_button(_("New contact group"), folder_preserving_link([("mode", "edit_contact_group")]), "new")
        html.context_button(_("Rules"), folder_preserving_link([("mode", "rulesets"),
                             ("filled_in", "search"), ("search", _("contact group"))]), "rulesets")


    def _page_no_groups(self):
        render_main_menu([("edit_contact_group", _("Create new contact group"), "new",
         "users", _("Contact groups are needed for assigning hosts and services to people (contacts)"))])


    def _collect_additional_data(self):
        users = userdb.load_users()
        self._members = {}
        for userid, user in users.items():
            cgs = user.get("contactgroups", [])
            for cg in cgs:
                self._members.setdefault(cg, []).append((userid, user.get('alias', userid)))


    def _show_row_cells(self, name, group):
        super(ModeContactgroups, self)._show_row_cells(name, group)
        table.cell(_("Members"))
        html.write_html(HTML(", ").join(
           [ html.render_a(alias, href=folder_preserving_link([("mode", "edit_user"), ("edit", userid)]))
             for userid, alias in self._members.get(name, [])]))



class ModeEditServicegroup(ModeEditGroup):
    type_name = "service"

    def title(self):
        if self._new:
            return _("Create new service group")
        else:
            return _("Edit service group")



class ModeEditHostgroup(ModeEditGroup):
    type_name = "host"

    def title(self):
        if self._new:
            return _("Create new host group")
        else:
            return _("Edit host group")



class ModeEditContactgroup(ModeEditGroup):
    type_name = "contact"

    def title(self):
        if self._new:
            return _("Create new contact group")
        else:
            return _("Edit contact group")


    def _vs_nagvis_maps(self):
        return ListChoice(
            title = _('NagVis Maps'),
            choices = self._get_nagvis_maps,
            toggle_all = True,
        )


    def _get_nagvis_maps(self):
        # Find all NagVis maps in the local installation to register permissions
        # for each map. When no maps can be found skip this problem silently.
        # This only works in OMD environments.
        maps = []
        nagvis_maps_path = cmk.paths.omd_root + '/etc/nagvis/maps'
        for f in os.listdir(nagvis_maps_path):
            if f[0] != '.' and f.endswith('.cfg'):
                maps.append((f[:-4], f[:-4]))
        return maps


    def _determine_additional_group_data(self):
        super(ModeEditContactgroup, self)._determine_additional_group_data()
        permitted_maps = self._vs_nagvis_maps().from_html_vars('nagvis_maps')
        self._vs_nagvis_maps().validate_value(permitted_maps, 'nagvis_maps')
        if permitted_maps:
            self.group["nagvis_maps"] = permitted_maps


    def _show_extra_page_elements(self):
        super(ModeEditContactgroup, self)._show_extra_page_elements()
        # Show permissions for NagVis maps if any of those exist
        if self._get_nagvis_maps():
            forms.header(_("Permissions"))
            forms.section(_("Access to NagVis Maps"))
            html.help(_("Configure access permissions to NagVis maps."))
            self._vs_nagvis_maps().render_input('nagvis_maps', self.group.get('nagvis_maps', []))



class GroupSelection(ElementSelection):
    def __init__(self, what, **kwargs):
        kwargs.setdefault('empty_text', _('You have not defined any %s group yet. Please '
                                          '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.') %
                                                                                                    (what, what))
        ElementSelection.__init__(self, **kwargs)
        self._what = what
        # Allow to have "none" entry with the following title
        self._no_selection = kwargs.get("no_selection")

    def get_elements(self):
        all_groups = userdb.load_group_information()
        this_group = all_groups.get(self._what, {})
        # replace the title with the key if the title is empty
        elements = [ (k, t['alias'] and t['alias'] or k) for (k, t) in this_group.items() ]
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(('', self._no_selection))
        return dict(elements)



class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        ElementSelection.__init__(self, **kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = check_mk_local_automation("get-check-information")
        elements = dict([ (cn, "%s - %s" % (cn, c["title"])) for (cn, c) in checks.items()
                     if c.get("group") == self._checkgroup ])
        return elements

    def value_to_text(self, value):
        return "<tt>%s</tt>" % value



def FolderChoice(**kwargs):
    kwargs["choices"] = lambda: Folder.folder_choices()
    kwargs.setdefault("title", _("Folder"))
    return DropdownChoice(**kwargs)


def vs_notification_bulkby():
    return ListChoice(
      title = _("Create separate notification bulks based on"),
      choices = [
        ( "folder",     _("Folder") ),
        ( "host",       _("Host") ),
        ( "service",    _("Service description") ),
        ( "sl",         _("Service level") ),
        ( "check_type", _("Check type") ),
        ( "state",      _("Host/Service state") ),
        ( "ec_contact", _("Event console contact") ),
      ],
      default_value = [ "host" ],
    )

def vs_notification_scripts():
    return DropdownChoice(
       title = _("Notification Script"),
       choices = notification_script_choices,
       default_value = "mail"
    )


def vs_notification_rule(userid = None):
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
                  GroupSelection("contact"),
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
                  GroupSelection("contact"),
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

    return Dictionary(
        title = _("General Properties"),
        elements = rule_option_elements()
        + section_override
        + generic_rule_match_conditions()
        + event_rule_match_conditions(flavour="notify")
        + notification_rule_match_conditions()
        + section_contacts
        + [
            # Notification
            ( "notify_plugin",
              get_vs_notification_methods(),
            ),

            # ( "notify_method",
            #   Alternative(
            #       title = _("Parameters / Cancelling"),
            #       style = "dropdown",
            #       elements = [
            #           ListOfStrings(
            #               title = _("Call the script with the following parameters"),
            #               valuespec = TextUnicode(size = 24),
            #               orientation = "horizontal",
            #           ),
            #           FixedValue(
            #               value = None,
            #               title = _("Cancel all previous notifications with this method"),
            #               totext = "",
            #           ),
            #       ]
            #   )
            # ),

            ( "bulk",
              Dictionary(
                  title = _("Notification Bulking"),
                  help = _("Enabling the bulk notifications will collect several subsequent notifications "
                           "for the same contact into one single notification, which lists of all the "
                           "actual problems, e.g. in a single emails. This cuts down the number of notifications "
                           "in cases where many (related) problems occur within a short time."),
                  elements = [
                    ( "interval",
                      Age(
                          title = _("Time horizon"),
                          label = _("Bulk up to"),
                          help = _("Notifications are kept back for bulking at most for this time."),
                          default_value = 60,
                      )
                    ),
                    ( "count",
                      Integer(
                          title = _("Maximum bulk size"),
                          label = _("Bulk up to"),
                          unit  = _("Notifications"),
                          help = _("At most that many Notifications are kept back for bulking. A value of "
                                   "1 essentially turns off notification bulking."),
                          default_value = 1000,
                          minvalue = 1,
                      ),
                    ),
                    ( "groupby",
                      vs_notification_bulkby(),
                    ),
                    ( "groupby_custom",
                      ListOfStrings(
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
                  ],
                  columns = 1,
                  optional_keys = False,
            ),
          ),

        ],
        optional_keys = [ "match_folder", "match_hosttags", "match_hostgroups", "match_hosts", "match_exclude_hosts",
                          "match_servicegroups", "match_exclude_servicegroups", "match_servicegroups_regex", "match_exclude_servicegroups_regex",
                          "match_services", "match_exclude_services",
                          "match_contacts", "match_contactgroups",
                          "match_plugin_output",
                          "match_timeperiod", "match_escalation", "match_escalation_throttle",
                          "match_sl", "match_host_event", "match_service_event", "match_ec", "match_notification_comment",
                          "match_checktype", "bulk", "contact_users", "contact_groups", "contact_emails",
                          "contact_match_macros", "contact_match_groups" ],
        headers = [
            ( _("General Properties"), [ "description", "comment", "disabled", "docu_url", "allow_disable" ] ),
            ( _("Notification Method"), [ "notify_plugin", "notify_method", "bulk" ] ),]
            + contact_headers
            + [
            ( _("Conditions"),         [ "match_folder", "match_hosttags", "match_hostgroups",
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
        validate = validate_notification_rule,
    )

def simple_host_rule_match_conditions():
    return [
        ( "match_folder",
          FolderChoice(
              title = _("Match folder"),
              help = _("This condition makes the rule match only hosts that are managed "
                       "via WATO and that are contained in this folder - either directly "
                       "or in one of its subfolders."),
          ),
        ),
        ( "match_hosttags",
          HostTagCondition(
              title = _("Match Host Tags"))
        ),
        ( "match_hostgroups",
          userdb.GroupChoice("host",
              title = _("Match Host Groups"),
              help = _("The host must be in one of the selected host groups"),
              allow_empty = False,
          )
        ),
        ( "match_hosts",
          ListOfStrings(
              title = _("Match only the following hosts"),
              size = 24,
              orientation = "horizontal",
              allow_empty = False,
              empty_text = _("Please specify at least one host. Disable the option if you want to allow all hosts."),
          )
        ),
        ( "match_exclude_hosts",
          ListOfStrings(
              title = _("Exclude the following hosts"),
              size = 24,
              orientation = "horizontal",
          )
        ),
    ]


def generic_rule_match_conditions():
    return simple_host_rule_match_conditions() + [
        ( "match_servicegroups",
          userdb.GroupChoice("service",
              title = _("Match Service Groups"),
              help = _("The service must be in one of the selected service groups. For host events this condition "
                       "never matches as soon as at least one group is selected."),
              allow_empty = False,
          )
        ),
        ( "match_exclude_servicegroups",
          userdb.GroupChoice("service",
              title = _("Exclude Service Groups"),
              help = _("The service must not be in one of the selected service groups. For host events this condition "
                       "is simply ignored."),
              allow_empty = False,
          )
        ),
        ( "match_servicegroups_regex",
          Tuple(
                title = _("Match Service Groups (regex)"),
                elements = [
                DropdownChoice(
                    choices = [
                        ( "match_id",    _("Match the internal identifier")),
                        ( "match_alias", _("Match the alias"))
                    ],
                    default = "match_id"
                  ),
                  ListOfStrings(
                      help = _("The service group alias must match one of the following regular expressions."
                               " For host events this condition never matches as soon as at least one group is selected."),
                      valuespec = RegExpUnicode(
                          size = 32,
                          mode = RegExpUnicode.infix,
                      ),
                      orientation = "horizontal",
                  )
                ]
          )
        ),
        ( "match_exclude_servicegroups_regex",
          Tuple(
                title = _("Exclude Service Groups (regex)"),
                elements = [
                  DropdownChoice(
                    choices = [
                        ( "match_id",    _("Match the internal identifier")),
                        ( "match_alias", _("Match the alias"))
                    ],
                    default = "match_id"
                  ),
                  ListOfStrings(
                      help = _("The service group alias must not match one of the following regular expressions. "
                               "For host events this condition is simply ignored."),
                      valuespec = RegExpUnicode(
                          size = 32,
                          mode = RegExpUnicode.infix,
                      ),
                      orientation = "horizontal",
                  )
                ]
          )
        ),
        ( "match_services",
          ListOfStrings(
              title = _("Match only the following services"),
              help = _("Specify a list of regular expressions that must match the <b>beginning</b> of the "
                       "service name in order for the rule to match. Note: Host notifications never match this "
                       "rule if this option is being used."),
              valuespec = RegExpUnicode(
                  size = 32,
                  mode = RegExpUnicode.prefix,
              ),
              orientation = "horizontal",
              allow_empty = False,
              empty_text = _("Please specify at least one service regex. Disable the option if you want to allow all services."),
          )
        ),
        ( "match_exclude_services",
          ListOfStrings(
              title = _("Exclude the following services"),
              valuespec = RegExpUnicode(
                  size = 32,
                  mode = RegExpUnicode.prefix,
              ),
              orientation = "horizontal",
          )
        ),
        # BEWARE: If you add further match conditions here, you might have to adjust
        # the the number in the_alert_handlers.py:ModeAlertHandlerRule._alert_handler_conditions
        ( "match_checktype",
          CheckTypeSelection(
              title = _("Match the following check types"),
              help = _("Only apply the rule if the notification originates from certain types of check plugins. "
                       "Note: Host notifications never match this rule if this option is being used."),
          )
        ),
        ( "match_plugin_output",
          RegExp(
             title = _("Match the output of the check plugin"),
             help = _("This text is a regular expression that is being searched in the output "
                      "of the check plugins that produced the alert. It is not a prefix but an infix match."),
             mode = RegExpUnicode.prefix,
          ),
        ),
        ( "match_contacts",
          ListOf(
              UserSelection(only_contacts = True),
                  title = _("Match Contacts"),
                  help = _("The host/service must have one of the selected contacts."),
                  movable = False,
                  allow_empty = False,
                  add_label = _("Add contact"),
          )
        ),
        ( "match_contactgroups",
          userdb.GroupChoice("contact",
              title = _("Match Contact Groups"),
              help = _("The host/service must be in one of the selected contact groups. This only works with Check_MK Micro Core. " \
                       "If you don't use the CMC that filter will not apply"),
              allow_empty = False,
          )
        ),
        ( "match_sl",
          Tuple(
            title = _("Match service level"),
            help = _("Host or service must be in the following service level to get notification"),
            orientation = "horizontal",
            show_titles = False,
            elements = [
              DropdownChoice(label = _("from:"),  choices = service_levels, prefix_values = True),
              DropdownChoice(label = _(" to:"),  choices = service_levels, prefix_values = True),
            ],
          ),
        ),
        ( "match_timeperiod",
          TimeperiodSelection(
              title = _("Match only during timeperiod"),
              help = _("Match this rule only during times where the selected timeperiod from the monitoring "
                       "system is active."),
          ),
        ),
    ]


# flavour = "notify" or "alert"
def event_rule_match_conditions(flavour):
    if flavour == "notify":
        add_choices = [
            ( 'f', _("Start or end of flapping state")),
            ( 's', _("Start or end of a scheduled downtime")),
            ( 'x', _("Acknowledgement of problem")),
            ( 'as', _("Alert handler execution, successful")),
            ( 'af', _("Alert handler execution, failed")),
        ]
        add_default = [ 'f', 's', 'x', 'as', 'af' ]
    else:
        add_choices = []
        add_default = []

    return [
       ( "match_host_event",
          ListChoice(
               title = _("Match host event type"),
               help = _("Select the host event types and transitions this rule should handle. Note: "
                        "If you activate this option and do <b>not</b> also specify service event "
                        "types then this rule will never hold for service notifications!"),
               choices = [
                   ( 'rd', _("UP")          + u" ➤ " + _("DOWN")),
                   ( 'ru', _("UP")          + u" ➤ " + _("UNREACHABLE")),

                   ( 'dr', _("DOWN")        + u" ➤ " + _("UP")),
                   ( 'du', _("DOWN")        + u" ➤ " + _("UNREACHABLE")),

                   ( 'ud', _("UNREACHABLE") + u" ➤ " + _("DOWN")),
                   ( 'ur', _("UNREACHABLE") + u" ➤ " + _("UP")),

                   ( '?r', _("any")         + u" ➤ " + _("UP")),
                   ( '?d', _("any")         + u" ➤ " + _("DOWN")),
                   ( '?u', _("any")         + u" ➤ " + _("UNREACHABLE")),
               ] + add_choices,
               default_value = [ 'rd', 'dr', ] + add_default,
         )
       ),
       ( "match_service_event",
           ListChoice(
               title = _("Match service event type"),
                help  = _("Select the service event types and transitions this rule should handle. Note: "
                          "If you activate this option and do <b>not</b> also specify host event "
                          "types then this rule will never hold for host notifications!"),
               choices = [
                   ( 'rw', _("OK")      + u" ➤ " + _("WARN")),
                   ( 'rr', _("OK")      + u" ➤ " + _("OK")),

                   ( 'rc', _("OK")      + u" ➤ " + _("CRIT")),
                   ( 'ru', _("OK")      + u" ➤ " + _("UNKNOWN")),

                   ( 'wr', _("WARN")    + u" ➤ " + _("OK")),
                   ( 'wc', _("WARN")    + u" ➤ " + _("CRIT")),
                   ( 'wu', _("WARN")    + u" ➤ " + _("UNKNOWN")),

                   ( 'cr', _("CRIT")    + u" ➤ " + _("OK")),
                   ( 'cw', _("CRIT")    + u" ➤ " + _("WARN")),
                   ( 'cu', _("CRIT")    + u" ➤ " + _("UNKNOWN")),

                   ( 'ur', _("UNKNOWN") + u" ➤ " + _("OK")),
                   ( 'uw', _("UNKNOWN") + u" ➤ " + _("WARN")),
                   ( 'uc', _("UNKNOWN") + u" ➤ " + _("CRIT")),

                   ( '?r', _("any") + u" ➤ " + _("OK")),
                   ( '?w', _("any") + u" ➤ " + _("WARN")),
                   ( '?c', _("any") + u" ➤ " + _("CRIT")),
                   ( '?u', _("any") + u" ➤ " + _("UNKNOWN")),

               ] + add_choices,
               default_value = [ 'rw', 'rc', 'ru', 'wc', 'wu', 'uc', ] + add_default,
          )
        ),
    ]


def notification_rule_match_conditions():
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
                      "25.. and so on."),
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


def validate_notification_rule(rule, varprefix):
    if "bulk" in rule and rule["notify_plugin"][1] == None:
        raise MKUserError(varprefix + "_p_bulk_USE",
             _("It does not make sense to add a bulk configuration for cancelling rules."))

    if "bulk" in rule:
        if rule["notify_plugin"][0]:
            info = load_notification_scripts()[rule["notify_plugin"][0]]
            if not info["bulk"]:
                raise MKUserError(varprefix + "_p_notify_plugin",
                      _("The notification script %s does not allow bulking.") % info["title"])
        else:
            raise MKUserError(varprefix + "_p_notify_plugin",
                  _("Legacy ASCII Emails do not support bulking. You can either disable notification "
                    "bulking or choose another notification plugin which allows bulking."))


def render_notification_rules(rules, userid="", show_title=False, show_buttons=True,
                              analyse=False, start_nr=0, profilemode=False):
    if not rules:
        html.message(_("You have not created any rules yet."))

    if rules:
        if not show_title:
            title = ""
        elif profilemode:
            title = _("Notification rules")
        elif userid:
            url = html.makeuri([("mode", "user_notifications"), ("user", userid)])
            html.plug()
            html.icon_button(url, _("Edit this user's notifications"), "edit")
            code = html.drain()
            html.unplug()
            title = code + _("Notification rules of user %s") % userid
        else:
            title = _("Global notification rules")
        table.begin(title = title, limit = None)

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

            if show_buttons:
                anavar = html.var("analyse", "")
                delete_url = make_action_link([("mode", listmode), ("user", userid), ("_delete", nr)])
                drag_url   = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr)])
                suffix = profilemode and "_p" or ""
                edit_url   = folder_preserving_link([("mode", "notification_rule" + suffix), ("edit", nr), ("user", userid)])
                clone_url  = folder_preserving_link([("mode", "notification_rule" + suffix), ("clone", nr), ("user", userid)])

                table.cell(_("Actions"), css="buttons")
                html.icon_button(edit_url, _("Edit this notification rule"), "edit")
                html.icon_button(clone_url, _("Create a copy of this notification rule"), "clone")
                html.element_dragger("tr", base_url=drag_url)
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
            if "bulk" in rule:
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

            table.cell(_("Conditions"))
            num_conditions = len([key for key in rule if key.startswith("match_")])
            if num_conditions:
                html.write_text(_("%d conditions") % num_conditions)
            else:
                html.i(_("(no conditions)"))

        table.end()


def add_notify_change(action_name, text):
    add_change(action_name, text, need_restart=False)


def generic_rule_list_actions(rules, what, what_title, save_rules):
    if html.has_var("_delete"):
        nr = int(html.var("_delete"))
        rule = rules[nr]
        c = wato_confirm(_("Confirm deletion of %s") % what_title,
                         _("Do you really want to delete the %s <b>%d</b> <i>%s</i>?") %
                           (what_title, nr, rule.get("description","")))
        if c:
            add_notify_change(what + "-delete-rule", _("Deleted %s %d") % (what_title, nr))
            del rules[nr]
            save_rules(rules)
        elif c == False:
            return ""
        else:
            return

    elif html.has_var("_move"):
        if html.check_transaction():
            from_pos = html.get_integer_input("_move")
            to_pos = html.get_integer_input("_index")
            rule = rules[from_pos]
            del rules[from_pos] # make to_pos now match!
            rules[to_pos:to_pos] = [rule]
            save_rules(rules)
            add_notify_change(what + "-move-rule",
                _("Changed position of %s %d") % (what_title, from_pos))


def convert_context_to_unicode(context):
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


def mode_notifications(phase):
    options         = config.user.load_file("notification_display_options", {})
    show_user_rules = options.get("show_user_rules", False)
    show_backlog    = options.get("show_backlog", False)
    show_bulks      = options.get("show_bulks", False)

    if phase == "title":
        return _("Notification configuration")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Rule"), folder_preserving_link([("mode", "notification_rule")]), "new")
        if show_user_rules:
            html.context_button(_("Hide user rules"), html.makeactionuri([("_show_user", "")]), "users")
        else:
            html.context_button(_("Show user rules"), html.makeactionuri([("_show_user", "1")]), "users")

        if show_backlog:
            html.context_button(_("Hide Analysis"), html.makeactionuri([("_show_backlog", "")]), "analyze")
        else:
            html.context_button(_("Analyse"), html.makeactionuri([("_show_backlog", "1")]), "analyze")

        if show_bulks:
            html.context_button(_("Hide Bulks"), html.makeactionuri([("_show_bulks", "")]), "bulk")
        else:
            html.context_button(_("Show Bulks"), html.makeactionuri([("_show_bulks", "1")]), "bulk")

        return

    rules = []
    for rule in load_notification_rules():
        if config.user.may("notification_plugin.%s" % rule['notify_plugin'][0]) and \
           rule not in rules:
            rules.append(rule)

    if phase == "action":
        if html.has_var("_show_user"):
            if html.check_transaction():
                options["show_user_rules"] = not not html.var("_show_user")
                config.user.save_file("notification_display_options", options)

        elif html.has_var("_show_backlog"):
            if html.check_transaction():
                options["show_backlog"] = not not html.var("_show_backlog")
                config.user.save_file("notification_display_options", options)

        elif html.has_var("_show_bulks"):
            if html.check_transaction():
                options["show_bulks"] = not not html.var("_show_bulks")
                config.user.save_file("notification_display_options", options)

        elif html.has_var("_replay"):
            if html.check_transaction():
                nr = int(html.var("_replay"))
                result = check_mk_local_automation("notification-replay", [str(nr)], None)
                return None, _("Replayed notifiation number %d") % (nr + 1)

        else:
            return generic_rule_list_actions(rules, "notification", _("notification rule"),  save_notification_rules)

        return


    # Check setting of global notifications. Are they enabled? If not, display
    # a warning here. Note: this is a main.mk setting, so we cannot access this
    # directly.
    current_settings = load_configuration_settings()
    if not current_settings.get("enable_rulebased_notifications"):
        url = 'wato.py?mode=edit_configvar&varname=enable_rulebased_notifications'
        html.show_warning(
           _("<b>Warning</b><br><br>Rule based notifications are disabled in your global settings. "
             "The rules that you edit here will have affect only on notifications that are "
             "created by the Event Console. Normal monitoring alerts will <b>not</b> use the "
             "rule based notifications now."
             "<br><br>"
             "You can change this setting <a href=\"%s\">here</a>.") % url)

    elif not fallback_mail_contacts_configured():
        url = 'wato.py?mode=edit_configvar&varname=notification_fallback_email'
        html.show_warning(
          _("<b>Warning</b><br><br>You haven't configured a "
            "<a href=\"%s\">fallback email address</a> nor enabled receiving fallback emails for "
            "any user. If your monitoring produces a notification that is not matched by any of your "
            "notification rules, the notification will not be sent out. To prevent that, please "
            "configure either the global setting or enable the fallback contact option for at least "
            "one of your users.") % url)

    if show_bulks:
        if not render_bulks(only_ripe = False): # Warn if there are unsent bulk notificatios
            html.message(_("Currently there are no unsent notification bulks pending."))
    else:
        render_bulks(only_ripe = True) # Warn if there are unsent bulk notificatios

    # Show recent notifications. We can use them for rule analysis
    if show_backlog:
        backlog = store.load_data_from_file(cmk.paths.var_dir + "/notify/backlog.mk", [])
        if backlog:
            table.begin(table_id = "backlog", title = _("Recent notifications (for analysis)"), sortable=False)
            for nr, context in enumerate(backlog):
                convert_context_to_unicode(context)
                table.row()
                table.cell("&nbsp;", css="buttons")

                analyse_url = html.makeuri([("analyse", str(nr))])
                tooltip = "".join(("%s: %s\n" % e) for e in sorted(context.items()))
                html.icon_button(analyse_url, _("Analyze ruleset with this notification:\n%s") % tooltip, "analyze")
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
                table.cell(_("Plugin output"), output)
            table.end()

    # Do analysis
    if html.var("analyse"):
        nr = int(html.var("analyse"))
        analyse = check_mk_local_automation("notification-analyse", [str(nr)], None)
    else:
        analyse = False

    start_nr = 0
    render_notification_rules(rules, show_title = True, analyse=analyse, start_nr = start_nr)
    start_nr += len(rules)

    if options.get("show_user_rules"):
        users = userdb.load_users()
        userids = users.keys()
        userids.sort() # Create same order as modules/notification.py
        for userid in userids:
            user = users[userid]
            rules = user.get("notification_rules", [])
            if rules:
                render_notification_rules(rules, userid, show_title = True, show_buttons = False, analyse=analyse, start_nr = start_nr)
                start_nr += len(rules)

    if analyse:
        table.begin(table_id = "plugins", title = _("Resulting notifications"))
        for contact, plugin, parameters, bulk in analyse[1]:
            table.row()
            if contact.startswith('mailto:'):
                contact = contact[7:] # strip of fake-contact mailto:-prefix
            table.cell(_("Recipient"), contact)
            table.cell(_("Plugin"), vs_notification_scripts().value_to_text(plugin))
            table.cell(_("Plugin parameters"), ", ".join(parameters))
            table.cell(_("Bulking"))
            if bulk:
                html.write(_("Time horizon") + ": " + Age().value_to_text(bulk["interval"]))
                html.write_text(", %s: %d" % (_("Maximum count"), bulk["count"]))
                html.write(", %s %s" % (_("group by"), vs_notification_bulkby().value_to_text(bulk["groupby"])))

        table.end()


def render_bulks(only_ripe):
    bulks = check_mk_local_automation("notification-get-bulks", [ only_ripe and "1" or "0" ], None)
    if bulks:
        if only_ripe:
            table.begin(title = _("Overdue bulk notifications!"))
        else:
            table.begin(title = _("Open bulk notifications"))

        for dir, age, interval, maxcount, uuids in bulks:
            dirparts = dir.split("/")
            contact = dirparts[-3]
            method = dirparts[-2]
            bulk_id = dirparts[-1].split(",", 2)[-1]
            table.row()
            table.cell(_("Contact"), contact)
            table.cell(_("Method"), method)
            table.cell(_("Bulk ID"), bulk_id)
            table.cell(_("Max. Age"), "%d %s" % (interval, _("sec")), css="number")
            table.cell(_("Age"), "%d %s" % (age, _("sec")), css="number")
            if age >= interval:
                html.icon(_("Age of oldest notification is over maximum age"), "warning")
            table.cell(_("Max. Count"), str(maxcount), css="number")
            table.cell(_("Count"), str(len(uuids)), css="number")
            if len(uuids) >= maxcount:
                html.icon(_("Number of notifications exceeds maximum allowed number"), "warning")
        table.end()
        return True
    else:
        return False


def fallback_mail_contacts_configured():
    current_settings = load_configuration_settings()
    if current_settings.get("notification_fallback_email"):
        return True

    for user_id, user in userdb.load_users(lock=False).items():
        if user.get("fallback_contact", False):
            return True

    return False


# Similar like mode_notifications, but just for the user specific notification table
def mode_user_notifications(phase, profilemode):
    global notification_rule_start_async_repl

    if profilemode:
        userid = config.user.id
        title = _("Your personal notification rules")
        config.user.need_permission("general.edit_notifications")
    else:
        userid = html.get_unicode_input("user")
        title = _("Custom notification table for user ") + userid

    if phase == "title":
        return title

    users = userdb.load_users(lock = phase == 'action' or html.has_var("_move"))
    user = users[userid]
    rules = user.setdefault("notification_rules", [])

    if phase == "buttons":
        if profilemode:
            html.context_button(_("Profile"), "user_profile.py", "back")
            html.context_button(_("New Rule"), folder_preserving_link([("mode", "notification_rule_p")]), "new")
        else:
            html.context_button(_("All Users"), folder_preserving_link([("mode", "users")]), "back")
            html.context_button(_("User Properties"), folder_preserving_link([("mode", "edit_user"), ("edit", userid)]), "edit")
            html.context_button(_("New Rule"), folder_preserving_link([("mode", "notification_rule"), ("user", userid)]), "new")
        return

    elif phase == "action":
        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = rules[nr]
            c = wato_confirm(_("Confirm notification rule deletion"),
                             _("Do you really want to delete the notification rule <b>%d</b> <i>%s</i>?") %
                               (nr, rule.get("description","")))
            if c:
                del rules[nr]
                userdb.save_users(users)

                log_what = "notification-delete-user-rule"
                log_text = _("Deleted notification rule %d of user %s") % (nr, userid)

                notification_rule_start_async_repl = False
                if profilemode and has_wato_slave_sites():
                    notification_rule_start_async_repl = True
                    log_audit(None, log_what, log_text)
                else:
                    add_notify_change(log_what, log_text)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = html.get_integer_input("_move")
                to_pos = html.get_integer_input("_index")
                rule = rules[from_pos]
                del rules[from_pos] # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                userdb.save_users(users)

                log_what = "notification-move-user-rule"
                log_text = _("Changed position of notification rule %d of user %s") % (from_pos, userid)

                notification_rule_start_async_repl = False
                if profilemode and has_wato_slave_sites():
                    notification_rule_start_async_repl = True
                    log_audit(None, log_what, log_text)
                else:
                    add_notify_change(log_what, log_text)
        return

    if notification_rule_start_async_repl:
        user_profile_async_replication_dialog()
        notification_rule_start_async_repl = False
        html.h3(_('Notification Rules'))

    rules = user.get("notification_rules", [])
    render_notification_rules(rules, userid, profilemode = profilemode)

notification_rule_start_async_repl = False

def mode_notification_rule(phase, profilemode):
    global notification_rule_start_async_repl

    edit_nr = int(html.var("edit", "-1"))
    clone_nr = int(html.var("clone", "-1"))
    if profilemode:
        userid = config.user.id
        config.user.need_permission("general.edit_notifications")
    else:
        userid = html.get_unicode_input("user", "")

    if userid and not profilemode:
        suffix = _(" for user ") + html.attrencode(userid)
    else:
        suffix = ""

    new = edit_nr < 0

    if phase == "title":
        if new:
            return _("Create new notification rule") + suffix
        else:
            return _("Edit notification rule %d") % edit_nr + suffix

    elif phase == "buttons":
        if profilemode:
            html.context_button(_("All Rules"), folder_preserving_link([("mode", "user_notifications_p")]), "back")
        else:
            html.context_button(_("All Rules"), folder_preserving_link([("mode", "notifications"), ("userid", userid)]), "back")
        return

    if userid:
        users = userdb.load_users(lock = phase == 'action')
        if userid not in users:
            raise MKUserError(None, _("The user you are trying to edit "
                                      "notification rules for does not exist."))
        user = users[userid]
        rules = user.setdefault("notification_rules", [])
    else:
        rules = load_notification_rules()

    if new:
        if clone_nr >= 0 and not html.var("_clear"):
            rule = {}
            rule.update(rules[clone_nr])
        else:
            rule = {}
    else:
        rule = rules[edit_nr]

    vs = vs_notification_rule(userid)

    if phase == "action":
        if not html.check_transaction():
            return "notifications"

        rule = vs.from_html_vars("rule")
        if userid:
            rule["contact_users"] = [ userid ] # Force selection of our user

        vs.validate_value(rule, "rule")

        if new and clone_nr >= 0:
            rules[clone_nr:clone_nr] = [ rule ]
        elif new:
            rules[0:0] = [ rule ]
        else:
            rules[edit_nr] = rule

        if userid:
            userdb.save_users(users)
        else:
            save_notification_rules(rules)

        if new:
            log_what = "new-notification-rule"
            log_text = _("Created new notification rule") + suffix
        else:
            log_what = "edit-notification-rule"
            log_text = _("Changed notification rule %d") % edit_nr + suffix

        notification_rule_start_async_repl = False
        if profilemode and has_wato_slave_sites():
            notification_rule_start_async_repl = True
            log_audit(None, log_what, log_text)
            return # don't redirect to other page
        else:
            add_notify_change(log_what, log_text)

        if profilemode:
            return "user_notifications_p"
        elif userid:
            return "user_notifications"
        else:
            return "notifications"

    if notification_rule_start_async_repl:
        user_profile_async_replication_dialog()
        notification_rule_start_async_repl = False
        return

    html.begin_form("rule", method = "POST")
    vs.render_input("rule", rule)
    vs.set_focus("rule")
    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()


def load_notification_scripts():
    return load_user_scripts("notifications")


#.
#   .--Timeperiods---------------------------------------------------------.
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Modes for managing Nagios' timeperiod definitions.                   |
#   '----------------------------------------------------------------------'

def mode_timeperiods(phase):
    if phase == "title":
        return _("Time Periods")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Timeperiod"), folder_preserving_link([("mode", "edit_timeperiod")]), "new")
        html.context_button(_("Import iCalendar"), folder_preserving_link([("mode", "import_ical")]), "ical")
        return

    timeperiods = load_timeperiods()

    if phase == "action":
        delname = html.var("_delete")
        if delname and html.transaction_valid():
            usages = find_usages_of_timeperiod(delname)
            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this timeperiod."),
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            c = wato_confirm(_("Confirm deletion of time period %s") % delname,
                  _("Do you really want to delete the time period '%s'? I've checked it: "
                    "it is not being used by any rule or user profile right now.") % delname)
            if c:
                del timeperiods[delname]
                save_timeperiods(timeperiods)
                add_change("edit-timeperiods", _("Deleted timeperiod %s") % delname)
            elif c == False:
                return ""
        return None


    table.begin("timeperiods", empty_text = _("There are no timeperiods defined yet."))
    names = timeperiods.keys()
    names.sort()
    for name in names:
        table.row()

        timeperiod = timeperiods[name]
        edit_url     = folder_preserving_link([("mode", "edit_timeperiod"), ("edit", name)])
        delete_url   = make_action_link([("mode", "timeperiods"), ("_delete", name)])

        table.cell(_("Actions"), css="buttons")
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), timeperiod.get("alias", ""))
    table.end()




class ExceptionName(TextAscii):
    def __init__(self, **kwargs):
        kwargs["regex"] = "^[-a-z0-9A-Z /]*$"
        kwargs["regex_error"] = _("This is not a valid Nagios timeperiod day specification.")
        kwargs["allow_empty"] = False
        super(ExceptionName, self).__init__(**kwargs)

    def validate_value(self, value, varprefix):
        if value in [ "monday", "tuesday", "wednesday", "thursday",
                       "friday", "saturday", "sunday" ]:
            raise MKUserError(varprefix, _("You cannot use weekday names (%s) in exceptions") % value)
        if value in [ "name", "alias", "timeperiod_name", "register", "use", "exclude" ]:
            raise MKUserError(varprefix, _("<tt>%s</tt> is a reserved keyword."))
        TextAscii.validate_value(self, value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)

class MultipleTimeRanges(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._num_columns = kwargs.get("num_columns", 3)
        self._rangevs = TimeofdayRange()

    def canonical_value(self):
        return [ ((0,0), (24,0)), None, None ]

    def render_input(self, varprefix, value):
        for c in range(0, self._num_columns):
            if c:
                html.write(" &nbsp; ")
            if c < len(value):
                v = value[c]
            else:
                v = self._rangevs.canonical_value()
            self._rangevs.render_input(varprefix + "_%d" % c, v)

    def value_to_text(self, value):
        parts = []
        for v in value:
            parts.append(self._rangevs.value_to_text(v))
        return ", ".join(parts)

    def from_html_vars(self, varprefix):
        value = []
        for c in range(0, self._num_columns):
            v = self._rangevs.from_html_vars(varprefix + "_%d" % c)
            if v != None:
                value.append(v)
        return value

    def validate_value(self, value, varprefix):
        for c, v in enumerate(value):
            self._rangevs.validate_value(v, varprefix + "_%d" % c)
        ValueSpec.custom_validate(self, value, varprefix)

# Check, if timeperiod tpa excludes or is tpb
def timeperiod_excludes(timeperiods, tpa_name, tpb_name):
    if tpa_name == tpb_name:
        return True

    tpa = timeperiods[tpa_name]
    for ex in tpa.get("exclude", []):
        if ex == tpb_name:
            return True
        if timeperiod_excludes(timeperiods, ex, tpb_name):
            return True
    return False

def validate_ical_file(value, varprefix):
    filename, ty, content = value
    if not filename.endswith('.ics'):
        raise MKUserError(varprefix, _('The given file does not seem to be a valid iCalendar file. '
                                       'It needs to have the file extension <tt>.ics</tt>.'))

    if not content.startswith('BEGIN:VCALENDAR'):
        raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))

    if not content.startswith('END:VCALENDAR'):
        raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))

# Returns a dictionary in the format:
# {
#   'name'   : '...',
#   'descr'  : '...',
#   'events' : [
#       {
#           'name': '...',
#           'date': '...',
#       },
#   ],
# }
#
# Relevant format specifications:
#   http://tools.ietf.org/html/rfc2445
#   http://tools.ietf.org/html/rfc5545
# TODO: Let's use some sort of standard module in the future. Maybe we can then also handle
# times instead of only full day events.
def parse_ical(ical_blob, horizon=10, times=(None, None, None)):
    ical = {'raw_events': []}

    def get_params(key):
        if ';' in key:
            return dict([ p.split('=', 1) for p in key.split(';')[1:] ])
        return {}

    def parse_date(params, val):
        # First noprmalize the date value to make it easier parsable later
        if 'T' not in val and params.get('VALUE') == 'DATE':
            val += 'T000000' # add 00:00:00 to date specification

        return list(time.strptime(val, '%Y%m%dT%H%M%S'))

    # First extract the relevant information from the file
    in_event = False
    event    = {}
    for l in ical_blob.split('\n'):
        line = l.strip()
        if not line:
            continue
        try:
            key, val = line.split(':', 1)
        except ValueError:
            raise Exception('Failed to parse line: "%s"' % line)

        if key == 'X-WR-CALNAME':
            ical['name'] = val
        elif key == 'X-WR-CALDESC':
            ical['descr'] = val

        elif line == 'BEGIN:VEVENT':
            in_event = True
            event = {} # create new event

        elif line == 'END:VEVENT':
            # Finish the current event
            ical['raw_events'].append(event)
            in_event = False

        elif in_event:
            if key.startswith('DTSTART'):
                params = get_params(key)
                event['start'] = parse_date(params, val)

            elif key.startswith('DTEND'):
                params = get_params(key)
                event['end'] = parse_date(params, val)

            elif key == 'RRULE':
                event['recurrence'] = dict([ p.split('=', 1) for p in val.split(';') ])

            elif key == 'SUMMARY':
                event['name'] = val

    def next_occurrence(start, now, freq):
        # convert struct_time to list to be able to modify it,
        # then set it to the next occurence
        t = start[:]

        if freq == 'YEARLY':
            t[0] = now[0]+1 # add 1 year
        elif freq == 'MONTHLY':
            if now[1] + 1 > 12:
                t[0] = now[0]+1
                t[1] = now[1] + 1 - 12
            else:
                t[0] = now[0]
                t[1] = now[1] + 1
        else:
            raise Exception('The frequency "%s" is currently not supported' % freq)
        return t


    def resolve_multiple_days(event, cur_start_time):
        if time.strftime('%Y-%m-%d', cur_start_time) \
            == time.strftime('%Y-%m-%d', event["end"]):
            # Simple case: a single day event
            return [{
                'name'  : event['name'],
                'date'  : time.strftime('%Y-%m-%d', cur_start_time),
            }]

        # Resolve multiple days
        resolved, cur_timestamp, day = [], time.mktime(cur_start_time), 1
        # day < 100 is just some plausibilty check. In case such an event
        # is needed eventually remove this
        while cur_timestamp < time.mktime(event["end"]) and day < 100:
            resolved.append({
                "name" : "%s %s" % (event["name"], _(" (day %d)") % day),
                "date" : time.strftime("%Y-%m-%d", time.localtime(cur_timestamp)),
            })
            cur_timestamp += 86400
            day += 1

        return resolved

    # Now resolve recurring events starting from 01.01 of current year
    # Non-recurring events are simply copied
    resolved = []
    now  = list(time.strptime(str(time.localtime().tm_year-1), "%Y"))
    last = now[:]
    last[0] += horizon+1 # update year to horizon
    for event in ical['raw_events']:
        if 'recurrence' in event and event['start'] < now:
            rule     = event['recurrence']
            freq     = rule['FREQ']
            interval = int(rule.get('INTERVAL', 1))
            cur      = now
            while cur < last:
                cur = next_occurrence(event['start'], cur, freq)
                resolved += resolve_multiple_days(event, cur)
        else:
            resolved += resolve_multiple_days(event, event["start"])

    ical['events'] = sorted(resolved)

    return ical

# Displays a dialog for uploading an ical file which will then
# be used to generate timeperiod exceptions etc. and then finally
# open the edit_timeperiod page to create a new timeperiod using
# these information
def mode_timeperiod_import_ical(phase):
    if phase == "title":
        return _("Import iCalendar File to create a Timeperiod")

    elif phase == "buttons":
        html.context_button(_("All Timeperiods"), folder_preserving_link([("mode", "timeperiods")]), "back")
        return

    vs_ical = Dictionary(
        title = _('Import iCalendar File'),
        render = "form",
        optional_keys = None,
        elements = [
            ('file', FileUpload(
                title = _('iCalendar File'),
                help = _("Select an iCalendar file (<tt>*.ics</tt>) from your PC"),
                allow_empty = False,
                custom_validate = validate_ical_file,
            )),
            ('horizon', Integer(
                title = _('Time horizon for repeated events'),
                help = _("When the iCalendar file contains definitions of repeating events, these repeating "
                         "events will be resolved to single events for the number of years you specify here."),
                minvalue = 0,
                maxvalue = 50,
                default_value = 10,
                unit = _('years'),
                allow_empty = False,
            )),
            ('times', Optional(
                MultipleTimeRanges(
                    default_value = [None, None, None],
                ),
                title = _('Use specific times'),
                label = _('Use specific times instead of whole day'),
                help = _("When you specify explicit time definitions here, these will be added to each "
                         "date which is added to the resulting time period. By default the whole day is "
                         "used."),
            )),
        ]
    )

    ical = {}

    if phase == "action":
        if html.check_transaction():
            ical = vs_ical.from_html_vars("ical")
            vs_ical.validate_value(ical, "ical")

            filename, ty, content = ical['file']

            try:
                data = parse_ical(content, ical['horizon'], ical['times'])
            except Exception, e:
                if config.debug:
                    raise
                raise MKUserError('ical_file', _('Failed to parse file: %s') % e)

            html.set_var('alias', data.get('descr', data.get('name', filename)))

            for day in [ "monday", "tuesday", "wednesday", "thursday",
                         "friday", "saturday", "sunday" ]:
                html.set_var('%s_0_from' % day, '')
                html.set_var('%s_0_until' % day, '')

            html.set_var('except_count', "%d" % len(data['events']))
            for index, event in enumerate(data['events']):
                index += 1
                html.set_var('except_%d_0' % index, event['date'])
                html.set_var('except_indexof_%d' % index, "%d" % index)
                for n, time_spec in enumerate(ical["times"]):
                    start_time = ":".join(map(str, time_spec[0]))
                    end_time   = ":".join(map(str, time_spec[1]))
                    html.set_var('except_%d_1_%d_from' % (index, n), start_time)
                    html.set_var('except_%d_1_%d_until' % (index, n), end_time)
            return "edit_timeperiod"
        return

    html.p(_('This page can be used to generate a new timeperiod definition based '
             'on the appointments of an iCalendar (<tt>*.ics</tt>) file. This import is normally used '
             'to import events like holidays, therefore only single whole day appointments are '
             'handled by this import.'))

    html.begin_form("import_ical", method="POST")
    vs_ical.render_input("ical", ical)
    forms.end()
    html.button("upload", _("Import"))
    html.hidden_fields()
    html.end_form()

def mode_edit_timeperiod(phase):
    num_columns = 3
    timeperiods = load_timeperiods()
    name = html.var("edit") # missing -> new group
    new = name == None

    # ValueSpec for the list of Exceptions
    vs_ex = ListOf(
        Tuple(
            orientation = "horizontal",
            show_titles = False,
            elements = [
                ExceptionName(),
                MultipleTimeRanges()]
        ),
        movable = False,
        add_label = _("Add Exception"))

    # ValueSpec for excluded Timeperiods. We offer the list of
    # all other timeperiods - but only those that do not
    # exclude the current timeperiod (in order to avoid cycles)
    other_tps = []
    for tpname, tp in timeperiods.items():
        if not timeperiod_excludes(timeperiods, tpname, name):
            other_tps.append((tpname, tp.get("alias") or name))

    vs_excl = ListChoice(choices=other_tps)

    # convert Check_MK representation of range to ValueSpec-representation
    def convert_from_tod(tod):
        # "00:30" -> (0, 30)
        return tuple(map(int, tod.split(":")))

    def convert_from_range(range):
        # ("00:30", "10:17") -> ((0,30),(10,17))
        return tuple(map(convert_from_tod, range))

    def convert_to_tod(value):
        return "%02d:%02d" % value

    def convert_to_range(value):
        return tuple(map(convert_to_tod, value))

    def timeperiod_ranges(vp, keyname, new):
        ranges = timeperiod.get(keyname, [])
        value = []
        for range in ranges:
            value.append(convert_from_range(range))
        if len(value) == 0 and new:
            value.append(((0,0),(24,0)))

        html.open_td()
        MultipleTimeRanges().render_input(vp, value)
        html.close_td()

    def get_ranges(varprefix):
        value = MultipleTimeRanges().from_html_vars(varprefix)
        MultipleTimeRanges().validate_value(value, varprefix)
        return map(convert_to_range, value)

    if phase == "title":
        if new:
            return _("Create new time period")
        else:
            return _("Edit time period")

    elif phase == "buttons":
        html.context_button(_("All Timeperiods"), folder_preserving_link([("mode", "timeperiods")]), "back")
        return

    if new:
        timeperiod = {}
    else:
        timeperiod = timeperiods.get(name, {})

    weekdays_by_name = [
      ( "monday",    _("Monday") ),
      ( "tuesday",   _("Tuesday") ),
      ( "wednesday", _("Wednesday") ),
      ( "thursday",  _("Thursday") ),
      ( "friday",    _("Friday") ),
      ( "saturday",  _("Saturday") ),
      ( "sunday",    _("Sunday") ),
    ]

    if phase == "action":
        if html.check_transaction():
            alias = html.get_unicode_input("alias").strip()
            if not alias:
                raise MKUserError("alias", _("Please specify an alias name for your timeperiod."))

            unique, info = is_alias_used("timeperiods", name, alias)
            if not unique:
                raise MKUserError("alias", info)

            timeperiod.clear()

            # extract time ranges of weekdays
            for weekday, weekday_name in weekdays_by_name:
                ranges = get_ranges(weekday)
                if ranges:
                    timeperiod[weekday] = ranges
                elif weekday in timeperiod:
                    del timeperiod[weekday]

            # extract ranges for custom days
            exceptions = vs_ex.from_html_vars("except")
            vs_ex.validate_value(exceptions, "except")
            for exname, ranges in exceptions:
                timeperiod[exname] = map(convert_to_range, ranges)

            # extract excludes
            excludes = vs_excl.from_html_vars("exclude")
            vs_excl.validate_value(excludes, "exclude")
            if excludes:
                timeperiod["exclude"] = excludes

            if new:
                name = html.var("name")
                if len(name) == 0:
                    raise MKUserError("name", _("Please specify a name of the new timeperiod."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid timeperiod name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if name in timeperiods:
                    raise MKUserError("name", _("This name is already being used by another timeperiod."))
                if name == "24X7":
                    raise MKUserError("name", _("The time period name 24X7 cannot be used. It is always autmatically defined."))
                timeperiods[name] = timeperiod
                add_change("edit-timeperiods", _("Created new time period %s") % name)
            else:
                add_change("edit-timeperiods", _("Modified time period %s") % name)
            timeperiod["alias"] = alias
            save_timeperiods(timeperiods)
            return "timeperiods"
        return

    html.begin_form("timeperiod", method="POST")
    forms.header(_("Timeperiod"))

    # Name
    forms.section(_("Internal name"), simple = not new)
    if new:
        html.text_input("name")
        html.set_focus("name")
    else:
        html.write_text(name)

    # Alias
    if not new:
        alias = timeperiods[name].get("alias", "")
    else:
        alias = ""

    forms.section(_("Alias"))
    html.help(_("An alias or description of the timeperiod"))
    html.text_input("alias", alias, size = 81)
    if not new:
        html.set_focus("alias")

    # Week days
    forms.section(_("Weekdays"))
    html.help("For each weekday you can setup no, one or several "
               "time ranges in the format <tt>23:39</tt>, in which the time period "
               "should be active.")
    html.open_table(class_="timeperiod")

    for weekday, weekday_alias in weekdays_by_name:
        ranges = timeperiod.get(weekday)
        html.open_tr()
        html.td(weekday_alias, class_="name")
        timeperiod_ranges(weekday, weekday, new)
        html.close_tr()
    html.close_table()

    # Exceptions
    forms.section(_("Exceptions (from weekdays)"))
    html.help(_("Here you can specify exceptional time ranges for certain "
                "dates in the form YYYY-MM-DD which are used to define more "
                "specific definitions to override the times configured for the matching "
                "weekday."))

    exceptions = []
    for k in timeperiod:
        if k not in [ w[0] for w in weekdays_by_name ] and k not in [ "alias", "exclude" ]:
            exceptions.append((k, map(convert_from_range, timeperiod[k])))
    exceptions.sort()
    vs_ex.render_input("except", exceptions)

    # Excludes
    if other_tps:
        forms.section(_("Exclude"))
        html.help(_('You can use other timeperiod definitions to exclude the times '
                    'defined in the other timeperiods from this current timeperiod.'))
        vs_excl.render_input("exclude", timeperiod.get("exclude", []))


    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()


class TimeperiodSelection(ElementSelection):
    def __init__(self, **kwargs):
        ElementSelection.__init__(self, **kwargs)

    def get_elements(self):
        timeperiods = load_timeperiods()
        elements = dict([ ("24X7", _("Always")) ] + \
           [ (name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items() ])
        return elements

    def default_value(self):
        return "24x7"

# Check if a timeperiod is currently in use and cannot be deleted
# Returns a list of occurrances.
# Possible usages:
# - 1. rules: service/host-notification/check-period
# - 2. user accounts (notification period)
# - 3. excluded by other timeperiods
def find_usages_of_timeperiod(tpname):

    # Part 1: Rules
    used_in = []

    rulesets = AllRulesets()
    rulesets.load()

    for varname, ruleset in rulesets.get_rulesets().items():
        if not isinstance(ruleset.valuespec(), TimeperiodSelection):
            continue

        for folder, rulenr, rule in ruleset.get_rules():
            if rule.value == tpname:
                used_in.append(("%s: %s" % (_("Ruleset"), ruleset.title()),
                               folder_preserving_link([("mode", "edit_ruleset"), ("varname", varname)])))
                break

    # Part 2: Users
    for userid, user in userdb.load_users().items():
        tp = user.get("notification_period")
        if tp == tpname:
            used_in.append(("%s: %s" % (_("User"), userid),
                folder_preserving_link([("mode", "edit_user"), ("edit", userid)])))

    # Part 3: Other Timeperiods
    for tpn, tp in load_timeperiods().items():
        if tpname in tp.get("exclude", []):
            used_in.append(("%s: %s (%s)" % (_("Timeperiod"), tp.get("alias", tpn),
                    _("excluded")),
                    folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tpn)])))

    return used_in


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



class ModeSites(WatoMode):
    def __init__(self):
        super(ModeSites, self).__init__()


    def buttons(self):
        global_buttons()



class ModeDistributedMonitoring(ModeSites):
    def __init__(self):
        super(ModeDistributedMonitoring, self).__init__()


    def title(self):
        return _("Distributed Monitoring")


    def buttons(self):
        super(ModeDistributedMonitoring, self).buttons()
        html.context_button(_("New connection"),
                            folder_preserving_link([("mode", "edit_site")]),
                            "new")


    def action(self):
        delete_id = html.var("_delete")
        if delete_id and html.transaction_valid():
            self._action_delete(delete_id)

        logout_id = html.var("_logout")
        if logout_id:
            return self._action_logout(logout_id)

        login_id = html.var("_login")
        if login_id:
            return self._action_login(login_id)


    def _action_delete(self, delete_id):
        configured_sites = load_sites()
        # The last connection can always be deleted. In that case we
        # fall back to non-distributed-WATO and the site attribute
        # will be removed.
        test_sites = dict(configured_sites.items())
        del test_sites[delete_id]

        # Make sure that site is not being used by hosts and folders
        if delete_id in Folder.root_folder().all_site_ids():
            search_url = html.makeactionuri([
                ("host_search_change_site", "on"),
                ("host_search_site", delete_id),
                ("host_search",      "1"),
                ("folder",           ""),
                ("mode",             "search"),
                ("filled_in",        "edit_host"),
            ])
            raise MKUserError(None,
                _("You cannot delete this connection. It has folders/hosts "
                  "assigned to it. You can use the <a href=\"%s\">host "
                  "search</a> to get a list of the hosts.") % search_url)


        c = wato_confirm(_("Confirm deletion of site %s") % html.render_tt(delete_id),
                         _("Do you really want to delete the connection to the site %s?") % \
                         html.render_tt(delete_id))
        if c:
            del configured_sites[delete_id]
            save_sites(configured_sites)
            clear_site_replication_status(delete_id)
            add_change("edit-sites", _("Deleted site %s") % html.render_tt(delete_id),
                       domains=[ConfigDomainGUI], sites=[default_site()])
            return None

        elif c == False:
            return ""

        else:
            return None


    def _action_logout(self, logout_id):
        configured_sites = load_sites()
        site = configured_sites[logout_id]
        c = wato_confirm(_("Confirm logout"),
                         _("Do you really want to log out of '%s'?") % \
                         html.render_tt(site["alias"]))
        if c:
            if "secret" in site:
                del site["secret"]
            save_sites(configured_sites)
            add_change("edit-site", _("Logged out of remote site %s") % html.render_tt(site["alias"]),
                       domains=[ConfigDomainGUI], sites=[default_site()])
            return None, _("Logged out.")

        elif c == False:
            return ""

        else:
            return None


    def _action_login(self, login_id):
        configured_sites = load_sites()
        if html.var("_abort"):
            return "sites"

        if not html.check_transaction():
            return

        site  = configured_sites[login_id]
        error = None
        # Fetch name/password of admin account
        if html.has_var("_name"):
            name   = html.var("_name", "").strip()
            passwd = html.var("_passwd", "").strip()
            try:
                secret = do_site_login(login_id, name, passwd)
                site["secret"] = secret
                save_sites(configured_sites)
                message = _("Successfully logged into remote site %s.") % html.render_tt(site["alias"])
                log_audit(None, "edit-site", message)
                return None, message

            except MKAutomationException, e:
                error = _("Cannot connect to remote site: %s") % e

            except MKUserError, e:
                html.add_user_error(e.varname, e)
                error = "%s" % e

            except Exception, e:
                if config.debug:
                    raise
                html.add_user_error("_name", error)
                error = str(e)

        wato_html_head(_("Login into site %s") % html.render_tt(site["alias"]))
        if error:
            html.show_error(error)

        html.p(_("For the initial login into the slave site %s "
                 "we need once your administration login for the Multsite "
                 "GUI on that site. Your credentials will only be used for "
                 "the initial handshake and not be stored. If the login is "
                 "successful then both side will exchange a login secret "
                 "which is used for the further remote calls.") % html.render_tt(site["alias"]))

        html.begin_form("login", method="POST")
        forms.header(_('Login credentials'))
        forms.section(_('Adminstrator name:'))
        html.text_input("_name")
        html.set_focus("_name")
        forms.section(_('Adminstrator password:'))
        html.password_input("_passwd")
        forms.end()
        html.button("_do_login", _("Login"))
        html.button("_abort", _("Abort"))
        html.hidden_field("_login", login_id)
        html.hidden_fields()
        html.end_form()
        html.footer()
        return False


    def page(self):
        table.begin("sites", _("Connections to local and remote sites"),
                    empty_text = _("You have not configured any local or remotes sites. Multisite will "
                                   "implicitely add the data of the local monitoring site. If you add remotes "
                                   "sites, please do not forget to add your local monitoring site also, if "
                                   "you want to display its data."))

        sites = sort_sites(load_sites().items())
        for site_id, site in sites:
            table.row()

            self._page_buttons(site_id, site)
            self._page_basic_settings(site_id, site)
            self._page_livestatus_settings(site_id, site)
            self._page_replication_configuration(site_id, site)

        table.end()


    def _page_buttons(self, site_id, site):
        table.cell(_("Actions"), css="buttons")
        edit_url = folder_preserving_link([("mode", "edit_site"), ("edit", site_id)])
        html.icon_button(edit_url, _("Properties"), "edit")

        clone_url = folder_preserving_link([("mode", "edit_site"), ("clone", site_id)])
        html.icon_button(clone_url, _("Clone this connection in order to create a new one"), "clone")

        delete_url = html.makeactionuri([("_delete", site_id)])
        html.icon_button(delete_url, _("Delete"), "delete")

        if has_wato_slave_sites() and (site.get("replication") or config.site_is_local(site_id)):
            globals_url = folder_preserving_link([("mode", "edit_site_globals"), ("site", site_id)])
            html.icon_button(globals_url, _("Site specific global configuration"), "configuration")


    def _page_basic_settings(self, site_id, site):
        table.cell(_("ID"), site_id)
        table.cell(_("Alias"), site.get("alias", ""))


    def _page_livestatus_settings(self, site_id, site):
        # Socket
        socket = site.get("socket", _("local site"))
        if socket == "disabled:":
            socket = _("don't query status")
        table.cell(_("Socket"))
        if type(socket) == tuple and socket[0] == "proxy":
            html.write_text(_("Use livestatus Proxy-Daemon"))
        else:
            html.write_text(socket)

        # Status host
        if site.get("status_host"):
            sh_site, sh_host = site["status_host"]
            table.cell(_("Status host"), "%s/%s" % (sh_site, sh_host))
        else:
            table.cell(_("Status host"))

        # Disabled
        if site.get("disabled", False) == True:
            table.cell(_("Disabled"), "<b>%s</b>" % _("yes"))
        else:
            table.cell(_("Disabled"), _("no"))

        # Timeout
        if "timeout" in site:
            table.cell(_("Timeout"), _("%d sec") % int(site["timeout"]), css="number")
        else:
            table.cell(_("Timeout"), "")

        # Persist
        if site.get("persist", False):
            table.cell(_("Pers."), "<b>%s</b>" % _("yes"))
        else:
            table.cell(_("Pers."), _("no"))


    def _page_replication_configuration(self, site_id, site):
        # Replication
        if site.get("replication"):
            repl = _("Slave")
            if site.get("replicate_ec"):
                repl += ", " + _("EC")
            if site.get("replicate_mkps"):
                repl += ", " + _("MKPs")
        else:
            repl = ""
        table.cell(_("Replication"), repl)

        # Login-Button for Replication
        table.cell(_("Login"))
        if repl:
            if site.get("secret"):
                logout_url = make_action_link([("mode", "sites"), ("_logout", site_id)])
                html.buttonlink(logout_url, _("Logout"))
            else:
                login_url = make_action_link([("mode", "sites"), ("_login", site_id)])
                html.buttonlink(login_url, _("Login"))



class ModeEditSiteGlobals(ModeSites):
    def __init__(self):
        super(ModeEditSiteGlobals, self).__init__()
        self._site_id = html.var("site")
        self._configured_sites = load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

        # The site's default values are the current global settings
        self._default_values = check_mk_local_automation("get-configuration", [], get_check_mk_config_var_names())
        self._default_values.update(load_configuration_settings())
        self._current_settings = self._site.get("globals", {})


    def title(self):
        return _("Edit site specific global settings of %s") % \
               html.render_tt(self._site_id)


    def buttons(self):
        super(ModeEditSiteGlobals, self).buttons()
        html.context_button(_("All Sites"),
                            folder_preserving_link([("mode", "sites")]),
                            "back")
        html.context_button(_("Connection"),
                            folder_preserving_link([("mode", "edit_site"),
                            ("edit", self._site_id)]), "sites")


    def action(self):
        varname = html.var("_varname")
        action  = html.var("_action")
        if not varname:
            return

        domain, valuespec, need_restart, allow_reset, in_global_settings = configvars()[varname]
        def_value = self._default_values.get(varname, valuespec.default_value())

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
                  (varname, self._current_settings[varname] and _("on") or _("off"))

            self._site.setdefault("globals", {})[varname] = self._current_settings[varname]
            save_sites(self._configured_sites, activate=False)

            add_change("edit-configvar", msg, sites=[self._site_id], need_restart=need_restart)

            if action == "_reset":
                return "edit_site_globals", msg
            else:
                return "edit_site_globals"

        elif c == False:
            return ""

        else:
            return None


    def page(self):
        search = get_search_expression()
        html.help(_("Here you can configure global settings, that should just be applied "
                    "on that site. <b>Note</b>: this only makes sense if the site "
                    "is part of a distributed setup."))

        if not has_wato_slave_sites():
           html.show_error(_("You can not configure site specific global settings "
                             "in non distributed setups."))
           return

        if not self._site.get("replication") and not config.site_is_local(self._site_id):
            html.show_error(_("This site is not the master site nor a replication slave. "
                              "You cannot configure specific settings for it."))
            return

        group_names = global_config_variable_groups(show_all=True)
        render_global_configuration_variables(group_names, self._default_values,
                                              self._current_settings, search=search)



class ModeEditSite(ModeSites):
    def __init__(self):
        super(ModeEditSite, self).__init__()
        self._from_html_vars()

        self._new        = self._site_id == None
        self._new_site   = {}
        configured_sites = load_sites()

        if self._clone_id:
            self._site = configured_sites[self._clone_id]

        elif self._new:
            self._site = { "replicate_mkps" : True }

        else:
            self._site = configured_sites.get(self._site_id, {})


    def _from_html_vars(self):
        self._site_id      = html.var("edit")
        self._clone_id     = html.var("clone")
        self._id           = html.var("id")
        self._url_prefix   = html.var("url_prefix", "").strip()
        self._timeout      = html.var("timeout", "").strip()
        self._sh_site      = html.var("sh_site")
        self._sh_host      = html.var("sh_host")
        self._repl         = html.var("replication")
        self._multisiteurl = html.var("multisiteurl", "").strip()


    def title(self):
        if self._new:
            return _("Create new site connection")
        else:
            return _("Edit site connection %s") % html.render_tt(self._site_id)


    def buttons(self):
        super(ModeEditSite, self).buttons()
        html.context_button(_("All Sites"), folder_preserving_link([("mode", "sites")]), "back")
        if not self._new and self._site.get("replication"):
            html.context_button(_("Site-Globals"),
                                folder_preserving_link([("mode", "edit_site_globals"),
                                ("site", self._site_id)]), "configuration")


    def action(self):
        if not html.check_transaction():
            return "sites"

        if self._new:
            self._id = self._id.strip()
        else:
            self._id = self._site_id

        configured_sites = load_sites()
        if self._new and self._id in configured_sites:
            raise MKUserError("id", _("This id is already being used by another connection."))

        if not re.match("^[-a-z0-9A-Z_]+$", self._id):
            raise MKUserError("id", _("The site id must consist only of letters, digit and the underscore."))

        detail_msg = self._set_site_attributes()
        configured_sites[self._id] = self._new_site
        save_sites(configured_sites)

        if self._new:
            msg = _("Created new connection to site %s") % html.render_tt(self._id)
        else:
            msg = _("Modified site connection %s") % html.render_tt(self._id)

        # Don't know exactly what have been changed, so better issue a change
        # affecting all domains
        add_change("edit-sites", msg, sites=[self._id], domains=ConfigDomain.enabled_domains())

        # In case a site is not being replicated anymore, confirm all changes for this site!
        if not self._repl:
            clear_site_replication_status(self._id)

        if self._id != config.omd_site():
            # On central site issue a change only affecting the GUI
            add_change("edit-sites", msg, sites=[config.omd_site()], domains=[ConfigDomainGUI])

        return "sites", detail_msg


    def _set_site_attributes(self):
        # Save copy of old site for later
        configured_sites = load_sites()
        if not self._new:
            old_site = configured_sites[self._site_id]

        self._new_site = {}
        alias = html.get_unicode_input("alias", "").strip()
        if not alias:
            raise MKUserError("alias", _("Please enter an alias name or description of this site."))

        self._new_site["alias"] = alias
        if self._url_prefix and self._url_prefix[-1] != '/':
            raise MKUserError("url_prefix", _("The URL prefix must end with a slash."))
        if self._url_prefix:
            self._new_site["url_prefix"] = self._url_prefix
        disabled = html.get_checkbox("disabled")
        self._new_site["disabled"] = disabled

        # Connection
        method = self._vs_conn_method().from_html_vars("method")
        self._vs_conn_method().validate_value(method, "method")
        if type(method) == tuple and method[0] in [ "unix", "tcp"]:
            if method[0] == "unix":
                self._new_site["socket"] = "unix:" + method[1]
            else:
                self._new_site["socket"] = "tcp:%s:%d" % method[1]
        elif method:
            self._new_site["socket"] = method

        elif "socket" in self._new_site:
            del self._new_site["socket"]

        if method == None and self._site_id != config.omd_site():
            raise MKUserError("method_sel", _("You can only configure a local site connection for "
                                              "the local site. The site IDs ('%s' and '%s') are "
                                              "not equal.") % (self._site_id, config.omd_site()))

        # Timeout
        if self._timeout != "":
            try:
                timeout = int(self._timeout)
            except:
                raise MKUserError("timeout", _("%s is not a valid integer number.") % self._timeout)
            self._new_site["timeout"] = timeout

        # Persist
        self._new_site["persist"] = html.get_checkbox("persist")

        # Status host
        if self._sh_site:
            if self._sh_site not in configured_sites:
                raise MKUserError("sh_site", _("The site of the status host does not exist."))
            if self._sh_site in [ self._site_id, self._id ]:
                raise MKUserError("sh_site", _("You cannot use the site itself as site of the status host."))
            if not self._sh_host:
                raise MKUserError("sh_host", _("Please specify the name of the status host."))
            self._new_site["status_host"] = ( self._sh_site, self._sh_host )
        else:
            self._new_site["status_host"] = None

        # Replication
        if self._repl == "none":
            self._repl = None
        self._new_site["replication"] = self._repl

        if self._repl:
            if not self._multisiteurl:
                raise MKUserError("multisiteurl",
                    _("Please enter the Multisite URL of the slave site."))

            if not self._multisiteurl.endswith("/check_mk/"):
                raise MKUserError("multisiteurl",
                    _("The Multisite URL must end with /check_mk/"))

            if not self._multisiteurl.startswith("http://") and \
               not self._multisiteurl.startswith("https://"):
                raise MKUserError("multisiteurl",
                    _("The Multisites URL must begin with <tt>http://</tt> or <tt>https://</tt>."))

            if "socket" not in self._new_site:
                raise MKUserError("replication",
                    _("You cannot do replication with the local site."))

        # Save Multisite-URL even if replication is turned off. That way that
        # setting is not lost if replication is turned off for a while.
        self._new_site["multisiteurl"] = self._multisiteurl

        # Disabling of WATO
        self._new_site["disable_wato"] = html.get_checkbox("disable_wato")

        # Handle the insecure replication flag
        self._new_site["insecure"] = html.get_checkbox("insecure")

        # Allow direct user login
        self._new_site["user_login"] = html.get_checkbox("user_login")

        # User synchronization
        user_sync = self._vs_user_sync().from_html_vars("user_sync")
        self._vs_user_sync().validate_value(user_sync, "user_sync")
        self._new_site["user_sync"] = user_sync

        # Event Console Replication
        self._new_site["replicate_ec"] = html.get_checkbox("replicate_ec")

        # MKPs and ~/local/
        self._new_site["replicate_mkps"] = html.get_checkbox("replicate_mkps")

        # Secret is not checked here, just kept
        if not self._new and "secret" in old_site:
            self._new_site["secret"] = old_site["secret"]

        # Do not forget to add those settings (e.g. "globals") that
        # are not edited with this dialog
        if not self._new:
            for key in old_site.keys():
                if key not in self._new_site and key != "socket":
                    self._new_site[key] = old_site[key]


    def page(self):
        html.begin_form("site")

        self._page_basic_settings()
        self._page_livestatus_settings()
        self._page_replication_configuration()

        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


    def _page_basic_settings(self):
        forms.header(_("Basic settings"))
        # ID
        forms.section(_("Site ID"), simple = not self._new)
        if self._new:
            html.text_input("id", self._site_id or self._clone_id)
            html.set_focus("id")
        else:
            html.write_text(self._site_id)

        # Alias
        forms.section(_("Alias"))
        html.text_input("alias", self._site.get("alias", ""), size = 60)
        if not self._new:
            html.set_focus("alias")
        html.help(_("An alias or description of the site"))


    def _page_livestatus_settings(self):
        forms.header(_("Livestatus settings"))
        forms.section(_("Connection"))
        method = self._site.get("socket", None)

        if type(method) == str and method.startswith("unix:"):
            method = ('unix', method[5:])

        elif type(method) == str and method.startswith("tcp:"):
            parts = method.split(":")[1:] # pylint: disable=no-member
            method = ('tcp', (parts[0], int(parts[1])))

        self._vs_conn_method().render_input("method", method)
        html.help( _("When connecting to remote site please make sure "
                   "that Livestatus over TCP is activated there. You can use UNIX sockets "
                   "to connect to foreign sites on localhost. Please make sure that this "
                   "site has proper read and write permissions to the UNIX socket of the "
                   "foreign site."))

        # Timeout
        forms.section(_("Connect Timeout"))
        timeout = self._site.get("timeout", 10)
        html.number_input("timeout", timeout, size=2)
        html.write_text(_(" seconds"))
        html.help(_("This sets the time that Multisite waits for a connection "
                     "to the site to be established before the site is considered to be unreachable. "
                     "If not set, the operating system defaults are begin used and just one login attempt is being. "
                     "performed."))

        # Persistent connections
        forms.section(_("Persistent Connection"), simple=True)
        html.checkbox("persist", self._site.get("persist", False), label=_("Use persistent connections"))
        html.help(_("If you enable persistent connections then Multisite will try to keep open "
                  "the connection to the remote sites. This brings a great speed up in high-latency "
                  "situations but locks a number of threads in the Livestatus module of the target site."))

        # URL-Prefix
        docu_url = "https://mathias-kettner.com/checkmk_multisite_modproxy.html"
        forms.section(_("URL prefix"))
        html.text_input("url_prefix", self._site.get("url_prefix", ""), size = 60)
        html.help(_("The URL prefix will be prepended to links of addons like PNP4Nagios "
                     "or the classical Nagios GUI when a link to such applications points to a host or "
                     "service on that site. You can either use an absolute URL prefix like <tt>http://some.host/mysite/</tt> "
                     "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you needed a mod_proxy "
                     "configuration in your local system apache that proxies such URLs to the according remote site. "
                     "Please refer to the <a target=_blank href='%s'>online documentation</a> for details. "
                     "The prefix should end with a slash. Omit the <tt>/pnp4nagios/</tt> from the prefix.") % docu_url)

        # Status-Host
        docu_url = "https://mathias-kettner.com/checkmk_multisite_statushost.html"
        forms.section(_("Status host"))

        sh = self._site.get("status_host")
        if sh:
            self._sh_site, self._sh_host = sh
        else:
            self._sh_site = ""
            self._sh_host = ""

        html.write_text(_("host: "))
        html.text_input("sh_host", self._sh_host, size=10)
        html.write_text(_(" on monitoring site: "))

        html.sorted_select("sh_site",
           [ ("", _("(no status host)")) ] + [
             (sk, si.get("alias", sk)) for (sk, si) in load_sites().items() ], self._sh_site)

        html.help( _("By specifying a status host for each non-local connection "
                     "you prevent Multisite from running into timeouts when remote sites do not respond. "
                     "You need to add the remote monitoring servers as hosts into your local monitoring "
                     "site and use their host state as a reachability state of the remote site. Please "
                     "refer to the <a target=_blank href='%s'>online documentation</a> for details.") % docu_url)

        # Disabled
        forms.section(_("Disable"), simple=True)
        html.checkbox("disabled", self._site.get("disabled", False), label = _("Temporarily disable this connection"))
        html.help( _("If you disable a connection, then no data of this site will be shown in the status GUI. "
                     "The replication is not affected by this, however."))


    def _page_replication_configuration(self):
        # Replication
        forms.header(_("Configuration Replication (Distributed WATO)"))
        forms.section(_("Replication method"))
        html.select("replication",
            [ (None,  _("No replication with this site")),
              ("slave", _("Slave: push configuration to this site"))
            ], self._site.get("replication"))
        html.help( _("WATO replication allows you to manage several monitoring sites with a "
                    "logically centralized WATO. Slave sites receive their configuration "
                    "from master sites. <br><br>Note: Slave sites "
                    "do not need any replication configuration. They will be remote-controlled "
                    "by the master sites."))

        forms.section(_("Multisite-URL of remote site"))
        html.text_input("multisiteurl", self._site.get("multisiteurl", ""), size=60)
        html.help( _("URL of the remote Check_MK including <tt>/check_mk/</tt>. "
                       "This URL is in many cases the same as the URL-Prefix but with <tt>check_mk/</tt> "
                       "appended, but it must always be an absolute URL. Please note, that "
                       "that URL will be fetched by the Apache server of the local "
                       "site itself, whilst the URL-Prefix is used by your local Browser."))

        forms.section(_("WATO"), simple=True)
        html.checkbox("disable_wato", self._site.get("disable_wato", True),
                      label = _('Disable configuration via WATO on this site'))
        html.help( _('It is a good idea to disable access to WATO completely on the slave site. '
                     'Otherwise a user who does not now about the replication could make local '
                     'changes that are overridden at the next configuration activation.'))

        forms.section(_("SSL"), simple=True)
        html.checkbox("insecure", self._site.get("insecure", False),
                      label = _('Ignore SSL certificate errors'))
        html.help( _('This might be needed to make the synchronization accept problems with '
                     'SSL certificates when using an SSL secured connection.'))

        forms.section(_('Direct login to Web GUI allowed'), simple=True)
        html.checkbox('user_login', self._site.get('user_login', True),
                      label = _('Users are allowed to directly login into the Web GUI of this site'))
        html.help(_('When enabled, this site is marked for synchronisation every time a Web GUI '
                    'related option is changed in the master site.'))

        forms.section(_("Sync with LDAP connections"), simple=True)
        self._vs_user_sync().render_input("user_sync",
                             self._site.get("user_sync", userdb.user_sync_default_config(self._site_id)))
        html.br()
        html.help(_('By default the users are synchronized automatically in the interval configured '
                    'in the connection. For example the LDAP connector synchronizes the users every '
                    'five minutes by default. The interval can be changed for each connection '
                    'individually in the <a href="wato.py?mode=ldap_config">connection settings</a>. '
                    'Please note that the synchronization is only performed on the master site in '
                    'distributed setups by default.<br>'
                    'The remote sites don\'t perform automatic user synchronizations with the '
                    'configured connections. But you can configure each site to either '
                    'synchronize the users with all configured connections or a specific list of '
                    'connections.')),

        if config.mkeventd_enabled:
            forms.section(_('Event Console'), simple=True)
            html.checkbox('replicate_ec', self._site.get("replicate_ec", True),
                          label = _("Replicate Event Console configuration to this site"))
            html.help(_("This option enables the distribution of global settings and rules of the Event Console "
                        "to the remote site. Any change in the local Event Console settings will mark the site "
                        "as <i>need sync</i>. A synchronization will automatically reload the Event Console of "
                        "the remote site."))

        forms.section(_("Extensions"), simple=True)
        html.checkbox("replicate_mkps", self._site.get("replicate_mkps", False),
                      label = _("Replicate extensions (MKPs and files in <tt>~/local/</tt>)"))
        html.help(_("If you enable the replication of MKPs then during each <i>Activate Changes</i> MKPs "
                    "that are installed on your master site and all other files below the <tt>~/local/</tt> "
                    "directory will be also transferred to the slave site. Note: <b>all other MKPs and files "
                    "below <tt>~/local/</tt> on the slave will be removed</b>."))


    def _vs_tcp_port(self):
        return Tuple(
                title = _("TCP Port to connect to"),
                orientation = "float",
                elements = [
                    TextAscii(label = _("Host:"), allow_empty = False, size=15),
                    Integer(label = _("Port:"), minvalue=1, maxvalue=65535, default_value=6557),
        ])

    def _conn_choices(self):
        conn_choices = [
            (None,   _("Connect to the local site")),
            ("tcp",  _("Connect via TCP"), self._vs_tcp_port()),
            ("unix", _("Connect via UNIX socket"), TextAscii(
                label = _("Path:"),
                size = 40,
                allow_empty = False)
            ),
        ]

        if config.liveproxyd_enabled:
            conn_choices[2:2] = [
            ( "proxy", _("Use Livestatus Proxy-Daemon"),
              Dictionary(
                  optional_keys = False,
                  columns = 1,
                  elements = [
                      ("socket", Alternative(
                          title = _("Connect to"),
                          style = "dropdown",
                          elements = [
                              FixedValue(None,
                                  title = _("Connect to the local site"),
                                  totext = "",
                              ),
                              self._vs_tcp_port(),
                          ],
                      )),
                      ( "channels",
                        Integer(
                            title = _("Number of channels to keep open"),
                            minvalue = 2,
                            maxvalue = 50,
                            default_value = 5)),
                      ( "heartbeat",
                        Tuple(
                            title = _("Regular heartbeat"),
                            orientation = "float",
                            elements = [
                                Integer(label = _("One heartbeat every"), unit=_("sec"),
                                        minvalue=1, default_value = 5),
                                Float(label = _("with a timeout of"), unit=_("sec"),
                                      minvalue=0.1, default_value = 2.0, display_format="%.1f"),
                       ])),
                       ( "channel_timeout",
                         Float(
                             title = _("Timeout waiting for a free channel"),
                             minvalue = 0.1,
                             default_value = 3,
                             unit = _("sec"),
                         )
                       ),
                       ( "query_timeout",
                         Float(
                             title = _("Total query timeout"),
                             minvalue = 0.1,
                             unit = _("sec"),
                             default_value = 120,
                         )
                       ),
                       ( "connect_retry",
                         Float(
                            title = _("Cooling period after failed connect/heartbeat"),
                            minvalue = 0.1,
                            unit = _("sec"),
                            default_value = 4.0,
                       )),
                       ( "cache",
                          Checkbox(title = _("Enable Caching"),
                             label = _("Cache several non-status queries"),
                              help = _("This option will enable the caching of several queries that "
                                       "need no current data. This reduces the number of Livestatus "
                                       "queries to sites and cuts down the response time of remote "
                                       "sites with large latencies."),
                              default_value = True,
                       )),
                    ]
                 )
              )
            ]
        return conn_choices


    def _vs_conn_method(self):
        # ValueSpecs for the more complex input fields
        return CascadingDropdown(
            orientation = "horizontal",
            choices = self._conn_choices(),
        )


    def _vs_user_sync(self):
        return CascadingDropdown(
            orientation = "horizontal",
            choices = [
                (None, _("Disable automatic user synchronization (use master site users)")),
                ("all", _("Sync users with all connections")),
                ("list", _("Sync with the following LDAP connections"), ListChoice(
                    choices = userdb.connection_choices,
                    allow_empty = False,
                )),
            ])



# Sort given sites argument by local, followed by slaves
# TODO: Change to sorted() mechanism
def sort_sites(sitelist):
    def custom_sort(a,b):
        return cmp(a[1].get("replication"), b[1].get("replication")) or \
               cmp(a[1].get("alias"), b[1].get("alias"))
    sitelist.sort(cmp = custom_sort)
    return sitelist


def get_check_mk_config_var_names():
    return [ varname for (varname, var) in configvars().items() if var[0] == ConfigDomainCore ]


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

def page_automation_login():
    if not config.user.may("wato.automation"):
        raise MKAuthException(_("This account has no permission for automation."))
    # When we are here, a remote (master) site has successfully logged in
    # using the credentials of the administrator. The login is done be exchanging
    # a login secret. If such a secret is not yet present it is created on
    # the fly.
    html.set_output_format("python")
    html.write_html(repr(get_login_secret(True)))


def page_automation():
    secret = html.var("secret")
    if not secret:
        raise MKAuthException(_("Missing secret for automation command."))
    if secret != get_login_secret():
        raise MKAuthException(_("Invalid automation secret."))

    # The automation page is accessed unauthenticated. After leaving the index.py area
    # into the page handler we always want to have a user context initialized to keep
    # the code free from special cases (if no user logged in, then...). So fake the
    # logged in user here.
    config.set_super_user()

    # To prevent mixups in written files we use the same lock here as for
    # the normal WATO page processing. This might not be needed for some
    # special automation requests, like inventory e.g., but to keep it simple,
    # we request the lock in all cases.
    lock_exclusive()

    init_wato_datastructures(with_wato_lock=False)

    command = html.var("command")
    if command == "checkmk-automation":
        cmk_command = html.var("automation")
        args        = mk_eval(html.var("arguments"))
        indata      = mk_eval(html.var("indata"))
        stdin_data  = mk_eval(html.var("stdin_data"))
        timeout     = mk_eval(html.var("timeout"))
        result = check_mk_local_automation(cmk_command, args, indata, stdin_data, timeout)
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        html.write(repr(result))

    elif command == "push-profile":
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(mk_repr(automation_push_profile()))
        except Exception, e:
            log_exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))

    elif command in automation_commands:
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(repr(automation_commands[command]()))
        except Exception, e:
            log_exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % \
                            (e, traceback.format_exc()))

    else:
        raise MKGeneralException(_("Invalid automation command: %s.") % command)

def automation_push_profile():
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
    profile = mk_eval(profile)
    users[user_id] = profile
    userdb.save_users(users)

    return True


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

def service_levels():
    try:
        return config.mkeventd_service_levels
    except:
        return [(0, "(no service level)")]

def load_notification_table():
    # Make sure, that list is not trivially false
    def validate_only_services(value, varprefix):
        for s in value:
            if s and s[0] != '!':
                return
        raise MKUserError(varprefix + "_0", _("The list of services will never match"))

    global vs_notification_method
    vs_notification_method = \
        CascadingDropdown(
            title = _("Notification Method"),
            choices = [
                ( "email", _("Plain Text Email (using configured templates)") ),
                ( "flexible",
                  _("Flexible Custom Notifications"),
                    ListOf(
                        Foldable(
                            Dictionary(
                                optional_keys = [ "service_blacklist", "only_hosts", "only_services", "escalation" , "match_sl"],
                                columns = 1,
                                headers = True,
                                elements = [
                                    (  "plugin",
                                       DropdownChoice(
                                            title = _("Notification Plugin"),
                                            choices = notification_script_choices,
                                            default_value = "mail",
                                        ),
                                    ),
                                    ( "parameters",
                                       ListOfStrings(
                                        title = _("Plugin Arguments"),
                                        help = _("You can specify arguments to the notification plugin here. "
                                                 "Please refer to the documentation about the plugin for what "
                                                 "parameters are allowed or required here."),
                                       )
                                    ),
                                    (  "disabled",
                                       Checkbox(
                                            title = _("Disabled"),
                                            label = _("Currently disable this notification"),
                                            default_value = False,
                                        )
                                    ),
                                    ( "timeperiod",
                                      TimeperiodSelection(
                                          title = _("Timeperiod"),
                                          help = _("Do only notifiy alerts within this time period"),
                                      )
                                    ),
                                    ( "escalation",
                                      Tuple(
                                          title = _("Restrict to n<sup>th</sup> to m<sup>th</sup> notification (escalation)"),
                                          orientation = "float",
                                          elements = [
                                              Integer(
                                                  label = _("from"),
                                                  help = _("Let through notifications counting from this number"),
                                                  default_value = 1,
                                                  minvalue = 1,
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
                                    ( "match_sl",
                                      Tuple(
                                        title = _("Match service level"),
                                        help = _("Host or Service must be in the following service level to get notification"),
                                        orientation = "horizontal",
                                        show_titles = False,
                                        elements = [
                                          DropdownChoice(label = _("from:"),  choices = service_levels, prefix_values = True),
                                          DropdownChoice(label = _(" to:"),  choices = service_levels, prefix_values = True),
                                        ],
                                      ),
                                    ),
                                  ( "host_events",
                                     ListChoice(
                                          title = _("Host Events"),
                                          choices = [
                                          ( 'd', _("Host goes down")),
                                          ( 'u', _("Host gets unreachble")),
                                          ( 'r', _("Host goes up again")),
                                          ( 'f', _("Start or end of flapping state")),
                                          ( 's', _("Start or end of a scheduled downtime ")),
                                          ( 'x', _("Acknowledgement of host problem")),
                                        ],
                                        default_value = [ 'd', 'u', 'r', 'f', 's', 'x' ],
                                    )
                                  ),
                                    ( "service_events",
                                      ListChoice(
                                          title = _("Service Events"),
                                          choices = [
                                            ( 'w', _("Service goes into warning state")),
                                            ( 'u', _("Service goes into unknown state")),
                                            ( 'c', _("Service goes into critical state")),
                                            ( 'r', _("Service recovers to OK")),
                                            ( 'f', _("Start or end of flapping state")),
                                            ( 's', _("Start or end of a scheduled downtime")),
                                            ( 'x', _("Acknowledgement of service problem")),
                                        ],
                                        default_value = [ 'w', 'c', 'u', 'r', 'f', 's', 'x' ],
                                    )
                                  ),
                                  ( "only_hosts",
                                    ListOfStrings(
                                        title = _("Limit to the following hosts"),
                                        help = _("Configure the hosts for this notification. Without prefix, only exact, case sensitive matches, "
                                                 "<tt>!</tt> for negation and <tt>~</tt> for regex matches."),
                                        orientation = "horizontal",
                                        # TODO: Clean this up to use an alternative between TextAscii() and RegExp(). Also handle the negation in a different way
                                        valuespec = TextAscii(
                                            size = 20,
                                        ),
                                    ),
                                  ),
                                  ( "only_services",
                                    ListOfStrings(
                                        title = _("Limit to the following services"),
                                        help = _("Configure regular expressions that match the beginning of the service names here. Prefix an "
                                                 "entry with <tt>!</tt> in order to <i>exclude</i> that service."),
                                        orientation = "horizontal",
                                        # TODO: Clean this up to use an alternative between TextAscii() and RegExp(). Also handle the negation in a different way
                                        valuespec = TextAscii(
                                            size = 20,
                                        ),
                                        validate = validate_only_services,
                                    ),
                                  ),
                                  ( "service_blacklist",
                                    ListOfStrings(
                                        title = _("Blacklist the following services"),
                                        help = _("Configure regular expressions that match the beginning of the service names here."),
                                        orientation = "horizontal",
                                        valuespec = RegExp(
                                            size = 20,
                                            mode = RegExp.prefix,
                                        ),
                                        validate = validate_only_services,
                                    ),
                                  ),
                                ]
                            ),
                            title_function = lambda v: _("Notify by: ") + notification_script_title(v["plugin"]),
                        ),
                        title = _("Flexible Custom Notifications"),
                        add_label = _("Add notification"),
                    ),
                ),
            ]
        )


def mode_users(phase):
    if phase == "title":
        return _("Users")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New User"), folder_preserving_link([("mode", "edit_user")]), "new")
        html.context_button(_("Custom Attributes"), folder_preserving_link([("mode", "user_attrs")]), "custom_attr")
        if userdb.sync_possible():
            html.context_button(_("Sync Users"), html.makeactionuri([("_sync", 1)]), "replicate")
        if config.user.may("general.notify"):
            html.context_button(_("Notify Users"), 'notify.py', "notification")
        html.context_button(_("LDAP Connections"), folder_preserving_link([("mode", "ldap_config")]), "ldap")
        return

    roles = userdb.load_roles()
    users = userdb.load_users(lock = phase == 'action' and html.var('_delete'))
    timeperiods = load_timeperiods()
    contact_groups = userdb.load_group_information().get("contact", {})

    if phase == "action":
        if html.var('_delete'):
            delid = html.get_unicode_input("_delete")
            c = wato_confirm(_("Confirm deletion of user %s") % delid,
                             _("Do you really want to delete the user %s?") % delid)
            if c:
                delete_users([delid])
            elif c == False:
                return ""

        elif html.var('_sync'):
            try:
                if userdb.hook_sync(add_to_changelog = True, raise_exc = True):
                    return None, _('The user synchronization completed successfully.')
            except Exception, e:
                if config.debug:
                    raise MKUserError(None, traceback.format_exc().replace('\n', '<br>\n'))
                else:
                    raise MKUserError(None, "%s" % e)

        elif html.var("_bulk_delete_users"):
            return bulk_delete_users_after_confirm(users)

        return None

    visible_custom_attrs = [
        (name, attr)
        for name, attr
        in userdb.get_user_attributes()
        if attr.get('show_in_table', False)
    ]

    entries = users.items()
    entries.sort(cmp = lambda a, b: cmp(a[1].get("alias", a[0]).lower(), b[1].get("alias", b[0]).lower()))

    html.begin_form("bulk_delete_form", method = "POST")

    table.begin("users", None, empty_text = _("No users are defined yet."))
    online_threshold = time.time() - config.user_online_maxage
    for id, user in entries:
        table.row()

        # Checkboxes
        table.cell("<input type=button class=checkgroup name=_toggle_group"
                   " onclick=\"toggle_all_rows();\" value=\"%s\" />" % _('X'),
                   sortable=False, css="buttons")

        if id != config.user.id:
            html.checkbox("_c_user_%s" % id)

        user_connection_id = userdb.cleanup_connection_id(user.get('connector'))
        connection = userdb.get_connection(user_connection_id)

        # Buttons
        table.cell(_("Actions"), css="buttons")
        if connection: # only show edit buttons when the connector is available and enabled
            edit_url = folder_preserving_link([("mode", "edit_user"), ("edit", id)])
            html.icon_button(edit_url, _("Properties"), "edit")

            clone_url = folder_preserving_link([("mode", "edit_user"), ("clone", id)])
            html.icon_button(clone_url, _("Create a copy of this user"), "clone")

        delete_url = make_action_link([("mode", "users"), ("_delete", id)])
        html.icon_button(delete_url, _("Delete"), "delete")

        notifications_url = folder_preserving_link([("mode", "user_notifications"), ("user", id)])
        if load_configuration_settings().get("enable_rulebased_notifications"):
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
        if user.get("disable_notifications", False):
            html.icon(_('Notifications are disabled'), 'notif_disabled')

        # Full name / Alias
        table.cell(_("Alias"), user.get("alias", ""))

        # Email
        table.cell(_("Email"), user.get("email", ""))

        # Roles
        table.cell(_("Roles"))
        if user.get("roles", []):
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (folder_preserving_link([("mode", "edit_role"), ("edit", r)]), roles[r].get('alias')) for r in user["roles"]]))

        # contact groups
        table.cell(_("Contact groups"))
        cgs = user.get("contactgroups", [])
        if cgs:
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (folder_preserving_link([("mode", "edit_contact_group"), ("edit", c)]),
                                          c in contact_groups and contact_groups[c]['alias'] or c) for c in cgs]))
        else:
            html.i(_("none"))

        # notifications
        if not load_configuration_settings().get("enable_rulebased_notifications"):
            table.cell(_("Notifications"))
            if not cgs:
                html.i(_("not a contact"))
            elif not user.get("notifications_enabled", True):
                html.write_text(_("disabled"))
            elif "" == user.get("host_notification_options", "") \
                and "" == user.get("service_notification_options", ""):
                html.write_text(_("all events disabled"))
            else:
                tp = user.get("notification_period", "24X7")
                if tp != "24X7" and tp not in timeperiods:
                    tp = tp + _(" (invalid)")
                elif tp != "24X7":
                    url = folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tp)])
                    tp = '<a href="%s">%s</a>' % (url, timeperiods[tp].get("alias", tp))
                else:
                    tp = _("Always")
                html.write(tp)

        # the visible custom attributes
        for name, attr in visible_custom_attrs:
            vs = attr['valuespec']
            table.cell(_u(vs.title()))
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



def bulk_delete_users_after_confirm(users):
    selected_users = []
    for varname in html.all_varnames_with_prefix("_c_user_"):
        if html.get_checkbox(varname):
            user = varname.split("_c_user_")[-1]
            if user in users:
                selected_users.append(user)

    if selected_users:
        c = wato_confirm(_("Confirm deletion of %d users") % len(selected_users),
                         _("Do you really want to delete %d users?") % len(selected_users))
        if c:
            delete_users(selected_users)
        elif c == False:
            return ""


def mode_edit_user(phase):
    # Check if rule based notifications are enabled (via WATO)
    rulebased_notifications = load_configuration_settings().get("enable_rulebased_notifications")

    users   = userdb.load_users(lock = phase == 'action')
    user_id = html.get_unicode_input("edit") # missing -> new user
    cloneid = html.get_unicode_input("clone") # Only needed in 'new' mode
    is_new_user = user_id == None
    if phase == "title":
        if is_new_user:
            return _("Create new user")
        else:
            return _("Edit user %s") % user_id

    elif phase == "buttons":
        html.context_button(_("All Users"), folder_preserving_link([("mode", "users")]), "back")
        if rulebased_notifications and not is_new_user:
            html.context_button(_("Notifications"), folder_preserving_link([("mode", "user_notifications"),
                    ("user", user_id)]), "notifications")
        return

    if is_new_user:
        if cloneid:
            user = users.get(cloneid, userdb.new_user_template('htpasswd'))
        else:
            user = userdb.new_user_template('htpasswd')
        pw_suffix = 'new'
    else:
        user = users.get(user_id, userdb.new_user_template('htpasswd'))
        pw_suffix = base64.b64encode(user_id.encode("utf-8"))

    user_attrs = {}
    # Returns true if an attribute is locked and should be read only. Is only
    # checked when modifying an existing user
    locked_attributes = userdb.locked_attributes(user.get('connector'))
    user_attrs["locked_attributes"] = locked_attributes

    def is_locked(attr):
        return not is_new_user and attr in user_attrs["locked_attributes"]

    def custom_user_attributes(topic = None):
        for name, attr in userdb.get_user_attributes():
            if topic is not None and topic != attr['topic']:
                continue # skip attrs of other topics

            vs = attr['valuespec']
            forms.section(_u(vs.title()))
            if attr['user_editable'] and not is_locked(name):
                vs.render_input("ua_" + name, user.get(name, vs.default_value()))
            else:
                html.write(vs.value_to_text(user.get(name, vs.default_value())))
                # Render hidden to have the values kept after saving
                html.open_div(style="display:none")
                vs.render_input("ua_" + name, user.get(name, vs.default_value()))
                html.close_div()
            html.help(_u(vs.help()))


    # Load data that is referenced - in order to display dropdown
    # boxes and to check for validity.
    contact_groups = userdb.load_group_information().get("contact", {})
    timeperiods    = load_timeperiods()
    roles          = userdb.load_roles()

    if cmk.is_managed_edition():
        vs_customer = managed.vs_customer()

    if phase == "action":
        if not html.check_transaction():
            return "users"

        if is_new_user:
            user_id = UserID(allow_empty = False).from_html_vars("user_id")
        else:
            user_id = html.get_unicode_input("edit").strip()
            user_attrs = users[user_id]

        # Full name
        user_attrs["alias"] = html.get_unicode_input("alias").strip()

        # Locking
        user_attrs["locked"] = html.get_checkbox("locked")
        increase_serial = False

        if user_id in users and users[user_id]["locked"] != user_attrs["locked"] and user_attrs["locked"]:
            increase_serial = True # when user is being locked now, increase the auth serial

        # Authentication: Password or Secret
        auth_method = html.var("authmethod")
        if auth_method == "secret":
            secret = html.var("secret", "").strip()
            user_attrs["automation_secret"] = secret
            user_attrs["password"] = userdb.encrypt_password(secret)
            increase_serial = True # password changed, reflect in auth serial

        else:
            password  = html.var("password_" + pw_suffix, '').strip()
            password2 = html.var("password2_" + pw_suffix, '').strip()

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
                user_attrs["password"] = userdb.encrypt_password(password)
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

        idle_timeout = get_vs_user_idle_timeout().from_html_vars("idle_timeout")
        user_attrs["idle_timeout"] = idle_timeout
        if idle_timeout != None:
            user_attrs["idle_timeout"] = idle_timeout
        elif idle_timeout == None and "idle_timeout" in user_attrs:
            del user_attrs["idle_timeout"]

        # Pager
        user_attrs["pager"] = html.var("pager", '').strip()

        if cmk.is_managed_edition():
            customer = vs_customer.from_html_vars("customer")
            vs_customer.validate_value(customer, "customer")

            if customer != managed.default_customer_id():
                user_attrs["customer"] = customer
            elif "customer" in user_attrs:
                del user_attrs["customer"]

        # Roles
        user_attrs["roles"] = filter(lambda role: html.get_checkbox("role_" + role),
                                   roles.keys())

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
        for c in contact_groups:
            if html.get_checkbox("cg_" + c):
                cgs.append(c)
        user_attrs["contactgroups"] = cgs

        # Notification settings are only active if we do *not* have
        # rule based notifications!
        if not rulebased_notifications:
            # Notifications
            user_attrs["notifications_enabled"] = html.get_checkbox("notifications_enabled")

            ntp = html.var("notification_period")
            if ntp not in timeperiods:
                ntp = "24X7"
            user_attrs["notification_period"] = ntp

            for what, opts in [ ( "host", "durfs"), ("service", "wucrfs") ]:
                user_attrs[what + "_notification_options"] = "".join(
                  [ opt for opt in opts if html.get_checkbox(what + "_" + opt) ])

            value = vs_notification_method.from_html_vars("notification_method")
            user_attrs["notification_method"] = value
        else:
            user_attrs["fallback_contact"] = html.get_checkbox("fallback_contact")

        # Custom user attributes
        for name, attr in userdb.get_user_attributes():
            value = attr['valuespec'].from_html_vars('ua_' + name)
            user_attrs[name] = value

        # Generate user "object" to update
        user_object = {user_id: {"attributes": user_attrs, "is_new_user": is_new_user}}
        # The following call validates and updated the users
        edit_users(user_object)
        return "users"

    # Let exceptions from loading notification scripts happen now
    load_notification_scripts()

    html.begin_form("user", method="POST")
    html.prevent_password_auto_completion()

    forms.header(_("Identity"))

    # ID
    forms.section(_("Username"), simple = not is_new_user)
    if is_new_user:
        vs_user_id = UserID(allow_empty = False)

    else:
        vs_user_id = FixedValue(user_id)
    vs_user_id.render_input("user_id", user_id)

    def lockable_input(name, dflt):
        if not is_locked(name):
            html.text_input(name, user.get(name, dflt), size = 50)
        else:
            html.write_text(user.get(name, dflt))
            html.hidden_field(name, user.get(name, dflt))

    # Full name
    forms.section(_("Full name"))
    lockable_input('alias', user_id)
    html.help(_("Full name or alias of the user"))

    # Email address
    forms.section(_("Email address"))
    email = user.get("email", "")
    if not is_locked("email"):
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
        forms.section(vs_customer.title())
        vs_customer.render_input("customer", managed.get_customer_id(user))

        html.help(vs_customer.help())

    custom_user_attributes('ident')

    forms.header(_("Security"))
    forms.section(_("Authentication"))

    is_automation = user.get("automation_secret", None) != None
    html.radiobutton("authmethod", "password", not is_automation,
                     _("Normal user login with password"))
    html.open_ul()
    html.open_table()
    html.open_tr()
    html.td(_("password:"))
    html.open_td()

    if not is_locked('password'):
        html.password_input("password_" + pw_suffix, autocomplete="new-password")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td(_("repeat:"))
        html.open_td()
        html.password_input("password2_" + pw_suffix, autocomplete="new-password")
        html.write_text(" (%s)" % _("optional"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td("%s:" % _("Enforce change"))
        html.open_td()
        # Only make password enforcement selection possible when user is allowed to change the PW
        if is_new_user or config.user_may(user_id, 'general.edit_profile') and config.user_may(user_id, 'general.change_password'):
            html.checkbox("enforce_pw_change", user.get("enforce_pw_change", False),
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
    html.text_input("secret", user.get("automation_secret", ""), size=30,
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
    if not is_locked('locked'):
        html.checkbox("locked", user.get("locked", False), label = _("disable the login to this account"))
    else:
        html.write_text(_('Login disabled') if user.get("locked", False) else _('Login possible'))
        html.hidden_field('locked', user.get("locked", False) and '1' or '')
    html.help(_("Disabling the password will prevent a user from logging in while "
                 "retaining the original password. Notifications are not affected "
                 "by this setting."))

    forms.section(_("Idle timeout"))
    idle_timeout = user.get("idle_timeout")
    if not is_locked("idle_timeout"):
        get_vs_user_idle_timeout().render_input("idle_timeout", idle_timeout)
    else:
        html.write_text(idle_timeout)
        html.hidden_field("idle_timeout", idle_timeout)

    # Roles
    forms.section(_("Roles"))
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))
    is_member_of_at_least_one = False
    for role_id, role in entries:
        if not is_locked("roles"):
            html.checkbox("role_" + role_id, role_id in user.get("roles", []))
            url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
            html.a(role["alias"], href=url)
            html.br()
        else:
            is_member = role_id in user.get("roles", [])
            if is_member:
                is_member_of_at_least_one = True
                url = folder_preserving_link([("mode", "edit_role"), ("edit", role_id)])
                html.a(role["alias"], href=url)
                html.br()

            html.hidden_field("role_" + role_id, is_member and '1' or '')
    if is_locked('roles') and not is_member_of_at_least_one:
        html.i(_('No roles assigned.'))
    custom_user_attributes('security')

    # Contact groups
    forms.header(_("Contact Groups"), isopen=False)
    forms.section()
    groups_page_url  = folder_preserving_link([("mode", "contact_groups")])
    group_assign_url = folder_preserving_link([("mode", "rulesets"), ("group", "grouping")])
    if len(contact_groups) == 0:
        html.write(_("Please first create some <a href='%s'>contact groups</a>") %
                groups_page_url)
    else:
        entries = sorted([ (group['alias'], c) for c, group in contact_groups.items() ])
        is_member_of_at_least_one = False
        for alias, gid in entries:
            if not alias:
                alias = gid

            if not is_locked('contactgroups'):
                html.checkbox("cg_" + gid, gid in user.get("contactgroups", []))
            else:
                is_member = gid in user.get("contactgroups", [])
                if is_member:
                    is_member_of_at_least_one = True
                html.hidden_field("cg_" + gid, '1' if is_member else '')

            url = folder_preserving_link([("mode", "edit_contact_group"), ("edit", gid)])
            html.a(alias, href=url)
            html.br()

        if is_locked('contactgroups') and not is_member_of_at_least_one:
            html.i(_('No contact groups assigned.'))

    html.help(_("Contact groups are used to assign monitoring "
                "objects to users. If you haven't defined any contact groups yet, "
                "then first <a href='%s'>do so</a>. Hosts and services can be "
                "assigned to contact groups using <a href='%s'>rules</a>.<br><br>"
                "If you do not put the user into any contact group "
                "then no monitoring contact will be created for the user.") %
                                    (groups_page_url, group_assign_url))

    forms.header(_("Notifications"), isopen=False)
    if not rulebased_notifications:
        forms.section(_("Enabling"), simple=True)
        html.checkbox("notifications_enabled", user.get("notifications_enabled", False),
             label = _("enable notifications"))
        html.help(_("Notifications are sent out "
                    "when the status of a host or service changes."))

        # Notification period
        forms.section(_("Notification time period"))
        choices = [ ( "24X7", _("Always")) ] + \
                  [ ( id, "%s" % (tp["alias"])) for (id, tp) in timeperiods.items() ]
        html.sorted_select("notification_period", choices, user.get("notification_period"))
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

            user_opts = user.get(what + "_notification_options", opts)
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
        vs_notification_method.render_input("notification_method", user.get("notification_method"))
        custom_user_attributes('notify')

    else:
        forms.section(_("Fallback notifications"), simple=True)

        html.checkbox("fallback_contact", False, label = _("Receive fallback notifications"))

        html.help(_("In case none of your notification rules handles a certain event a notification "
                 "will be sent to this contact. This makes sure that in that case at least <i>someone</i> "
                 "gets notified. Furthermore this contact will be used for notifications to any host or service "
                 "that is not known to the monitoring. This can happen when you forward notifications "
                 "from the Event Console.<br><br>Notification fallback can also configured in the global "
                 "setting <a href=\"wato.py?mode=edit_configvar&varname=notification_fallback_email\">"
                    "Fallback email address for notifications</a>."))

    forms.header(_("Personal Settings"), isopen = False)
    select_language(user)
    custom_user_attributes('personal')

    # Later we could add custom macros here, which then could be used
    # for notifications. On the other hand, if we implement some check_mk
    # --notify, we could directly access the data in the account with the need
    # to store values in the monitoring core. We'll see what future brings.
    forms.end()
    html.button("save", _("Save"))
    if is_new_user:
        html.set_focus("user_id")
    else:
        html.set_focus("alias")
    html.hidden_fields()
    html.end_form()



def generate_wato_users_elements_function(none_value, only_contacts = False):
    def get_wato_users(nv):
        users = userdb.load_users()
        elements = [ (name, "%s - %s" % (name, us.get("alias", name)))
                     for (name, us)
                     in users.items()
                     if (not only_contacts or us.get("contactgroups")) ]
        elements.sort()
        if nv != None:
            elements = [ (None, none_value) ] + elements
        return elements
    return lambda: get_wato_users(none_value)


# Dropdown for choosing a multisite user
class UserSelection(DropdownChoice):
    def __init__(self, **kwargs):
        only_contacts = kwargs.get("only_contacts", False)
        kwargs["choices"] = generate_wato_users_elements_function(kwargs.get("none"), only_contacts = only_contacts)
        kwargs["invalid_choice"] = "complain" # handle vanished users correctly!
        DropdownChoice.__init__(self, **kwargs)

    def value_to_text(self, value):
        text = DropdownChoice.value_to_text(self, value)
        return text.split(" - ")[-1]


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

def mode_roles(phase):
    if phase == "title":
        return _("Roles & Permissions")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Matrix"), folder_preserving_link([("mode", "role_matrix")]), "matrix")
        return

    roles = userdb.load_roles()
    users = userdb.load_users()

    if phase == "action":
        if html.var("_delete"):
            delid = html.var("_delete")

            if delid not in roles:
                raise MKUserError(None, _("This role does not exist."))

            if html.transaction_valid() and roles[delid].get('builtin'):
                raise MKUserError(None, _("You cannot delete the builtin roles!"))

            c = wato_confirm(_("Confirm deletion of role %s") % delid,
                             _("Do you really want to delete the role %s?") % delid)
            if c:
                rename_user_role(delid, None) # Remove from existing users
                del roles[delid]
                save_roles(roles)
                add_change("edit-roles", _("Deleted role '%s'") % delid, sites=get_login_sites())
            elif c == False:
                return ""
        elif html.var("_clone"):
            if html.check_transaction():
                cloneid = html.var("_clone")

                try:
                    cloned_role = roles[cloneid]
                except KeyError:
                    raise MKUserError(None, _("This role does not exist."))

                newid = cloneid
                while newid in roles:
                    newid += "x"

                new_role = {}
                new_role.update(cloned_role)

                new_alias = new_role["alias"]
                while not is_alias_used("roles", newid, new_alias)[0]:
                    new_alias += _(" (copy)")
                new_role["alias"] = new_alias

                if cloned_role.get("builtin"):
                    new_role["builtin"] = False
                    new_role["basedon"] = cloneid

                roles[newid] = new_role
                save_roles(roles)
                add_change("edit-roles", _("Created new role '%s'") % newid,
                           sites=get_login_sites())
        return

    table.begin("roles")

    # Show table of builtin and user defined roles
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))

    for id, role in entries:
        table.row()

        # Actions
        table.cell(_("Actions"), css="buttons")
        edit_url = folder_preserving_link([("mode", "edit_role"), ("edit", id)])
        clone_url = make_action_link([("mode", "roles"), ("_clone", id)])
        delete_url = make_action_link([("mode", "roles"), ("_delete", id)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Clone"), "clone")
        if not role.get("builtin"):
            html.icon_button(delete_url, _("Delete this role"), "delete")

        # ID
        table.cell(_("Name"), id)

        # Alias
        table.cell(_("Alias"), role["alias"])

        # Type
        table.cell(_("Type"), role.get("builtin") and _("builtin") or _("custom"))

        # Modifications
        table.cell(_("Modifications"), "<span title='%s'>%s</span>" % (
            _("That many permissions do not use the factory defaults."), len(role["permissions"])))

        # Users
        table.cell(_("Users"),
          ", ".join([ '<a href="%s">%s</a>' % (folder_preserving_link([("mode", "edit_user"), ("edit", user_id)]),
             user.get("alias", user_id))
            for (user_id, user) in users.items() if (id in user["roles"])]))


    # Possibly we could also display the following information
    # - number of set permissions (needs loading users)
    # - number of users with this role
    table.end()





def mode_edit_role(phase):
    role_id = html.var("edit")

    if phase == "title":
        return _("Edit user role %s") % role_id

    elif phase == "buttons":
        html.context_button(_("All Roles"), folder_preserving_link([("mode", "roles")]), "back")
        return

    # Make sure that all dynamic permissions are available (e.g. those for custom
    # views)
    config.load_dynamic_permissions()
    roles = userdb.load_roles()

    try:
        role = roles[role_id]
    except KeyError:
        raise MKGeneralException(_("This role does not exist."))

    search = get_search_expression()

    if phase == "action":
        if html.form_submitted("search"):
            return

        alias = html.get_unicode_input("alias")

        unique, info = is_alias_used("roles", role_id, alias)
        if not unique:
            raise MKUserError("alias", info)

        new_id = html.var("id")
        if len(new_id) == 0:
            raise MKUserError("id", _("Please specify an ID for the new role."))
        if not re.match("^[-a-z0-9A-Z_]*$", new_id):
            raise MKUserError("id", _("Invalid role ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
        if new_id != role_id:
            if new_id in roles:
                raise MKUserError("id", _("The ID is already used by another role"))

        role["alias"] = alias

        # based on
        if not role.get("builtin"):
            basedon = html.var("basedon")
            if basedon not in config.builtin_role_ids:
                raise MKUserError("basedon", _("Invalid valid for based on. Must be id of builtin rule."))
            role["basedon"] = basedon

        # Permissions
        permissions = role["permissions"]
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

        if role_id != new_id:
            roles[new_id] = role
            del roles[role_id]
            rename_user_role(role_id, new_id)

        save_roles(roles)
        add_change("edit-roles", _("Modified user role '%s'") % new_id, sites=get_login_sites())
        return "roles"

    search_form(_("Search for permissions: "), "edit_role")

    html.begin_form("role", method="POST")

    # ID
    forms.header(_("Basic Properties"))
    forms.section(_("Internal ID"), simple = "builtin" in role)
    if role.get("builtin"):
        html.write_text("%s (%s)" % (role_id, _("builtin role")))
        html.hidden_field("id", role_id)
    else:
        html.text_input("id", role_id)
        html.set_focus("id")

    # Alias
    forms.section(_("Alias"))
    html.help(_("An alias or description of the role"))
    html.text_input("alias", role.get("alias", ""), size = 50)

    # Based on
    if not role.get("builtin"):
        forms.section(_("Based on role"))
        html.help(_("Each user defined role is based on one of the builtin roles. "
                    "When created it will start with all permissions of that role. When due to a software "
                    "update or installation of an addons new permissions appear, the user role will get or "
                    "not get those new permissions based on the default settings of the builtin role it's "
                    "based on."))
        choices = [ (i, r["alias"]) for i, r in roles.items() if r.get("builtin") ]
        html.sorted_select("basedon", choices, role.get("basedon", "user"))


    forms.end()

    html.h2(_("Permissions"))

    # Permissions
    base_role_id = role.get("basedon", role_id)

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

            pvalue = role["permissions"].get(pname)
            def_value = base_role_id in perm["defaults"]

            choices = [ ( "yes", _("yes")),
                        ( "no", _("no")),
                        ( "default", _("default (%s)") % (def_value and _("yes") or _("no") )) ]
            html.select("perm_" + pname, choices, { True: "yes", False: "no" }.get(pvalue, "default"), attrs={"style": "width: 130px;"} )

            html.help(perm["description"])

    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def make_unicode(s):
    if type(s) != unicode: # assume utf-8 encoded bytestring
        return s.decode("utf-8")
    else:
        return s

def save_roles(roles):
    # Reflect the data in the roles dict kept in the config module Needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    config.roles.update(roles)

    make_nagios_directory(multisite_dir)
    store.save_to_mk_file(multisite_dir + "roles.mk", "roles", roles)

    call_hook_roles_saved(roles)


# Adapt references in users. Builtin rules cannot
# be renamed and are not handled here. If new_id is None,
# the role is being deleted
def rename_user_role(id, new_id):
    users = userdb.load_users(lock = True)
    for user in users.values():
        if id in user["roles"]:
            user["roles"].remove(id)
            if new_id:
                user["roles"].append(new_id)
    userdb.save_users(users)

def mode_role_matrix(phase):
    if phase == "title":
        return _("Role & Permission Matrix")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Back"), folder_preserving_link([("mode", "roles")]), "back")
        return

    elif phase == "action":
        return

    # Show table of builtin and user defined roles, sorted by alias
    roles = userdb.load_roles()
    role_list = roles.items()
    role_list.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))

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

def mode_hosttags(phase):
    if phase == "title":
        return _("Host tag groups")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Tag group"), folder_preserving_link([("mode", "edit_hosttag")]), "new")
        html.context_button(_("New Aux tag"), folder_preserving_link([("mode", "edit_auxtag")]), "new")
        return

    hosttags, auxtags = load_hosttags()
    builtin_hosttags, builtin_auxtags = load_builtin_hosttags()

    if phase == "action":
        # Deletion of tag groups
        del_id = html.var("_delete")
        if del_id:
            operations = None
            for e in hosttags:
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
                hosttags = [ e for e in hosttags if e[0] != del_id ]
                save_hosttags(hosttags, auxtags)
                Folder.invalidate_caches()
                Folder.root_folder().rewrite_hosts_files()
                add_change("edit-hosttags", _("Removed host tag group %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        # Deletion of auxiliary tags
        del_nr = html.var("_delaux")
        if del_nr:
            nr = int(del_nr)
            del_id = auxtags[nr][0]

            # Make sure that this aux tag is not begin used by any tag group
            for entry in hosttags:
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
                del auxtags[nr]
                # Remove auxiliary tag from all host tags
                for e in hosttags:
                    choices = e[2]
                    for choice in choices:
                        if len(choice) > 2:
                            if del_id in choice[2]:
                                choice[2].remove(del_id)

                save_hosttags(hosttags, auxtags)
                Folder.invalidate_caches()
                Folder.root_folder().rewrite_hosts_files()
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
                moved = hosttags[move_nr]
                del hosttags[move_nr]
                hosttags[move_nr+dir:move_nr+dir] = [moved]
                save_hosttags(hosttags, auxtags)
                config.wato_host_tags = hosttags
                add_change("edit-hosttags", _("Changed order of host tag groups"))
        return

    if not hosttags + auxtags:
        render_main_menu([
            ("edit_hosttag", _("Create new tag group"), "new", "hosttags",
                _("Each host tag group will create one dropdown choice in the host configuration.")),
            ("edit_auxtag", _("Create new auxiliary tag"), "new", "hosttags",
                _("You can have these tags automatically added if certain primary tags are set.")),
            ])

    else:
        render_host_tag_list(hosttags, builtin_hosttags)
        render_aux_tag_list(auxtags, builtin_auxtags)


def render_host_tag_list(hosttags, builtin_hosttags):
    table.begin("hosttags", _("Host tag groups"),
                help = (_("Host tags are the basis of Check_MK's rule based configuration. "
                         "If the first step you define arbitrary tag groups. A host "
                         "has assigned exactly one tag out of each group. These tags can "
                         "later be used for defining parameters for hosts and services, "
                         "such as <i>disable notifications for all hosts with the tags "
                         "<b>Network device</b> and <b>Test</b></i>.")),
                empty_text = _("You haven't defined any tag groups yet."),
                searchable = False, sortable = False)

    if not hosttags + builtin_hosttags:
        table.end()
        return

    for tag_type, tag_list in [ ('custom', hosttags),
                                ('builtin', builtin_hosttags), ]:
        for nr, entry in enumerate(tag_list):
            tag_id, title, choices = entry[:3] # fourth: tag dependency information
            topic, title = map(_u, parse_hosttag_title(title))
            table.row()
            table.cell(_("Actions"), css="buttons")
            if tag_type == "builtin":
                html.i("(builtin)")
            else:
                edit_url     = folder_preserving_link([("mode", "edit_hosttag"), ("edit", tag_id)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delete", tag_id)])
                if nr == 0:
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(-nr))]),
                                _("Move this tag group one position up"), "up")
                if nr == len(tag_list) - 1:
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(nr))]),
                                _("Move this tag group one position down"), "down")
                html.icon_button(edit_url,   _("Edit this tag group"), "edit")
                html.icon_button(delete_url, _("Delete this tag group"), "delete")

            table.cell(_("ID"), tag_id)
            table.cell(_("Title"), title)
            table.cell(_("Topic"), topic or '')
            table.cell(_("Type"), (len(choices) == 1 and _("Checkbox") or _("Dropdown")))
            table.cell(_("Choices"), str(len(choices)))
            table.cell(_("Demonstration"), sortable=False)
            html.begin_form("tag_%s" % tag_id)
            host_attribute("tag_%s" % tag_id).render_input("", None)
            html.end_form()
    table.end()



def render_aux_tag_list(auxtags, builtin_auxtags):
    table.begin("auxtags", _("Auxiliary tags"),
                help = _("Auxiliary tags can be attached to other tags. That way "
                         "you can for example have all hosts with the tag <tt>cmk-agent</tt> "
                         "get also the tag <tt>tcp</tt>. This makes the configuration of "
                         "your hosts easier."),
                empty_text = _("You haven't defined any auxiliary tags."),
                searchable = False)

    if not auxtags:
        table.end()
        return

    for tag_type, tag_list in [ ('custom', auxtags),
                                ('builtin', builtin_auxtags), ]:
        for nr, (tag_id, title) in enumerate(tag_list):
            table.row()
            topic, title = parse_hosttag_title(title)
            table.cell(_("Actions"), css="buttons")
            if tag_type == "builtin":
                html.i("(builtin)")
            else:
                edit_url     = folder_preserving_link([("mode", "edit_auxtag"), ("edit", nr)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delaux", nr)])
                html.icon_button(edit_url, _("Edit this auxiliary tag"), "edit")
                html.icon_button(delete_url, _("Delete this auxiliary tag"), "delete")
            table.cell(_("ID"), tag_id)

            table.cell(_("Title"), _u(title))
            table.cell(_("Topic"), _u(topic) or '')
    table.end()


def mode_edit_auxtag(phase):
    tag_nr = html.var("edit")
    new = tag_nr == None
    if not new:
        tag_nr = int(tag_nr)

    if phase == "title":
        if new:
            return _("Create new auxiliary tag")
        else:
            return _("Edit auxiliary tag")

    elif phase == "buttons":
        html.context_button(_("All Hosttags"), folder_preserving_link([("mode", "hosttags")]), "back")
        return

    hosttags, auxtags = load_hosttags()

    vs_topic = OptionalDropdownChoice(
        title = _("Topic") + "<sup>*</sup>",
        choices = hosttag_topics(hosttags, auxtags),
        explicit = TextUnicode(),
        otherlabel = _("Create New Topic"),
        default_value = None,
        sorted = True
    )

    if phase == "action":
        if html.transaction_valid():
            html.check_transaction() # use up transaction id
            if new:
                tag_id = html.var("tag_id").strip()
                if not tag_id:
                    raise MKUserError("tag_id", _("Please enter a tag ID"))
                validate_tag_id(tag_id, "tag_id")
            else:
                tag_id = auxtags[tag_nr][0]

            title = html.get_unicode_input("title").strip()
            if not title:
                raise MKUserError("title", _("Please supply a title "
                "for you auxiliary tag."))

            topic = forms.get_input(vs_topic, "topic")
            if topic != '':
                title = '%s/%s' % (topic, title)

            # Make sure that this ID is not used elsewhere
            for entry in configured_host_tags():
                tgid = entry[0]
                tit  = entry[1]
                ch   = entry[2]
                for e in ch:
                    if e[0] == tag_id:
                        raise MKUserError("tag_id",
                        _("This tag id is already being used "
                          "in the host tag group %s") % tit)

            for nr, (id, name) in enumerate(auxtags):
                if nr != tag_nr and id == tag_id:
                    raise MKUserError("tag_id",
                    _("This tag id does already exist in the list "
                      "of auxiliary tags."))

            if new:
                auxtags.append((tag_id, title))
            else:
                auxtags[tag_nr] = (tag_id, title)
            save_hosttags(hosttags, auxtags)
        return "hosttags"


    if new:
        title = ""
        tag_id = ""
        topic = ""
    else:
        tag_id, title = auxtags[tag_nr]
        topic, title = parse_hosttag_title(title)

    html.begin_form("auxtag")
    forms.header(_("Auxiliary Tag"))

    # Tag ID
    forms.section(_("Tag ID"))
    if new:
        html.text_input("tag_id", "")
        html.set_focus("tag_id")
    else:
        html.write_text(tag_id)
    html.help(_("The internal name of the tag. The special tags "
                "<tt>snmp</tt>, <tt>tcp</tt> and <tt>ping</tt> can "
                "be used here in order to specify the agent type."))

    # Title
    forms.section(_("Title") + "<sup>*</sup>")
    html.text_input("title", title, size = 30)
    html.help(_("An alias or description of this auxiliary tag"))

    # The (optional) topic
    forms.section(_("Topic") + "<sup>*</sup>")
    html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                "selections in the GUI more comfortable."))
    forms.input(vs_topic, "topic", topic)

    # Button and end
    forms.end()
    html.show_localization_hint()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

# Validate the syntactic form of a tag
def validate_tag_id(id, varname):
    if not re.match("^[-a-z0-9A-Z_]*$", id):
        raise MKUserError(varname,
            _("Invalid tag ID. Only the characters a-z, A-Z, "
              "0-9, _ and - are allowed."))

def mode_edit_hosttag(phase):
    tag_id = html.var("edit")
    new = tag_id == None

    if phase == "title":
        if new:
            return _("Create new tag group")
        else:
            return _("Edit tag group")

    elif phase == "buttons":
        html.context_button(_("All Hosttags"), folder_preserving_link([("mode", "hosttags")]), "back")
        return

    hosttags, auxtags = load_hosttags()
    title = ""
    choices = []
    topic = None
    if not new:
        for entry in hosttags:
            id, tit, ch = entry[:3]
            if id == tag_id:
                topic, title = parse_hosttag_title(tit)
                choices = ch
                break

    vs_topic = OptionalDropdownChoice(
        title = _("Topic"),
        choices = hosttag_topics(hosttags, auxtags),
        explicit = TextUnicode(),
        otherlabel = _("Create New Topic"),
        default_value = None,
        sorted = True
    )

    vs_choices = ListOf(
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
                        choices = auxtags)),

            ],
            show_titles = True,
            orientation = "horizontal"),

        add_label = _("Add tag choice"),
        row_label = "@. Choice")

    if phase == "action":
        if html.transaction_valid():
            if new:
                html.check_transaction() # use up transaction id
                tag_id = html.var("tag_id").strip()
                validate_tag_id(tag_id, "tag_id")
                if len(tag_id) == 0:
                    raise MKUserError("tag_id", _("Please specify an ID for your tag group."))
                if not re.match("^[-a-z0-9A-Z_]*$", tag_id):
                    raise MKUserError("tag_id", _("Invalid tag group ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                for entry in configured_host_tags():
                    tgid = entry[0]
                    tit  = entry[1]
                    if tgid == tag_id:
                        raise MKUserError("tag_id", _("The tag group ID %s is already used by the tag group '%s'.") % (tag_id, tit))

            title = html.get_unicode_input("title").strip()
            if not title:
                raise MKUserError("title", _("Please specify a title for your host tag group."))

            topic = forms.get_input(vs_topic, "topic")
            # always put at least "/" as prefix to the title, the title
            # will then be split by the first "/' in future
            title = '%s/%s' % (topic, title)

            new_choices = forms.get_input(vs_choices, "choices")
            have_none_tag = False
            for nr, (id, descr, aux) in enumerate(new_choices):
                if id or descr:
                    if not id:
                        id = None
                        if have_none_tag:
                            raise MKUserError("choices_%d_id" % (nr+1), _("Only on tag may be empty."))
                        have_none_tag = True
                    # Make sure tag ID is unique within this group
                    for (n, x) in enumerate(new_choices):
                        if n != nr and x[0] == id:
                            raise MKUserError("choices_id_%d" % (nr+1), _("Tags IDs must be unique. You've used <b>%s</b> twice.") % id)

                if id:
                    # Make sure this ID is not used elsewhere
                    for entry in configured_host_tags():
                        tgid = entry[0]
                        tit  = entry[1]
                        ch   = entry[2]
                        # Do not compare the taggroup with itselfs
                        if tgid != tag_id:
                            for e in ch:
                                # Check primary and secondary tags
                                if id == e[0] or len(e) > 2 and id in e[2]:
                                    raise MKUserError("choices_id_%d" % (nr+1),
                                      _("The tag ID '%s' is already being used by the choice "
                                        "'%s' in the tag group '%s'.") %
                                        ( id, e[1], tit ))

                    # Also check all defined aux tags even if they are not used anywhere
                    for tag, descr in auxtags:
                        if id == tag:
                            raise MKUserError("choices_id_%d" % (nr+1),
                              _("The tag ID '%s' is already being used as auxiliary tag.") % id)

            if len(new_choices) == 0:
                raise MKUserError("id_0", _("Please specify at least one tag."))
            if len(new_choices) == 1 and new_choices[0][0] == None:
                raise MKUserError("id_0", _("Tags with only one choice must have an ID."))

            if new:
                taggroup = tag_id, title, new_choices
                hosttags.append(taggroup)
                save_hosttags(hosttags, auxtags)
                # Make sure, that all tags are active (also manual ones from main.mk)
                config.load_config()
                declare_host_tag_attributes()
                Folder.invalidate_caches()
                Folder.root_folder().rewrite_hosts_files()
                add_change("edit-hosttags", _("Created new host tag group '%s'") % tag_id)
                return "hosttags", _("Created new host tag group '%s'") % title
            else:
                new_hosttags = []
                for entry in hosttags:
                    if entry[0] == tag_id:
                        new_hosttags.append((tag_id, title, new_choices))
                    else:
                        new_hosttags.append(entry)

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
                new_by_title = dict([(e[1], e[0]) for e in new_choices])
                for entry in choices:
                    tag, tit = entry[:2] # optional third element: aux tags
                    if tit in new_by_title:
                        new_tag = new_by_title[tit]
                        if new_tag != tag:
                            operations[tag] = new_tag # might be None

                # Detect removal
                for entry in choices:
                    tag, tit = entry[:2] # optional third element: aux tags
                    if tag != None \
                        and tag not in [ e[0] for e in new_choices ] \
                        and tag not in operations:
                        # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
                        operations[tag] = False

                # Now check, if any folders, hosts or rules are affected
                message = rename_host_tags_after_confirmation(tag_id, operations)
                if message:
                    save_hosttags(new_hosttags, auxtags)
                    config.load_config()
                    declare_host_tag_attributes()
                    Folder.invalidate_caches()
                    Folder.root_folder().rewrite_hosts_files()
                    add_change("edit-hosttags", _("Edited host tag group %s (%s)") % (message, tag_id))
                    return "hosttags", message != True and message or None

        return "hosttags"



    html.begin_form("hosttaggroup", method = 'POST')
    forms.header(_("Edit group") + (tag_id and " %s" % tag_id or ""))

    # Tag ID
    forms.section(_("Internal ID"))
    html.help(_("The internal ID of the tag group is used to store the tag's "
                "value in the host properties. It cannot be changed later."))
    if new:
        html.text_input("tag_id")
        html.set_focus("tag_id")
    else:
        html.write_text(tag_id)

    # Title
    forms.section(_("Title") + "<sup>*</sup>")
    html.help(_("An alias or description of this tag group"))
    html.text_input("title", title, size = 30)

    # The (optional) topic
    forms.section(_("Topic") + "<sup>*</sup>")
    html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                "selections in the GUI more comfortable."))
    forms.input(vs_topic, "topic", topic)

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
    forms.input(vs_choices, "choices", choices)

    # Button and end
    forms.end()
    html.show_localization_hint()

    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

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
            undeclare_host_tag_attribute(tag_id)
        affected_folders, affected_hosts, affected_rulesets = \
        change_host_tags_in_folders(tag_id, operations, mode, Folder.root_folder())
        return _("Modified folders: %d, modified hosts: %d, modified rulesets: %d") % \
            (len(affected_folders), len(affected_hosts), len(affected_rulesets))

    message = ""
    affected_folders, affected_hosts, affected_rulesets = \
        change_host_tags_in_folders(tag_id, operations, "check", Folder.root_folder())

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
                folder_preserving_link([("mode", "edit_ruleset"), ("varname", ruleset.name)]),
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

    rulesets = FolderRulesets(folder)
    rulesets.load()

    for varname, ruleset in rulesets.get_rulesets().items():
        rules_to_delete = set([])
        for folder, rulenr, rule in ruleset.get_rules():
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

class ModeRuleEditor(WatoMode):
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
                folder_preserving_link([("mode", "edit_host"), ("host", self._only_host)]), "host")

        html.context_button(_("Used Rulesets"), folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_ruleset_used", "0"),
            ("search_p_ruleset_used_USE", "on"),
        ]), "usedrulesets")

        html.context_button(_("Ineffective rules"), folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_rule_ineffective", "0"),
            ("search_p_rule_ineffective_USE", "on")]
        ), "rulesets_ineffective")

        html.context_button(_("Deprecated Rulesets"), folder_preserving_link([
            ("mode", "rulesets"),
            ("search_p_ruleset_deprecated", "0"),
            ("search_p_ruleset_deprecated_USE", "on")
        ]), "rulesets_deprecated")

        rule_search_button()


    def page(self):
        if self._only_host:
            html.h3("%s: %s" % (_("Host"), self._only_host))

        search_form(mode="rulesets")

        menu = []
        for groupname in g_rulespecs.get_main_groups():
            url = folder_preserving_link([("mode", "rulesets"), ("group", groupname),
                             ("host", self._only_host)])
            if groupname == "static": # these have moved into their own WATO module
                continue

            rulegroup = get_rulegroup(groupname)
            icon = "rulesets"

            if rulegroup.help:
                help_text = rulegroup.help.split('\n')[0] # Take only first line as button text
            else:
                help_text = None

            menu.append((url, rulegroup.title, icon, "rulesets", help_text))
        render_main_menu(menu)


# TODO: Cleanup all calls using title and remove the argument
def search_form(title=None, mode=None, default_value=""):
    html.begin_form("search", add_transid=False)
    if title:
        html.write_text(title+' ')
    html.text_input("search", size=32, default_value=default_value)
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode, add_var=True)
    html.set_focus("search")
    html.write_text(" ")
    html.button("_do_seach", _("Search"))
    html.end_form()
    html.br()


def get_search_expression():
    search = html.get_unicode_input("search")
    if search != None:
        search = search.strip().lower()
    return search



class ModeRulesets(WatoMode):
    _mode = "rulesets"

    def __init__(self):
        super(ModeRulesets, self).__init__()
        self._from_vars()
        self._set_title_and_help()


    def _rulesets(self):
        return NonStaticChecksRulesets()


    def _from_vars(self):
        self._group_name = html.var("group")

        # Transform group argument to the "rule search arguments"
        # Keeping this for compatibility reasons for the moment
        if self._group_name:
            try:
                group_names = [ g[0] for g in g_rulespecs.get_group_choices(self._mode) ]
                rulegroup_index = group_names.index(html.get_unicode_input("group"))
            except (ValueError, IndexError):
                raise MKUserError(None, _("Unknown ruleset group"))
            html.set_var("search_p_ruleset_group", "%d" % rulegroup_index)
            html.set_var("search_p_ruleset_group_USE", "on")
            html.del_var("group")

        # Transform the search argument to the "rule search" arguments
        if html.has_var("search"):
            html.set_var("search_p_fulltext", html.get_unicode_input("search"))
            html.set_var("search_p_fulltext_USE", "on")
            html.del_var("search")

        self._search_options = ModeRuleSearch().search_options

        self._only_host = html.var("host")


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
            rulegroup = get_rulegroup(self._group_name)
            self._title, self._help = rulegroup.title, rulegroup.help


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

        rule_search_button(self._search_options, mode=self._mode)


    def _only_host_buttons(self):
        html.context_button(_("All Rulesets"), folder_preserving_link([("mode", "ruleeditor"), ("host", self._only_host)]), "back")
        html.context_button(self._only_host,
             folder_preserving_link([("mode", "edit_host"), ("host", self._only_host)]), "host")


    def _regular_buttons(self):
        if self._mode != "static_checks":
            html.context_button(_("All Rulesets"), folder_preserving_link([("mode", "ruleeditor")]), "back")

        if config.user.may("wato.hosts") or config.user.may("wato.seeall"):
            html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "folder")

        if self._group_name == "agents":
            html.context_button(_("Agent Bakery"), folder_preserving_link([("mode", "agents")]), "agents")


    def page(self):
        if not self._only_host:
            Folder.current().show_breadcrump(keepvarnames=True)

        search_form(default_value=self._search_options.get("fulltext", ""))

        if self._help:
            html.help(self._help)

        rulesets = self._rulesets()
        rulesets.load()

        # In case the user has filled in the search form, filter the rulesets by the given query
        if self._search_options:
            rulesets = SearchedRulesets(rulesets, self._search_options)

        html.open_div(class_="rulesets")

        grouped_rulesets = sorted(rulesets.get_grouped(), key=lambda (k, v): get_rulegroup(k).title)

        for main_group_name, sub_groups in grouped_rulesets:
            # Display the main group header only when there are several main groups shown
            if len(grouped_rulesets) > 1:
                html.h3(get_rulegroup(main_group_name).title)
                html.br()

            for sub_group_title, group_rulesets in sub_groups:
                forms.header(sub_group_title or get_rulegroup(main_group_name).title)
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
                        ("back_mode", self._mode),
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



class ModeStaticChecksRulesets(ModeRulesets):
    _mode = "static_checks"

    def _rulesets(self):
        return StaticChecksRulesets()


    def _set_title_and_help(self):
        self._title = _("Manual Checks")
        self._help = _("Here you can create explicit checks that are not being created by the "
                       "automatic service discovery.")



def rule_search_button(search_options=None, mode="rulesets"):
    is_searching = bool(search_options)
    # Don't highlight the button on "standard page" searches. Meaning the page calls
    # that are no searches from the users point of view because he did not fill the
    # search form, but clicked a link in the GUI
    if search_options and (search_options.keys() == ["ruleset_group"]
                           or search_options.keys() == ["ruleset_deprecated"]
                           or search_options.keys() == ["rule_ineffective"]
                           or search_options.keys() == ["ruleset_used"]):
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


class ModeEditRuleset(WatoMode):
    def __init__(self):
        super(ModeEditRuleset, self).__init__()
        self._from_vars()


    def _from_vars(self):
        self._name = html.var("varname")
        self._back_mode = html.var("back_mode", html.var("ruleset_back_mode", "rulesets"))

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        self._item = None

        # TODO: Clean this up. In which case is it used?
        if html.var("check_command"):
            check_command = html.var("check_command")
            checks = check_mk_local_automation("get-check-information")
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
            self._rulespec = g_rulespecs.get(self._name)
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        if not self._item:
            self._item = NO_ITEM
            if html.has_var("item"):
                try:
                    self._item = mk_eval(html.var("item"))
                except:
                    pass

        hostname = html.var("host")
        if hostname and Folder.current().has_host(hostname):
            self._hostname = hostname
        else:
            self._hostname = None


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

            html.context_button(_("Back"), folder_preserving_link([
                ("mode", self._back_mode),
                ("host", self._hostname)
            ] + group_arg), "back")

        if self._hostname:
            html.context_button(_("Services"),
                 folder_preserving_link([("mode", "inventory"),
                                         ("host", self._hostname)]), "services")

            if config.user.may('wato.rulesets'):
                html.context_button(_("Parameters"),
                      folder_preserving_link([("mode", "object_parameters"),
                                              ("host", self._hostname),
                                              ("service", self._item)]), "rulesets")

        if has_agent_bakery():
            agent_bakery_context_button(self._name)


    def action(self):
        rule_folder = Folder.folder(html.var("_folder", html.var("folder")))
        rule_folder.need_permission("write")
        rulesets = FolderRulesets(rule_folder)
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

        elif action == "insert": # Clone a rule
            if not html.check_transaction():
                return None # browser reload
            ruleset.clone_rule(rule)
            rulesets.save()
            return

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
            Folder.current().show_breadcrump(keepvarnames = ["mode", "varname"])

        if not config.wato_hide_varnames:
            display_varname = '%s["%s"]' % tuple(self._name.split(":")) \
                    if ':' in self._name else self._name
            html.div(display_varname, class_="varname")

        rulesets = AllRulesets()
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
                if not Folder.current().is_root() and not folder.is_transitive_parent_of(Folder.current()):
                    skip_this_folder = True
                    continue
                else:
                    skip_this_folder = False

                if last_folder != None:
                    table.end()

                first_in_group = True
                last_folder = folder

                alias_path = folder.alias_path(show_main = False)
                table.begin("rules", title="%s %s" % (_("Rules in folder"), alias_path),
                    css="ruleset", searchable=False, sortable=False, limit=None)
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
               and ("fulltext" in search_options and not ruleset.matches_fulltext_search(search_options)):
                css.append("matches_search")

            table.row(css=" ".join(css) if css else None)

            # Rule matching
            if self._hostname:
                table.cell(_("Ma."))
                if rule.is_disabled():
                    reason = _("This rule is disabled")
                else:
                    reason = rule.matches_host_and_item(Folder.current(), self._hostname, self._item)

                # Handle case where dict is constructed from rules
                if reason == True and ruleset.match_type() == "dict":
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

                elif reason == True and (not alread_matched or ruleset.match_type() == "all"):
                    title = _("This rule matches for the host '%s'") % self._hostname
                    if ruleset.item_type():
                        title += _(" and the %s '%s'.") % (ruleset.item_name(), self._item)
                    else:
                        title += "."
                    img = 'match'
                    alread_matched = True
                elif reason == True:
                    title = _("This rule matches, but is overridden by a previous rule.")
                    img = 'imatch'
                    alread_matched = True
                else:
                    title = _("This rule does not match: %s") % reason
                    img = 'nmatch'
                html.img("images/icon_rule%s.png" % img, align="absmiddle", title=title, class_="icon")

            # Disabling
            table.cell("", css="buttons")
            if rule.is_disabled():
                html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
            else:
                html.empty_icon()

            table.cell(_("Actions"), css="buttons rulebuttons")
            edit_url = folder_preserving_link([
                ("mode", "edit_rule"),
                ("ruleset_back_mode", self._back_mode),
                ("varname", self._name),
                ("rulenr", rulenr),
                ("host", self._hostname),
                ("item", mk_repr(self._item)),
                ("rule_folder", folder.path()),
            ])
            html.icon_button(edit_url, _("Edit this rule"), "edit")
            self._rule_button("insert", _("Insert a copy of this rule in current folder"),
                        folder, rulenr)
            html.element_dragger("tr", base_url=self._action_url("move_to", folder, rulenr))
            self._rule_button("delete", _("Delete this rule"), folder, rulenr)

            self._rule_cells(rule)

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
            img = value and "yes" or "no"
            title = value and _("This rule results in a positive outcome.") \
                          or  _("this rule results in a negative outcome.")
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
                        html.write_text(_("Host does not have tag"))
                    else:
                        html.write_text(_("Host has tag"))
                html.b(alias)
            else:
                if negate:
                    html.write_text(_("Host has <b>not</b> the tag "))
                    html.tt(tag)
                else:
                    html.write_text(_("Host has the tag "))
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
                    host = Host.host(host_spec)
                    if host:
                        host_spec = html.render_a(host_spec, host.edit_url())

                text_list.append(html.render_b(host_spec.strip("!").strip("~")))

        else:
            # Mixed entries
            for host_spec in host_list:
                is_regex = "~" in host_spec
                host_spec = host_spec.strip("!").strip("~")
                if not is_regex:
                    host = Host.host(host_spec)
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
            html.hidden_field("item", mk_repr(self._item))
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

        html.select("rule_folder", Folder.folder_choices(), html.var('folder'))
        html.close_td()
        html.close_tr()
        html.close_table()
        html.write_text("\n")
        html.hidden_field("varname", self._name)
        html.hidden_field("mode", "new_rule")
        html.hidden_field('folder', html.var('folder'))
        html.end_form()



class ModeRuleSearch(WatoMode):
    def __init__(self):
        super(ModeRuleSearch, self).__init__()
        self.back_mode = html.var("back_mode", "rulesets")
        self.search_options = self._from_vars()


    def title(self):
        if self.search_options:
            return _("Refine search")
        else:
            return _("Search rulesets and rules")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), html.makeuri([("mode", self.back_mode)]), "back")


    def page(self):
        html.begin_form("search", method="GET")
        html.hidden_field("mode", self.back_mode, add_var=True)

        valuespec = self._valuespec()
        valuespec.render_input("search", self.search_options, form=True)

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

        return value


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
                    choices = g_rulespecs.get_group_choices(self.back_mode),
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
                ("rule_hosttags", HostTagCondition(
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
            ],
        )



class ModeEditRule(WatoMode):
    _new = False

    def __init__(self):
        super(ModeEditRule, self).__init__()
        self._from_vars()


    def _from_vars(self):
        self._name = html.var("varname")

        if not may_edit_ruleset(self._name):
            raise MKAuthException(_("You are not permitted to access this ruleset."))

        try:
            self._rulespec = g_rulespecs.get(self._name)
        except KeyError:
            raise MKUserError("varname", _("The ruleset \"%s\" does not exist.") % self._name)

        self._back_mode = html.var('back_mode', 'edit_ruleset')

        self._set_folder()

        self._rulesets = FolderRulesets(self._folder)
        self._rulesets.load()
        self._ruleset = self._rulesets.get(self._name)

        self._set_rule()


    def _set_folder(self):
        self._folder = Folder.folder(html.var("rule_folder"))


    def _set_rule(self):
        try:
            rulenr = int(html.var("rulenr"))
            self._rule = self._ruleset.get_rule(self._folder, rulenr)
        except (KeyError, TypeError, ValueError, IndexError):
            raise MKUserError("rulenr", _("You are trying to edit a rule which does "
                                          "not exist anymore."))


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
            backurl = folder_preserving_link(var_list)

        else:
            backurl = folder_preserving_link([
                ('mode', self._back_mode),
                ("host", html.var("host",""))
            ])

        html.context_button(_("Abort"), backurl, "abort")


    def action(self):
        if not html.check_transaction():
            return self._back_mode

        self._update_rule_from_html_vars()

        # Check permissions on folders
        new_rule_folder = Folder.folder(html.var("new_rule_folder"))
        if not self._new:
            self._folder.need_permission("write")
        new_rule_folder.need_permission("write")

        if new_rule_folder == self._folder:
            self._rule.folder = new_rule_folder

            self._save_rule()

        else:
            # Move rule to new folder during editing
            self._ruleset.delete_rule(self._rule)
            self._rulesets.save()

            # Set new folder
            self._rule.folder = new_rule_folder

            self._rulesets = FolderRulesets(new_rule_folder)
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
        rule_options = vs_rule_options().from_html_vars("options")
        vs_rule_options().validate_value(rule_options, "options")
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


    def _save_rule(self):
        # Just editing without moving to other folder
        self._ruleset.edit_rule(self._rule)
        self._rulesets.save()


    def _success_message(self):
        return _("Edited rule in ruleset \"%s\" in folder \"%s\"") % \
                 (self._ruleset.title(), self._folder.alias_path())


    def _get_rule_conditions(self):
        tag_list = get_tag_conditions()

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
        if self._ruleset.help():
            html.div(HTML(self._ruleset.help()), class_="info")

        html.begin_form("rule_editor", method="POST")

        # Additonal rule options
        vs_rule_options().render_input("options", self._rule.rule_options)

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
        html.select("new_rule_folder", Folder.folder_choices(), self._folder.path())
        html.help(_("The rule is only applied to hosts directly in or below this folder."))

        # Host tags
        forms.section(_("Host tags"))
        render_condition_editor(self._rule.tag_specs)
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

        html.br()
        html.br()
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

            if itemtype:
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
        vs_rule_options().set_focus("options")
        html.end_form()


    def _vs_service_conditions(self,):
        return ListOfStrings(
            orientation = "horizontal",
            valuespec = RegExpUnicode(
                size = 30,
                mode = RegExpUnicode.prefix
            ),
        )



class ModeNewRule(ModeEditRule):
    _new = True

    def title(self):
        return _("New rule: %s") % self._rulespec.title


    def _set_folder(self):
        if html.has_var("_new_rule"):
            # Start creating new rule in the choosen folder
            self._folder = Folder.folder(html.var("rule_folder"))

        elif html.has_var("_new_host_rule"):
            # Start creating new rule for a specific host
            self._folder = Folder.current()

        else:
            # Submitting the creation dialog
            self._folder = Folder.folder(html.var("new_rule_folder"))


    def _set_rule(self):
        host_list = ALL_HOSTS
        item_list = [ "" ]

        if html.has_var("_new_host_rule"):
            hostname = html.var("host")
            if hostname:
                host_list = [hostname]

            if self._rulespec.item_type:
                item = mk_eval(html.var("item")) if html.has_var("item") else NO_ITEM
                if item != NO_ITEM:
                    item_list = [ "%s$" % escape_regex_chars(item) ]

        self._rule = Rule.create(self._folder, self._ruleset, host_list, item_list)


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



# Special version of register_rule, dedicated to checks. This is not really
# modular here, but we cannot put this function into the plugins file because
# the order is not defined there.
def register_check_parameters(subgroup, checkgroup, title, valuespec, itemspec,
                               match_type, has_inventory=True, register_static_check=True,
                               deprecated=False):

    if valuespec and isinstance(valuespec, Dictionary) and match_type != "dict":
        raise MKGeneralException("Check parameter definition for %s has type Dictionary, but match_type %s" %
                                 (checkgroup, match_type))

    # Register rule for discovered checks
    if valuespec and has_inventory: # would be useless rule if check has no parameters
        itemenum = None
        if itemspec:
            itemtype = "item"
            itemname = itemspec.title()
            itemhelp = itemspec.help()
            if isinstance(itemspec, DropdownChoice) or isinstance(itemspec, OptionalDropdownChoice):
                itemenum = itemspec._choices
        else:
            itemtype = None
            itemname = None
            itemhelp = None

        register_rule(
            "checkparams/" + subgroup,
            varname = "checkgroup_parameters:%s" % checkgroup,
            title = title,
            valuespec = valuespec,
            itemspec = itemspec,
            itemtype = itemtype,
            itemname = itemname,
            itemhelp = itemhelp,
            itemenum = itemenum,
            match = match_type,
            deprecated = deprecated)

    if register_static_check:
        # Register rule for static checks
        elements = [
            CheckTypeGroupSelection(
                checkgroup,
                title = _("Checktype"),
                help = _("Please choose the check plugin")) ]
        if itemspec:
            elements.append(itemspec)
        else:
            # In case of static checks without check-item, add the fixed
            # valuespec to add "None" as second element in the tuple
            elements.append(FixedValue(
                None,
                totext = '',
            ))
        if not valuespec:
            valuespec =\
                FixedValue(None,
                    help = _("This check has no parameters."),
                    totext = "")
        if not valuespec.title():
            valuespec._title = _("Parameters")
        elements.append(valuespec)

        register_rule(
            "static/" + subgroup,
            "static_checks:%s" % checkgroup,
            title = title,
            valuespec = Tuple(
                title = valuespec.title(),
                elements = elements,
            ),
            itemspec = itemspec,
            match = "all",
            deprecated = deprecated)






# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(**args):
    dif = args.get("default_difference", (2.0, 4.0))
    unitname = args.get("unit", "")
    if unitname:
        unitname += " "

    return Dictionary(
        title = _("Predictive Levels"),
        optional_keys = [ "weight", "levels_upper", "levels_upper_min", "levels_lower", "levels_lower_max" ],
        default_keys = [ "levels_upper" ],
        columns = 1,
        headers = "sup",
        elements = [
             ( "period",
                DropdownChoice(
                    title = _("Base prediction on"),
                    choices = [
                        ( "wday",   _("Day of the week (1-7, 1 is Monday)") ),
                        ( "day",    _("Day of the month (1-31)") ),
                        ( "hour",   _("Hour of the day (0-23)") ),
                        ( "minute", _("Minute of the hour (0-59)") ),
                    ]
             )),
             ( "horizon",
               Integer(
                   title = _("Time horizon"),
                   unit = _("days"),
                   minvalue = 1,
                   default_value = 90,
             )),
             # ( "weight",
             #   Percentage(
             #       title = _("Raise weight of recent time"),
             #       label = _("by"),
             #       default_value = 0,
             # )),
             ( "levels_upper",
               CascadingDropdown(
                   title = _("Dynamic levels - upper bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[0]),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[1]),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% above predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% above predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation above the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation above the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
             ( "levels_upper_min",
                Tuple(
                    title = _("Limit for upper bound dynamic levels"),
                    help = _("Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                             "the will never be set below the following limits. This avoids false alarms "
                             "during times where the predicted levels would be very low."),
                    elements = [
                        Float(title = _("Warning level is at least"), unit = unitname),
                        Float(title = _("Critical level is at least"), unit = unitname),
                    ]
              )),
             ( "levels_lower",
               CascadingDropdown(
                   title = _("Dynamic levels - lower bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("below predicted value"), default_value = 2.0),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("below predicted value"), default_value = 4.0),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% below predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% below predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation below the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation below the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
        ]
    )


# To be used as ValueSpec for levels on numeric values, with
# prediction
def match_levels_alternative(v):
    if type(v) == dict:
        return 2
    elif type(v) == tuple and v != (None, None):
        return 1
    else:
        return 0

def Levels(**kwargs):
    help = kwargs.get("help")
    unit = kwargs.get("unit")
    title = kwargs.get("title")
    default_levels = kwargs.get("default_levels", (0.0, 0.0))
    default_difference = kwargs.get("default_difference", (0,0))
    if "default_value" in kwargs:
        default_value = kwargs["default_value"]
    else:
        default_value = default_levels and default_levels or None

    return Alternative(
          title = title,
          help = help,
          show_titles = False,
          style = "dropdown",
          elements = [
              FixedValue(
                  None,
                  title = _("No Levels"),
                  totext = _("Do not impose levels, always be OK"),
              ),
              Tuple(
                  title = _("Fixed Levels"),
                  elements = [
                      Float(unit = unit, title = _("Warning at"), default_value = default_levels[0], allow_int = True),
                      Float(unit = unit, title = _("Critical at"), default_value = default_levels[1], allow_int = True),
                  ],
              ),
              PredictiveLevels(
                  default_difference = default_difference,
              ),
          ],
          match = match_levels_alternative,
          default_value = default_value,
    )

# When changing this keep it in sync with
# a) check_mk_base.py: do_hostname_translation()
# b) wato.py:          do_hostname_translation()
# FIXME TODO: Move the common do_hostname_translation() in a central Check_MK module
def HostnameTranslation(**kwargs):
    help = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title = title,
        help = help,
        elements = [
            ( "case",
              DropdownChoice(
                  title = _("Case translation"),
                  choices = [
                       ( None,    _("Do not convert case") ),
                       ( "upper", _("Convert hostnames to upper case") ),
                       ( "lower", _("Convert hostnames to lower case") ),
                  ]
            )),
            ( "drop_domain",
              FixedValue(
                  True,
                  title = _("Convert FQHN"),
                  totext = _("Drop domain part (<tt>host123.foobar.de</tt> &#8594; <tt>host123</tt>)"),
            )),
            ( "regex",
                Transform(
                    ListOf(
                        Tuple(
                            orientation = "horizontal",
                            elements    =  [
                                RegExpUnicode(
                                    title          = _("Regular expression"),
                                    help           = _("Must contain at least one subgroup <tt>(...)</tt>"),
                                    mingroups      = 0,
                                    maxgroups      = 9,
                                    size           = 30,
                                    allow_empty    = False,
                                    mode           = RegExp.prefix,
                                    case_sensitive = False,
                                ),
                                TextUnicode(
                                    title       = _("Replacement"),
                                    help        = _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"),
                                    size        = 30,
                                    allow_empty = False,
                                )
                            ],
                        ),
                        title     = _("Multiple regular expressions"),
                        help      = _("You can add any number of expressions here which are executed succesively until the first match. "
                                      "Please specify a regular expression in the first field. This expression should at "
                                      "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                                      "In the second field you specify the translated host name and can refer to the first matched "
                                      "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                                      ""),
                        add_label = _("Add expression"),
                        movable   = False,
                    ),
                    forth = lambda x: type(x) == tuple and [x] or x,
                )
            ),
            ( "mapping",
              ListOf(
                  Tuple(
                      orientation = "horizontal",
                      elements =  [
                          TextUnicode(
                               title = _("Original hostname"),
                               size = 30,
                               allow_empty = False,
                               attrencode = True,
                          ),
                          TextUnicode(
                               title = _("Translated hostname"),
                               size = 30,
                               allow_empty = False,
                               attrencode = True,
                          ),
                      ],
                  ),
                  title = _("Explicit host name mapping"),
                  help = _("If case conversion and regular expression do not work for all cases then you can "
                           "specify explicity pairs of origin host name  and translated host name here. This "
                           "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                           "expression conversion (if that matches)."),
                  add_label = _("Add new mapping"),
                  movable = False,
            )),
        ])


# When changing this keep it in sync with
# a) check_mk_base.py: do_hostname_translation()
# b) wato.py:          do_hostname_translation()
# FIXME TODO: Move the common do_hostname_translation() in a central Check_MK module
def do_hostname_translation(translation, hostname):
    # 1. Case conversion
    caseconf = translation.get("case")
    if caseconf == "upper":
        hostname = hostname.upper()
    elif caseconf == "lower":
        hostname = hostname.lower()

    # 2. Drop domain part (not applied to IP addresses!)
    if translation.get("drop_domain") and not hostname[0].isdigit():
        hostname = hostname.split(".", 1)[0]

    # 3. Multiple regular expression conversion
    if type(translation.get("regex")) == tuple:
        translations = [translation.get("regex")]
    else:
        translations = translation.get("regex", [])

    for expr, subst in translations:
        if not expr.endswith('$'):
            expr += '$'
        rcomp = regex(expr)
        # re.RegexObject.sub() by hand to handle non-existing references
        mo = rcomp.match(hostname)
        if mo:
            hostname = subst
            for nr, text in enumerate(mo.groups("")):
                hostname = hostname.replace("\\%d" % (nr+1), text)
            break

    # 4. Explicit mapping
    for from_host, to_host in translation.get("mapping", []):
        if from_host == hostname:
            hostname = to_host
            break

    return hostname


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
    languages = [ l for l in i18n.get_languages() if not config.hide_language(l[0]) ]
    if languages:
        active = 'language' in user
        forms.section(_("Language"), checkbox = ('_set_lang', active, 'language'))
        default_label = _('Default: %s') % (i18n.get_language_alias(config.default_language) or _('English'))
        html.div(default_label, class_="inherited", id_="attr_default_language", style= "display: none" if active else "")
        html.open_div(id_="attr_entry_language", style="display: none" if not active else "")

        language = user.get('language') if user.get('language') != None else ''
        html.select("language", languages, language)
        html.close_div()
        html.help(_('Configure the default language '
                    'to be used by the user in the user interface here. If you do not check '
                    'the checkbox, then the system default will be used.<br><br>'
                    'Note: currently Multisite is internationalized '
                    'but comes without any actual localisations (translations). If you want to '
                    'create you own translation, you find <a href="%(url)s">documentation online</a>.') %
                    { "url" : "https://mathias-kettner.com/checkmk_multisite_i18n.html"} )

def user_profile_async_replication_page():
    html.header(_('Replicate new User Profile'),
                javascripts = ['wato'],
                stylesheets = ['check_mk', 'pages', 'wato', 'status'])

    html.begin_context_buttons()
    html.context_button(_('User Profile'), 'user_profile.py', 'back')
    html.end_context_buttons()

    user_profile_async_replication_dialog()

    html.footer()


def user_profile_async_replication_dialog():
    repstatus = load_replication_status()

    html.message(_('In order to activate your changes available on all remote sites, your user profile needs '
                   'to be replicated to the remote sites. This is done on this page now. Each site '
                   'is being represented by a single image which is first shown gray and then fills '
                   'to green during synchronisation.'))

    html.h3(_('Replication States'))
    html.open_div(id_="profile_repl")
    num_replsites = 0
    for site_id in get_login_sites():
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
            changes_manager = ActivateChanges()
            changes_manager.load()
            estimated_duration = changes_manager.get_activation_time(site_id, ACTIVATION_TIME_PROFILE_SYNC, 2.0)
            html.javascript('wato_do_profile_replication(\'%s\', %d, \'%s\');' %
                      (site_id, int(estimated_duration * 1000.0), _('Replication in progress')))
            num_replsites += 1
        else:
            add_profile_replication_change(site_id, status_txt)
        html.span(site.get('alias', site_id))

        html.close_div()

    html.javascript('var g_num_replsites = %d;\n' % num_replsites)

    html.close_div()


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
                        i18n.set_language_cookie(language)

                    else:
                        # Remove the customized language
                        if 'language' in users[config.user.id]:
                            del users[config.user.id]['language']
                        config.user.unset_attribute("language")

                    # load the new language
                    i18n.localize(config.user.language())
                    multisite_modules.load_all_plugins()

                    user = users.get(config.user.id)
                    if config.user.may('general.edit_notifications') and user.get("notifications_enabled"):
                        value = forms.get_input(vs_notification_method, "notification_method")
                        users[config.user.id]["notification_method"] = value

                    # Custom attributes
                    if config.user.may('general.edit_user_attributes'):
                        for name, attr in userdb.get_user_attributes():
                            if attr['user_editable']:
                                if not attr.get("permission") or config.user.may(attr["permission"]):
                                    vs = attr['valuespec']
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

                    verify_password_policy(password)
                    users[config.user.id]['password'] = userdb.encrypt_password(password)
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
            if get_login_sites():
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
        rulebased_notifications = load_configuration_settings().get("enable_rulebased_notifications")
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
            html.http_redirect(html.var('_origtarget', 'index.py'))
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
            vs_notification_method.render_input("notification_method", user.get("notification_method"))

        if config.user.may('general.edit_user_attributes'):
            for name, attr in userdb.get_user_attributes():
                if attr['user_editable']:
                    vs = attr['valuespec']
                    forms.section(_u(vs.title()))
                    value = user.get(name, vs.default_value())
                    if not attr.get("permission") or config.user.may(attr["permission"]):
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

def page_download_agent_output():
    config.user.need_permission("wato.download_agent_output")

    host_name = html.var("host")
    if not host_name:
        raise MKGeneralException(_("The host is missing."))

    ty = html.var("type")
    if ty not in [ "walk", "agent" ]:
        raise MKGeneralException(_("Invalid type specified."))

    init_wato_datastructures(with_wato_lock=True)

    host = Folder.current().host(host_name)
    if not host:
        raise MKGeneralException(_("Invalid host."))
    host.need_permission("read")

    success, output, agent_data = check_mk_automation(host.site_id(), "get-agent-output",
                                                      [host_name, ty])

    if success:
        html.set_output_format("text")
        html.set_http_header("Content-Disposition", "Attachment; filename=" + host_name)
        html.write(agent_data)
    else:
        html.header(_("Failed to fetch agent data"), stylesheets=["status", "pages"])
        html.p(_("There was a problem fetching data from the host."))
        if output:
            html.show_error(html.attrencode(output))
        html.pre(agent_data)
        html.footer()

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
def create_sample_config():
    if os.path.exists(multisite_dir + "hosttags.mk") \
        or os.path.exists(wato_root_dir + "rules.mk") \
        or os.path.exists(wato_root_dir + "groups.mk") \
        or os.path.exists(wato_root_dir + "notifications.mk") \
        or os.path.exists(wato_root_dir + "global.mk"):
        return

    # Just in case. If any of the following functions try to write Git messages
    if config.wato_use_git:
        prepare_git_commit()

    # Global configuration settings
    save_global_settings(
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
                "etherbox",
                "liebert_bat_temp",
                "nvidia.temp",
                "ups_bat_temp",
                "innovaphone_temp",
                "enterasys_temp",
                "mknotifyd",
                "mknotifyd.connection",
                "postfix_mailq",
                "nullmailer_mailq",
                "barracuda_mailqueues",
                "qmail_stats",
            ],
            "inventory_check_interval": 120,
            "enable_rulebased_notifications": True,
        }
    )


    # A contact group for all hosts and services
    groups = {
        "contact" : { 'all' : {'alias': u'Everything'} },
    }
    save_group_information(groups)

    # Basic setting of host tags
    wato_host_tags = \
    [('agent',
      u'Agent type',
      [('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
       ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
       ('snmp-v1', u'Legacy SNMP device (using V1)', ['snmp']),
       ('snmp-tcp', u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
       ('ping', u'No Agent', [])]),
     ('criticality',
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

    wato_aux_tags = \
    [('snmp', u'monitor via SNMP'),
     ('tcp', u'monitor via Check_MK Agent')]

    save_hosttags(wato_host_tags, wato_aux_tags)

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
        'extra_service_conf:check_interval': [
          ( 1440, [], ALL_HOSTS, [ "Check_MK HW/SW Inventory$" ], {'description': u'Restrict HW/SW-Inventory to once a day'} ),
        ],
    }

    rulesets = FolderRulesets(Folder.root_folder())
    rulesets.from_config(Folder.root_folder(), ruleset_config)
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
    save_notification_rules(notification_rules)

    if "create_cee_sample_config" in globals():
        create_cee_sample_config()

    # Make sure the host tag attributes are immediately declared!
    config.wato_host_tags = wato_host_tags
    config.wato_aux_tags = wato_aux_tags

    # Initial baking of agents (when bakery is available)
    if has_agent_bakery():
        try:
            bake_agents()
        except:
            pass # silently ignore building errors here

    # This is not really the correct place for such kind of action, but the best place we could
    # find to execute it only for new created sites.
    import werks
    werks.acknowledge_all_werks(check_permission=False)

    save_mkeventd_sample_config()

    userdb.create_cmk_automation_user()


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

def mode_pattern_editor(phase):
    import logwatch

    # 1. Variablen auslesen
    hostname   = html.var('host', '')
    item       = html.var('file', '')
    match_txt  = html.var('match', '')
    master_url = html.var('master_url', '')

    host = Folder.current().host(hostname)

    if phase == "title":
        if not hostname and not item:
            return _("Logfile Pattern Analyzer")
        elif not hostname:
            return _("Logfile Patterns of Logfile %s on all Hosts") % (item)
        elif not item:
            return _("Logfile Patterns of Host %s") % (hostname)
        else:
            return _("Logfile Patterns of Logfile %s on Host %s") % (item, hostname)

    elif phase == "buttons":
        home_button()
        if host:
            if item:
                title = _("Show Logfile")
            else:
                title = _("Host Logfiles")

            html.context_button(title, html.makeuri_contextless([("host", hostname), ("file", item)], filename="logwatch.py"), 'logwatch')

        html.context_button(_('Edit Logfile Rules'), folder_preserving_link([
                ('mode', 'edit_ruleset'),
                ('varname', 'logwatch_rules')
            ]),
            'edit'
        )

        return

    if phase == "action":
        return

    html.help(_('On this page you can test the defined logfile patterns against a custom text, '
                'for example a line from a logfile. Using this dialog it is possible to analyze '
                'and debug your whole set of logfile patterns.'))

    # Render the tryout form
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

    # Bail out if the given hostname does not exist
    if hostname and not host:
        html.add_user_error('host', _('The given host does not exist.'))
        html.show_user_errors()
        return

    collection = SingleRulesetRecursively("logwatch_rules")
    collection.load()
    ruleset = collection.get("logwatch_rules")

    html.h3(_('Logfile Patterns'))
    if ruleset.is_empty():
        html.open_div(class_="info")
        html.write_text('There are no logfile patterns defined. You may create '
                        'logfile patterns using the <a href="%s">Rule Editor</a>.' %
                         folder_preserving_link([
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
        if hostname:
            # If hostname (and maybe filename) try match it
            reason = rule.matches_host_and_item(Folder.current(), hostname, item)
        elif item:
            # If only a filename is given
            reason = rule.matches_item()
        else:
            # If no host/file given match all rules
            reason = True

        match_img = ''
        if reason == True:
            # Applies to the given host/service
            reason_class = 'reason'
            # match_title/match_img are set below per pattern
        else:
            # not matching
            reason_class = 'noreason'
            match_img   = 'nmatch'
            match_title = reason

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
            if reason == True:
                matched = re.search(pattern, match_txt)
                if matched:

                    # Prepare highlighted search txt
                    match_start = matched.start()
                    match_end   = matched.end()
                    disp_match_txt = html.attrencode(match_txt[:match_start]) \
                                     + '<span class=match>' + html.attrencode(match_txt[match_start:match_end]) + '</span>' \
                                     + html.attrencode(match_txt[match_end:])

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

            table.row(css=reason_class)
            table.cell(_('Match'))
            html.icon(match_title, "rule%s" % match_img)

            cls = ''
            if match_class == 'match first':
                cls = 'svcstate state%d' % logwatch.level_state(state)
            table.cell(_('State'), logwatch.level_name(state), css=cls)
            table.cell(_('Pattern'), html.render_tt(html.attrencode(pattern)))
            table.cell(_('Comment'), html.attrencode(comment))
            table.cell(_('Matched line'), disp_match_txt)

        table.row(fixed=True)
        table.cell(colspan=5)
        edit_url = folder_preserving_link([
            ("mode", "edit_rule"),
            ("varname", "logwatch_rules"),
            ("rulenr", rulenr),
            ("host", hostname),
            ("item", mk_repr(item)),
            ("rule_folder", folder.path())])
        html.icon_button(edit_url, _("Edit this rule"), "edit")

        table.end()
        html.end_foldable_container()


#.
#   .--Custom-Attributes---------------------------------------------------.
#   |   ____          _                          _   _   _                 |
#   |  / ___|   _ ___| |_ ___  _ __ ___         / \ | |_| |_ _ __ ___      |
#   | | |  | | | / __| __/ _ \| '_ ` _ \ _____ / _ \| __| __| '__/ __|     |
#   | | |__| |_| \__ \ || (_) | | | | | |_____/ ___ \ |_| |_| |  \__ \_    |
#   |  \____\__,_|___/\__\___/|_| |_| |_|    /_/   \_\__|\__|_|  |___(_)   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mange custom attributes of users (in future hosts etc.)              |
#   '----------------------------------------------------------------------'

custom_attr_types = [
    ('TextAscii', _('Simple Text')),
]

def save_custom_attrs(attrs):
    output = wato_fileheader()
    for what in [ "user", "host" ]:
        if what in attrs and len(attrs[what]) > 0:
            output += "if type(wato_%s_attrs) != list:\n    wato_%s_attrs = []\n" % (what, what)
            output += "wato_%s_attrs += %s\n\n" % (what, pprint.pformat(attrs[what]))

    make_nagios_directory(multisite_dir)
    store.save_file(multisite_dir + "custom_attrs.mk", output)


def mode_edit_custom_attr(phase, what):
    name = html.var("edit") # missing -> new custom attr
    new = name == None

    if phase == "title":
        if new:
            if what == "user":
                return _("Create User Attribute")
            else:
                return _("Create Host Attribute")
        else:
            if what == "user":
                return _("Edit User Attribute")
            else:
                return _("Edit Host Attribute")

    elif phase == "buttons":
        html.context_button(_("Back"), folder_preserving_link([("mode", "%s_attrs" % what)]), "back")
        return

    all_attrs = userdb.load_custom_attrs()
    attrs = all_attrs.setdefault(what, [])

    if not new:
        attr = [ a for a in attrs if a['name'] == name ]
        if not attr:
            raise MKUserError(None, _('The attribute does not exist.'))
        else:
            attr = attr[0]
    else:
        attr = {}

    if phase == "action":
        if html.check_transaction():
            title = html.get_unicode_input("title").strip()
            if not title:
                raise MKUserError("title", _("Please specify a title."))
            for this_attr in attrs:
                if title == this_attr['title'] and name != this_attr['name']:
                    raise MKUserError("alias", _("This alias is already used by the attribute %s.") % this_attr['name'])

            topic = html.var('topic', '').strip()
            help  = html.get_unicode_input('help').strip()
            if what == "user":
                user_editable = html.get_checkbox('user_editable')
            show_in_table = html.get_checkbox('show_in_table')
            add_custom_macro = html.get_checkbox('add_custom_macro')

            if new:
                name = html.var("name", '').strip()
                if not name:
                    raise MKUserError("name", _("Please specify a name for the new attribute."))
                if ' ' in name:
                    raise MKUserError("name", _("Sorry, spaces are not allowed in attribute names."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid attribute name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if [ a for a in attrs if a['name'] == name ]:
                    raise MKUserError("name", _("Sorry, there is already an attribute with that name."))

                ty = html.var('type', '').strip()
                if ty not in [ t[0] for t in custom_attr_types ]:
                    raise MKUserError('type', _('The choosen attribute type is invalid.'))

                attr = {
                    'name' : name,
                    'type' : ty,
                }
                attrs.append(attr)

                add_change("edit-%sattr" % what, _("Create new %s attribute %s") % (what, name))
            else:
                add_change("edit-%sattr" % what, _("Modified %s attribute %s") % (what, name))
            attr.update({
                'title'            : title,
                'topic'            : topic,
                'help'             : help,
                'show_in_table'    : show_in_table,
                'add_custom_macro' : add_custom_macro,
            })

            if what == "user":
                attr['user_editable'] = user_editable

            save_changed_custom_attrs(all_attrs, what)

        return what + "_attrs"

    html.begin_form("attr")
    forms.header(_("Properties"))
    forms.section(_("Name"), simple = not new)
    html.help(_("The name of the attribute is used as an internal key. It cannot be "
                 "changed later."))
    if new:
        html.text_input("name", attr.get('name'))
        html.set_focus("name")
    else:
        html.write_text(name)
        html.set_focus("title")

    forms.section(_("Title") + "<sup>*</sup>")
    html.help(_("The title is used to label this attribute."))
    html.text_input("title", attr.get('title'))

    forms.section(_('Topic'))
    html.help(_('The attribute is added to this section in the edit dialog.'))

    if what == "user":
        topics = [
            ('ident',    _('Identity')),
            ('security', _('Security')),
            ('notify',   _('Notifications')),
            ('personal', _('Personal Settings')),
        ]
        default_topic = "personal"
    else:
        topics = list(set([ (a[1], a[1]) for a in all_host_attributes() if a[1] != None ]))
        topics.insert(0, (_("Custom attributes"), _("Custom attributes")))
        default_topic = _("Custom attributes")

    html.select('topic', topics, attr.get('topic', 'personal'))

    forms.section(_('Help Text') + "<sup>*</sup>")
    html.help(_('You might want to add some helpful description for the attribute.'))
    html.text_area('help', attr.get('help', ''))

    forms.section(_('Data type'))
    html.help(_('The type of information to be stored in this attribute.'))
    if new:
        html.select('type', custom_attr_types, attr.get('type'))
    else:
        html.write(dict(custom_attr_types)[attr.get('type')])

    if what == "user":
        forms.section(_('Editable by Users'))
        html.help(_('It is possible to let users edit their custom attributes.'))
        html.checkbox('user_editable', attr.get('user_editable', True),
                      label = _("Users can change this attribute in their personal settings"))

    forms.section(_('Show in Table'))
    html.help(_('This attribute is only visibile on the detail pages by default, but '
                'you can also make it visible in the overview tables.'))
    html.checkbox('show_in_table', attr.get('show_in_table', False),
                  label = _("Show the setting of the attribute in the list table"))

    forms.section(_('Add as custom macro'))
    if what == "user":
        html.help(_('The attribute can be added to the contact definiton in order '
                    'to use it for notifications.'))
        label = _("Make this variable available in notifications")
    else:
        html.help(_("The attribute can be added to the host definition in order to "
                    "use it as monitoring macro in different places, for example "
                    "as macro in check commands or notifications."))
        label = _("Make this variable available as monitoring macro, "
                  "e.g. in check commands or in notifications.")

    html.checkbox('add_custom_macro', attr.get('add_custom_macro', False),
                  label=label)

    forms.end()
    html.show_localization_hint()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def mode_custom_attrs(phase, what):
    if what == "user":
        title = _("Custom User Attributes")
    else:
        title = _("Custom Host Attributes")

    if phase == "title":
        return title

    elif phase == "buttons":
        if what == "user":
            html.context_button(_("Users"), folder_preserving_link([("mode", "users")]), "back")
        else:
            html.context_button(_("Folder"), folder_preserving_link([("mode", "folder")]), "back")
        html.context_button(_("New Attribute"), folder_preserving_link([("mode", "edit_%s_attr" % what)]), "new")
        return

    all_attrs = userdb.load_custom_attrs()
    attrs = all_attrs.get(what, {})

    if phase == "action":
        if html.var('_delete'):
            delname = html.var("_delete")

            # FIXME: Find usages and warn
            #if usages:
            #    message = "<b>%s</b><br>%s:<ul>" % \
            #                (_("You cannot delete this %s attribute.") % what,
            #                 _("It is still in use by"))
            #    for title, link in usages:
            #        message += '<li><a href="%s">%s</a></li>\n' % (link, title)
            #    message += "</ul>"
            #    raise MKUserError(None, message)

            confirm_txt = _('Do you really want to delete the custom attribute "%s"?') % (delname)

            c = wato_confirm(_("Confirm deletion of attribute \"%s\"") % delname, confirm_txt)
            if c:
                for index, attr in enumerate(attrs):
                    if attr['name'] == delname:
                        attrs.pop(index)
                save_changed_custom_attrs(all_attrs, what)
                add_change("edit-%sattrs" % what, _("Deleted attribute %s") % (delname))
            elif c == False:
                return ""

        return None

    if not attrs:
        html.div(_("No custom attributes are defined yet."), class_="info")
        return

    table.begin(what + "attrs")
    for attr in sorted(attrs, key = lambda x: x['title']):
        table.row()

        table.cell(_("Actions"), css="buttons")
        edit_url = folder_preserving_link([("mode", "edit_%s_attr" % what), ("edit", attr['name'])])
        delete_url = html.makeactionuri([("_delete", attr['name'])])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"),  attr['name'])
        table.cell(_("Title"), attr['title'])
        table.cell(_("Type"),  dict(custom_attr_types)[attr['type']])

    table.end()


def save_changed_custom_attrs(all_attrs, what):
    save_custom_attrs(all_attrs)
    if what == "user":
        userdb.declare_custom_user_attrs()
        userdb.rewrite_users()
    else:
        declare_custom_host_attrs()
        Folder.invalidate_caches()
        Folder.root_folder().rewrite_hosts_files()


def declare_custom_host_attrs():
    # First remove all previously registered custom host attributes
    for attr_name in all_host_attribute_names():
        if attr_name not in builtin_host_attribute_names and not\
           attr_name.startswith("tag_"):
            undeclare_host_attribute(attr_name)

    # now declare the custom attributes
    all_attrs = userdb.load_custom_attrs()
    attrs = all_attrs.setdefault('host', [])
    for attr in attrs:
        vs = globals()[attr['type']](title = attr['title'], help = attr['help'])

        if attr['add_custom_macro']:
            a = NagiosValueSpecAttribute(attr["name"], "_" + attr["name"], vs)
        else:
            a = ValueSpecAttribute(attr["name"], vs)

        declare_host_attribute(a,
            show_in_table = attr['show_in_table'],
            topic = attr['topic'],
        )

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

# topic, has_second_level, title, description
def man_page_catalog_topics():
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


def mode_check_plugins(phase):
    search = get_search_expression()
    topic  = html.var("topic")
    if topic and not search:
        path = tuple(topic.split("/")) # e.g. [ "hw", "network" ]
        if not re.match("^[a-zA-Z0-9_./]+$", topic):
            raise Exception("Invalid topic")
    else:
        path = tuple()

    for comp in path:
        ID().validate_value(comp, None) # Beware against code injection!

    manpages = get_check_catalog(path)
    titles = man_pages.man_page_catalog_titles()

    has_second_level = None
    if topic and not search:
        for t, has_second_level, title, helptext in man_page_catalog_topics():
            if t == path[0]:
                topic_title = title
                break
        if len(path) == 2:
            topic_title = titles.get(path[1], path[1])

    if phase == "title":
        if topic and not search:
            heading = "%s - %s" % ( _("Catalog of Check Plugins"), topic_title )
        elif search:
            heading = "%s: %s" % ( _("Check plugins matching"), html.attrencode(search) )
        else:
            heading = _("Catalog of Check Plugins")
        return heading

    elif phase == "buttons":
        global_buttons()
        if topic:
            if len(path) == 2:
                back_url = html.makeuri([("topic", path[0])])
            else:
                back_url = html.makeuri([("topic", "")])
            html.context_button(_("Back"), back_url, "back")
        return

    elif phase == "action":
        return

    html.help(_("This catalog of check plugins gives you a complete listing of all plugins "
                "that are shipped with your Check_MK installation. It also allows you to "
                "access the rule sets for configuring the parameters of the checks and to "
                "manually create services in case you cannot or do not want to rely on the "
                "automatic service discovery."))

    search_form( "%s: " % _("Search for check plugins"), "check_plugins" )

    # The maxium depth of the catalog paths is 3. The top level is being rendered
    # like the WATO main menu. The second and third level are being rendered like
    # the global settings.

    if topic and not search:
        render_manpage_topic( manpages, titles, has_second_level, path, topic_title )

    elif search:
        for path, manpages in get_manpages_after_search( manpages, search ):
            render_manpage_list( manpages, titles, path, titles.get( path, path ) )

    else:
        menu_items = []
        for topic, has_second_level, title, helptext in man_page_catalog_topics():
            menu_items.append((
                html.makeuri([("topic", topic)]), title, "plugins_" + topic, None, helptext))
        render_main_menu(menu_items)


def get_manpages_after_search( manpages, search ):
    this_search = search
    collection  = {}

    # searches in {"name" : "asd", "title" : "das", ...}
    def get_matched_entry( entry ):
        if type( entry ) == dict:
            name = entry.get( "name", "" )
            if type( name ) == str:
                name = name.decode( "utf8" )

            title = entry.get( "title", "" )
            if type( title ) == str:
                title = title.decode( "utf8" )
            if this_search in name.lower() or this_search in title.lower():
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
                collection[key] += these_matches

        elif type(entries) == dict:
            for key, subentries in entries.items():
                check_entries( key, subentries )

    for key, entries in manpages.items():
        check_entries( key, entries )

    return collection.items()


def get_check_catalog(args):
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
    if len(args) > 0:
        only_path = tuple(args)
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


def render_manpage_topic(manpages, titles, has_second_level, path, topic_title):
    if type(manpages) == list:
        render_manpage_list(manpages, titles, path[-1], topic_title)
    else:
        # For some topics we render a second level in the same optic as the first level
        if len(path) == 1 and has_second_level:
            menu_items = []
            for path_comp, subnode in manpages.items():
                url = html.makeuri([("topic", "%s/%s" % (path[0], path_comp))])
                title = titles.get(path_comp, path_comp)
                helptext = get_check_plugin_stats(subnode)
                menu_items.append((url, title, "check_plugins", None, helptext))
            render_main_menu(menu_items)

        # For the others we directly display the tables
        else:
            entries = []
            for path_comp, subnode in manpages.items():
                title = titles.get(path_comp, path_comp)
                entries.append((title, subnode, path_comp))
            entries.sort(cmp = lambda a,b: cmp(a[0].lower(), b[0].lower()))
            for title, subnode, path_comp in entries:
                render_manpage_list(subnode, titles, path_comp, title)


def get_check_plugin_stats(subnode):
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


def render_manpage_list(manpage_list, titles, path_comp, heading):
    def translate(t):
        return titles.get(t, t)

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


def mode_check_manpage(phase):
    check_type = html.var("check_type")

    if phase == "title":
        # TODO: There is one check "sap.value-groups" which will be renamed to "sap.value_groups".
        # As long as the old one is available, allow a minus here.
        if not re.match("^[-a-zA-Z0-9_.]+$", check_type):
            raise Exception("Invalid check type")

        # TODO: remove call of automation and then the automation. This can be done once the check_info
        # data is also available in the "cmk." module because the get-check-manpage automation not only
        # fetches the man page. It also contains info from check_info. What a hack.
        manpage = check_mk_local_automation("get-check-manpage", [ check_type ])
        if manpage == None:
            raise MKUserError(None, _("There is no manpage for this check."))

        html.set_cache("manpage", manpage)
        return _("Check plugin manual page") + " - " + manpage["header"]["title"]

    elif phase == "buttons":
        global_buttons()
        manpage = html.get_cached("manpage")
        path = manpage["header"]["catalog"]
        if html.var("back"):
            back_url = html.var("back")
            html.context_button(_("Back"), back_url, "back")
        html.context_button(_("All Check Plugins"), html.makeuri_contextless([("mode", "check_plugins")]), "check_plugins")
        if check_type.startswith("check_"):
            command = "check_mk_active-" + check_type[6:]
        else:
            command = "check_mk-" + check_type
        url = html.makeuri_contextless([("view_name", "searchsvc"), ("check_command", command), ("filled_in", "filter")], filename="view.py")
        html.context_button(_("Find usage"), url, "status")
        return

    elif phase == "action":
        return
    manpage = html.get_cached("manpage")


    # We could simply detect on how many hosts and services this plugin
    # is currently in use (Livestatus query) and display this information
    # together with a link for searching. Then we can remove the dump context
    # button, that will always be shown - even if the plugin is not in use.

    html.open_table(class_=["data", "headerleft"])

    html.open_tr()
    html.th(_("Title"))
    html.open_td()
    html.b(manpage["header"]["title"])
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.th(_("Name of plugin"))
    html.open_td()
    html.tt(check_type)
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.th(_("Description"))
    html.td(manpage_text(manpage["header"]["description"]))
    html.close_tr()

    def show_ruleset(varname):
        if g_rulespecs.exists(varname):
            rulespec = g_rulespecs.get(varname)
            url = html.makeuri_contextless([("mode", "edit_ruleset"), ("varname", varname)])
            param_ruleset = '<a href="%s">%s</a>' % (url, rulespec.title)
            html.open_tr()
            html.th(_("Parameter rule set"))
            html.open_td()
            html.icon_button(url, _("Edit parameter rule set for this check type"), "check_parameters")
            html.write_text(' %s' % param_ruleset)
            html.close_td()
            html.close_tr()
            html.open_tr()
            html.th(_("Example for Parameters"))
            html.open_td()
            vs = rulespec.valuespec
            vs.render_input("dummy", vs.default_value())
            html.close_td()
            html.close_tr()

    if manpage["type"] == "check_mk":
        html.open_tr()
        html.th(_("Service name"))
        html.td(HTML(manpage["service_description"].replace("%s", "&#9744;")))
        html.close_tr()

        if manpage.get("group"):
            group = manpage["group"]
            varname = "checkgroup_parameters:" + group
            show_ruleset(varname)

    else:
        varname = "active_checks:" + check_type[6:]
        show_ruleset(varname)

    html.close_table()

def manpage_text(text):
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

def validate_icon(value, varprefix):
    file_name = value[0]
    if os.path.exists("%s/share/check_mk/web/htdocs/images/icon_%s" % (cmk.paths.omd_root, file_name)) \
       or os.path.exists("%s/share/check_mk/web/htdocs/images/icons/%s" % (cmk.paths.omd_root, file_name)):
        raise MKUserError(varprefix, _('Your icon conflicts with a Check_MK builtin icon. Please '
                                       'choose another name for your icon.'))


def upload_icon(icon_info):
    # Add the icon category to the PNG comment
    from PIL import Image, PngImagePlugin
    from StringIO import StringIO
    im = Image.open(StringIO(icon_info['icon'][2]))
    im.info['Comment'] = icon_info['category']
    meta = PngImagePlugin.PngInfo()
    for k,v in im.info.iteritems():
        if k not in ('interlace', 'gamma', 'dpi', 'transparency', 'aspect'):
            meta.add_text(k, v, 0)

    # and finally save the image
    dest_dir = "%s/local/share/check_mk/web/htdocs/images/icons" % cmk.paths.omd_root
    make_nagios_directories(dest_dir)
    try:
        im.save(dest_dir+'/'+icon_info['icon'][0], 'PNG', pnginfo=meta)
    except IOError, e:
        # Might happen with interlaced PNG files and PIL version < 1.1.7
        raise MKUserError(None, _('Unable to upload icon: %s') % e)



def load_custom_icons():
    s = IconSelector()
    return s.available_icons(only_local=True)


def mode_icons(phase):
    if phase == 'title':
        return _('Manage Icons')

    elif phase == 'buttons':
        back_url = html.var("back")
        if back_url:
            html.context_button(_("Back"), back_url, "back")
        else:
            home_button()
        return

    vs_upload = Dictionary(
        title = _('Icon'),
        optional_keys = False,
        render = "form",
        elements = [
            ('icon', ImageUpload(
                title = _('Icon'),
                allow_empty = False,
                max_size = (80, 80),
                validate = validate_icon,
            )),
            ('category', DropdownChoice(
                title = _('Category'),
                choices = IconSelector._categories,
                no_preselect = True,
            ))
        ]
    )

    if phase == 'action':
        if html.has_var("_delete"):
            icon_name = html.var("_delete")
            if icon_name in load_custom_icons():
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
            icon_info = vs_upload.from_html_vars('_upload_icon')
            vs_upload.validate_value(icon_info, '_upload_icon')
            upload_icon(icon_info)
        return

    html.h3(_("Upload Icon"))
    if not config.omd_site():
        html.message(_("Sorry, you can mange your icons only within OMD environments."))
        return

    html.p(_("Allowed are single PNG image files with a maximum size of 80x80 px."))

    html.begin_form('upload_form', method='POST')
    vs_upload.render_input('_upload_icon', None)
    html.button('_do_upload', _('Upload'), 'submit')

    html.hidden_fields()
    html.end_form()

    icons = sorted(load_custom_icons().items())
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


class PasswordStore(object):
    def _load(self, lock=False):
        return store.load_from_mk_file(wato_root_dir + "/passwords.mk",
                                       key="stored_passwords", default={}, lock=lock)


    def _load_for_modification(self):
        return self._load(lock=True)


    def _owned_passwords(self):
        if config.user.may("wato.edit_all_passwords"):
            return self._load()

        user_groups = userdb.contactgroups_of_user(config.user.id)
        return dict([ (k, v) for k, v in self._load().items() if v["owned_by"] in user_groups ])


    def usable_passwords(self):
        if config.user.may("wato.edit_all_passwords"):
            return self._load()

        user_groups = userdb.contactgroups_of_user(config.user.id)

        passwords = self._owned_passwords()
        passwords.update(dict([ (k, v) for k, v in self._load().items()
                                if v["shared_with"] in user_groups ]))
        return passwords


    def _save(self, value):
        return store.save_to_mk_file(wato_root_dir + "/passwords.mk",
                                     key="stored_passwords", value=value)



class ModePasswords(WatoMode, PasswordStore):
    def __init__(self):
        super(ModePasswords, self).__init__()
        self._contact_groups = userdb.load_group_information().get("contact", {})


    def title(self):
        return _("Passwords")


    def buttons(self):
        global_buttons()
        html.context_button(_("New password"), html.makeuri_contextless([("mode", "edit_password")]), "new")


    def action(self):
        if not html.transaction_valid():
            return

        confirm = wato_confirm(_("Confirm deletion of password"),
                        _("The password may be used in checks. If you delete the password, the "
                          "checks won't be able to authenticate with this password anymore."
                          "<br><br>Do you really want to delete this password?"))
        if confirm == False:
            return False

        elif confirm:
            html.check_transaction() # invalidate transid

            passwords = self._load_for_modification()

            ident = html.var("_delete")
            if ident not in passwords:
                raise MKUserError("ident", _("This password does not exist."))

            add_change("delete-password", _("Removed the password '%s'") % ident)
            del passwords[ident]
            self._save(passwords)

            return None, _("The password has been deleted.")


    def page(self):
        html.p(_("This password management module stores the passwords you use in your checks and "
                 "special agents in a central place. Please note that this password store is no "
                 "kind of password safe. Your passwords will not be encrypted."))
        html.p(_("All the passwords you store in your monitoring configuration, "
                 "including this password store, are needed in plain text to contact remote systems "
                 "for monitoring. So all those passwords have to be stored readable by the monitoring."))


        passwords = self._owned_passwords()
        table.begin("passwords", _("Passwords"))
        for ident, password in sorted(passwords.items(), key=lambda e: e[1]["title"]):
            table.row()
            self._password_row(ident, password)

        table.end()


    def _password_row(self, ident, password):
        table.cell(_("Actions"), css="buttons")
        edit_url = html.makeuri_contextless([("mode", "edit_password"), ("ident", ident)])
        html.icon_button(edit_url, _("Edit this password"), "edit")
        delete_url = make_action_link([("mode", "passwords"), ("_delete", ident)])
        html.icon_button(delete_url, _("Delete this password"), "delete")

        table.cell(_("Title"), html.attrencode(password["title"]))
        table.cell(_("Editable by"))
        if password["owned_by"] == None:
            html.write_text(_("Administrators (having the permission "
                              "\"Write access to all passwords\")"))
        else:
            html.write_text(self._contact_group_alias(password["owned_by"]))
        table.cell(_("Shared with"))
        if not password["shared_with"]:
            html.write_text(_("Not shared"))
        else:
            html.write(html.attrencode(", ".join([ self._contact_group_alias(g) for g in password["shared_with"]])))


    def _contact_group_alias(self, name):
        return self._contact_groups.get(name, {"alias": name})["alias"]



class ModeEditPassword(WatoMode, PasswordStore):
    def __init__(self):
        super(ModeEditPassword, self).__init__()
        ident = html.var("ident")

        if ident != None:
            try:
                password = self._owned_passwords()[ident]
            except KeyError:
                raise MKUserError("ident", _("This password does not exist."))

            self._new   = False
            self._ident = ident
            self._cfg   = password
            self._title = _("Edit password: %s") % password["title"]
        else:
            self._new   = True
            self._ident = None
            self._cfg   = {}
            self._title = _("New password")


    def title(self):
        return self._title


    def buttons(self):
        html.context_button(_("Back"), html.makeuri_contextless([("mode", "passwords")]), "back")


    def valuespec(self):
        return Dictionary(
            title         = _("Password"),
            elements      = self._vs_elements(),
            optional_keys = ["contact_groups"],
            render        = "form", )


    def _vs_elements(self):
        if self._new:
            ident_attr = [
                ("ident", ID(
                    title = _("Unique ID"),
                    help = _("The ID must be a unique text. It will be used as an internal key "
                             "when objects refer to this password."),
                    allow_empty = False,
                    size = 12,
                )),
            ]
        else:
            ident_attr = [
                ("ident", FixedValue(self._ident,
                    title = _("Unique ID"),
                )),
            ]

        if config.user.may("wato.edit_all_passwords"):
            admin_element = [
                FixedValue(None,
                    title = _("Administrators"),
                    totext = _("Administrators (having the permission "
                               "\"Write access to all passwords\")"),
                )
            ]
        else:
            admin_element = []

        return ident_attr + [
            ("title", TextUnicode(
                title = _("Title"),
                allow_empty = False,
                size = 64,
            )),
            ("password", PasswordSpec(
                title = _("Password"),
                allow_empty = False,
                hidden = True,
            )),
            ("owned_by", Alternative(
                title = _("Editable by"),
                help  = _("Each password is owned by a group of users which are able to edit, "
                          "delete and use existing passwords."),
                style = "dropdown",
                elements = admin_element + [
                    DropdownChoice(
                        title = _("Members of the contact group:"),
                        choices = lambda: self.__contact_group_choices(only_own=True),
                        invalid_choice = "complain",
                        empty_text = _("You need to be member of at least one contact group to be able to "
                                       "create a password."),
                        invalid_choice_title = _("Group not existant or not member"),
                        invalid_choice_error = _("The choosen group is either not existant "
                                                 "anymore or you are not a member of this "
                                                 "group. Please choose another one."),
                    ),
                ]
            )),
            ("shared_with", DualListChoice(
                title = _("Share with"),
                help  = _("By default only the members of the owner contact group are permitted "
                          "to use a a configured password. It is possible to share a password with "
                          "other groups of users to make them able to use a password in checks."),
                choices = self.__contact_group_choices,
                autoheight = False,
            )),
        ]


    def __contact_group_choices(self, only_own=False):
        contact_groups = userdb.load_group_information().get("contact", {})

        if only_own:
            user_groups = userdb.contactgroups_of_user(config.user.id)
        else:
            user_groups = []

        entries = [ (c, g['alias']) for c, g in contact_groups.items()
                    if not only_own or c in user_groups ]
        return sorted(entries)


    def action(self):
        if html.transaction_valid():
            vs = self.valuespec()

            config = vs.from_html_vars("_edit")
            vs.validate_value(config, "_edit")

            if "ident" in config:
                self._ident = config.pop("ident")
            self._cfg = config

            passwords = self._load_for_modification()

            if self._new and self._ident in passwords:
                raise MKUserError(None, _("This ID is already in use. Please choose another one."))

            passwords[self._ident] = self._cfg

            if self._new:
                add_change("add-password", _("Added the password '%s'") % self._ident)
            else:
                add_change("edit-password", _("Edited the password '%s'") % self._ident)

            self._save(passwords)

        return "passwords"


    def page(self):
        html.begin_form("edit", method="POST")
        html.prevent_password_auto_completion()

        vs = self.valuespec()

        vs.render_input("_edit", self._cfg)
        vs.set_focus("_edit")
        forms.end()

        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


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

def download_table(title, file_titles, paths):
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
        html.div(file_size_human_readable(file_size), style="width:50px;", class_="rulecount")
        html.close_div()
        html.close_div()
    forms.end()

def mode_download_agents(phase):
    if phase == "title":
        return _("Agents and Plugins")

    elif phase == "buttons":
        global_buttons()
        if 'agents' in modes:
            html.context_button(_("Baked agents"), folder_preserving_link([("mode", "agents")]), "download_agents")
        html.context_button(_("Release Notes"), "version.py", "mk")
        return

    elif phase == "action":
        return

    html.open_div(class_="rulesets")
    packed = glob.glob(cmk.paths.agents_dir + "/*.deb") \
            + glob.glob(cmk.paths.agents_dir + "/*.rpm") \
            + glob.glob(cmk.paths.agents_dir + "/windows/c*.msi")

    download_table(_("Packaged Agents"), {}, packed)

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
                    file_titles.update(read_agent_contents_file(root))

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
        file_titles.update(read_plugin_inline_comments(useful_file_paths))
        if useful_file_paths:
            download_table(title, file_titles, sorted(useful_file_paths))
    html.close_div()



def read_plugin_inline_comments(file_paths):
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


def read_agent_contents_file(root):
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

    if is_wato_slave_site():
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
            found = do_network_scan(folder)
        else:
            found = do_remote_automation(config.site(folder.site_id()), "network-scan",
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
    for folder_path, folder in Folder.all_folders().items():
        scheduled_time = folder.next_network_scan_at()
        if scheduled_time != None and scheduled_time < time.time():
            if folder_to_scan == None:
                folder_to_scan = folder
            elif folder_to_scan.next_network_scan_at() > folder.next_network_scan_at():
                folder_to_scan = folder
    return folder_to_scan


def do_network_scan_automation():
    folder_path = html.var("folder")
    if folder_path == None:
        raise MKGeneralException(_("Folder path is missing"))
    folder = Folder.folder(folder_path)

    return do_network_scan(folder)


automation_commands["network-scan"] = do_network_scan_automation

def add_scanned_hosts_to_folder(folder, found):
    translation = folder.attribute("network_scan").get("translate_names", {})

    entries = []
    for host_name, ipaddress in found:
        host_name = do_hostname_translation(translation, host_name)

        attrs = {
            "ipaddress"       : ipaddress,
            "tag_criticality" : "offline",
        }
        if not Host.host_exists(host_name):
            entries.append((host_name, attrs, None))

    lock_exclusive()
    folder.create_hosts(entries)
    folder.save()
    unlock_exclusive()


def save_network_scan_result(folder, result):
    # Reload the folder, lock WATO before to protect against concurrency problems.
    lock_exclusive()

    # A user might have changed the folder somehow since starting the scan. Load the
    # folder again to get the current state.
    write_folder = Folder.folder(folder.path())
    write_folder.set_attribute("network_scan_result", result)
    write_folder.save()

    unlock_exclusive()


# This is executed in the site the host is assigned to.
# A list of tuples is returned where each tuple represents a new found host:
# [(hostname, ipaddress), ...]
def do_network_scan(folder):
    ip_addresses = ip_addresses_to_scan(folder)
    return scan_ip_addresses(folder, ip_addresses)


def ip_addresses_to_scan(folder):
    ip_range_specs = folder.attribute("network_scan")["ip_ranges"]
    exclude_specs = folder.attribute("network_scan")["exclude_ranges"]

    to_scan = ip_addresses_of_ranges(ip_range_specs)
    exclude = ip_addresses_of_ranges(exclude_specs)

    # Remove excludes from to_scan list
    to_scan.difference_update(exclude)

    # Reduce by all known host addresses
    # FIXME/TODO: Shouldn't this filtering be done on the central site?
    to_scan.difference_update(known_ip_addresses())

    # And now apply the IP regex patterns to exclude even more addresses
    to_scan.difference_update(excludes_by_regexes(to_scan, exclude_specs))

    return to_scan


# This will not scale well. Do you have a better idea?
def known_ip_addresses():
    addresses = []
    for hostname, host in Host.all().items():
        address = host.attribute("ipaddress")
        if address:
            addresses.append(address)
    return addresses


def ip_addresses_of_ranges(ip_ranges):
    addresses = set([])

    for ty, spec in ip_ranges:
        if ty == "ip_range":
            addresses.update(ip_addresses_of_range(spec))

        elif ty == "ip_network":
            addresses.update(ip_addresses_of_network(spec))

        elif ty == "ip_list":
            addresses.update(spec)

    return addresses


def excludes_by_regexes(addresses, exclude_specs):
    patterns = []
    for ty, spec in exclude_specs:
        if ty == "ip_regex_list":
            for p in spec:
                patterns.append(re.compile(p))

    if not patterns:
        return []

    excludes = []
    for address in addresses:
        for p in patterns:
            if p.match(address):
                excludes.append(address)
                break # one match is enough, exclude this.

    return excludes



FULL_IPV4 = (2 ** 32) - 1


def ip_addresses_of_range(spec):
    first_int, last_int = map(ip_int_from_string, spec)

    addresses = []

    if first_int > last_int:
        return addresses # skip wrong config

    while first_int <= last_int:
        addresses.append(string_from_ip_int(first_int))
        first_int += 1
        if first_int - 1 == FULL_IPV4: # stop on last IPv4 address
            break

    return addresses


def mask_bits_to_int(n):
    return (1 << (32 - n)) - 1


def ip_addresses_of_network(spec):
    net_addr, net_bits = spec

    ip_int   = ip_int_from_string(net_addr)
    mask_int = mask_bits_to_int(int(net_bits))
    first = ip_int & (FULL_IPV4 ^ mask_int)
    last = ip_int | (1 << (32 - int(net_bits))) - 1

    return [ string_from_ip_int(i) for i in range(first + 1, last - 1) ]


def ip_int_from_string(ip_str):
    packed_ip = 0
    octets = ip_str.split(".")
    for oc in octets:
        packed_ip = (packed_ip << 8) | int(oc)
    return packed_ip


def string_from_ip_int(ip_int):
    octets = []
    for _ in xrange(4):
        octets.insert(0, str(ip_int & 0xFF))
        ip_int >>=8
    return ".".join(octets)


def ping(address):
    return subprocess.Popen(['ping', '-c2', '-w2', address],
                            stdout=open(os.devnull, "a"),
                            stderr=subprocess.STDOUT,
                            close_fds=True).wait() == 0


def ping_worker(addresses, hosts):
    while True:
        try:
            ipaddress = addresses.pop()
        except KeyError:
            break

        if ping(ipaddress):
            try:
                host_name = socket.gethostbyaddr(ipaddress)[0]
            except socket.error:
                host_name = ipaddress

            hosts.append((host_name, ipaddress))


# Start ping threads till max parallel pings let threads do their work till all are done.
# let threds also do name resolution. Return list of tuples (hostname, address).
def scan_ip_addresses(folder, ip_addresses):
    num_addresses = len(ip_addresses)

    # dont start more threads than needed
    parallel_pings = min(folder.attribute("network_scan").get("max_parallel_pings", 100), num_addresses)

    # Initalize all workers
    threads = []
    found_hosts = []
    import threading
    for t_num in range(parallel_pings):
        t = threading.Thread(target = ping_worker, args = [ip_addresses, found_hosts])
        t.daemon = True
        threads.append(t)
        t.start()

    # Now wait for all workers to finish
    for t in threads:
        t.join()

    return found_hosts


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

class ModeManageReadOnly(WatoMode):
    def __init__(self):
        super(ModeManageReadOnly, self).__init__()
        self._settings = config.wato_read_only


    def title(self):
        return _("Manage configuration read only mode")


    def buttons(self):
        global_buttons()
        html.context_button(_("Back"), folder_preserving_link([("mode", "globalvars")]), "back")


    def action(self):
        settings = self._vs().from_html_vars("_read_only")
        self._vs().validate_value(settings, "_read_only")
        self._settings = settings

        self._save()


    def _save(self):
        store.save_to_mk_file(multisite_dir + "read_only.mk",
                          "wato_read_only", self._settings)


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
    if is_read_only_mode_enabled():
        html.show_warning(read_only_message())


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

def may_edit_ruleset(varname):
    if varname == "ignored_services":
        return config.user.may("wato.services") or config.user.may("wato.rulesets")
    else:
        return config.user.may("wato.rulesets")


def host_status_button(hostname, viewname):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("filename", Folder.current().path() + "/hosts.mk"),
           ("host",     hostname),
           ("site",     "")]),
           "status")


def service_status_button(hostname, servicedesc):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", "service"),
           ("host",     hostname),
           ("service",  servicedesc),
           ]),
           "status")


def folder_status_button(viewname = "allhosts"):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("wato_folder", Folder.current().path())]),
           "status")


def global_buttons():
    changelog_button()
    home_button()


def home_button():
    html.context_button(_("Main Menu"), folder_preserving_link([("mode", "main")]), "home")


def changelog_button():
    num_pending = get_number_of_pending_changes()
    if num_pending >= 1:
        hot = True
        icon = "wato_changes"

        if num_pending == 1:
            buttontext = _("1 change")
        else:
            buttontext = _("%d changes") % num_pending

    else:
        buttontext = _("No changes")
        hot = False
        icon = "wato_nochanges"
    html.context_button(buttontext, folder_preserving_link([("mode", "changelog")]), icon, hot)


# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.has_var("_do_confirm") and not html.has_var("_do_actions"):
        wato_html_head(html_title)
    return html.confirm(message)


def wato_html_head(title):
    global g_html_head_open
    if not g_html_head_open:
        g_html_head_open = True
        html.header(title, stylesheets = wato_styles)
        html.open_div(class_="wato")


def may_see_hosts():
    return config.user.may("wato.use") and \
       (config.user.may("wato.seeall") or config.user.may("wato.hosts"))



# Checks if a valuespec is a Checkbox
def is_a_checkbox(vs):
    if isinstance(vs, Checkbox):
        return True
    elif isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    else:
        return False


def site_neutral_path(path):
    if path.startswith('/omd'):
        parts = path.split('/')
        parts[3] = '&lt;siteid&gt;'
        return '/'.join(parts)
    else:
        return path


syslog_facilities = [
    (0, "kern"),
    (1, "user"),
    (2, "mail"),
    (3, "daemon"),
    (4, "auth"),
    (5, "syslog"),
    (6, "lpr"),
    (7, "news"),
    (8, "uucp"),
    (9, "cron"),
    (10, "authpriv"),
    (11, "ftp"),
    (16, "local0"),
    (17, "local1"),
    (18, "local2"),
    (19, "local3"),
    (20, "local4"),
    (21, "local5"),
    (22, "local6"),
    (23, "local7"),
]


def vs_rule_options(disabling=True):
    return Dictionary(
        title = _("Rule Options"),
        optional_keys = False,
        render = "form",
        elements = rule_option_elements(disabling),
    )


def rule_option_elements(disabling=True):
    def date_and_user():
        return time.strftime("%F", time.localtime()) + " " + config.user.id + ": "

    elements = [
        ( "description",
          TextUnicode(
            title = _("Description"),
            help = _("A description or title of this rule"),
            size = 80,
          )
        ),
        ( "comment",
          TextAreaUnicode(
            title = _("Comment"),
            help = _("An optional comment that explains the purpose of this rule."),
            rows = 4,
            cols = 80,
            prefix_buttons = [ ("insertdate", date_and_user, _("Prefix date and your name to the comment")) ]
          )
        ),
        ( "docu_url",
          TextAscii(
            title = _("Documentation-URL"),
            help = _("An optional URL pointing to documentation or any other page. This will be displayed "
                     "as an icon <img class=icon src='images/button_url.png'> and open a new page when clicked. "
                     "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
                     "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."),
            size = 80,
          ),
        ),
    ]
    if disabling:
        elements += [
            ( "disabled",
              Checkbox(
                  title = _("Rule activation"),
                  help = _("Disabled rules are kept in the configuration but are not applied."),
                  label = _("do not apply this rule"),
              )
            ),
        ]
    return elements


class UserIconOrAction(DropdownChoice):
    def __init__(self, **kwargs):
        empty_text = _("In order to be able to choose actions here, you need to "
                       "<a href=\"%s\">define your own actions</a>.") % \
                          "wato.py?mode=edit_configvar&varname=user_icons_and_actions"

        kwargs.update({
            'choices'     : self.list_user_icons_and_actions,
            'allow_empty' : False,
            'empty_text'  : empty_text,
            'help'        : kwargs.get('help', '') + ' '+empty_text,
        })
        DropdownChoice.__init__(self, **kwargs)

    def list_user_icons_and_actions(self):
        choices = []
        for key, action in config.user_icons_and_actions.items():
            label = key
            if 'title' in action:
                label += ' - '+action['title']
            if 'url' in action:
                label += ' ('+action['url'][0]+')'

            choices.append((key, label))
        return sorted(choices, key = lambda x: x[1])


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
    topics = [None]
    if configured_host_tags():
        topics.append(_("Host tags"))

    # The remaining topics are shown in the order of the
    # appearance of the attribute declarations:
    for attr, topic in all_host_attributes():
        if topic not in topics and attr.is_visible(for_what):
            topics.append(topic)

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags     = {}

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
            else:
                topic_id = None
            forms.header(title, isopen = topic == topics[0], table_id = topic_id)

        for attr, atopic in all_host_attributes():
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

                if not depends_on_tags and not depends_on_roles:
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
                host = hosts.values()[0]

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "host_search" mode.
            inherited_from = None
            inherited_value = None
            has_inherited = False
            container = None

            if attr.show_inherited_value():
                if for_what in [ "host", "cluster" ]:
                    url = Folder.current().edit_url()

                container = parent # container is of type Folder
                while container:
                    if attrname in container.attributes():
                        url = container.edit_url()
                        inherited_from = _("Inherited from ") + '<a href="%s">%s</a>' % (url, container.title())
                        inherited_value = container.attributes()[attrname]
                        has_inherited = True
                        if topic == _("Host tags"):
                            inherited_tags["attr_%s" % attrname] = '|'.join(attr.get_tag_list(inherited_value))
                        break

                    container = container.parent()
                    what = "folder"

            if not container: # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
                inherited_value = attr.default_value()
                # Also add the default values to the inherited values dict
                if topic == _("Host tags"):
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
                if active:
                    force_entry = True
                else:
                    disabled = True

            if (for_what in [ "host", "cluster" ] and parent.locked_hosts()) or (for_what == "folder" and myself and myself.locked()):
                checkbox_code = None
            elif force_entry:
                checkbox_code  = html.render_checkbox("ignored_" + checkbox_name, add_attr=["disabled"])
                checkbox_code += html.render_hidden_field(checkbox_name, "on")
            else:
                add_attr = disabled and ["disabled"] or []
                onclick = "wato_fix_visibility(); wato_toggle_attribute(this, '%s');" % attrname
                checkbox_code = html.render_checkbox(checkbox_name, active,
                                                  onclick=onclick, add_attr=add_attr)

            forms.section(_u(attr.title()), checkbox=checkbox_code, id="attr_" + attrname)
            html.help(attr.help())

            if len(values) == 1:
                defvalue = values[0]
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

                html.open_div(class_="inherited", id_="attr_default_%s" % attrname, style="display: none;" if active else None)

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation = ""
            if for_what == "bulk":
                if num_haveit == 0:
                    explanation = " (" + inherited_from + ")"
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
                    html.write(content)
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


def monitoring_macro_help():
    return " " + _("You can use monitoring macros here. The most important are: "
                   "<ul>"
                   "<li><tt>$HOSTADDRESS$</tt>: The IP address of the host</li>"
                   "<li><tt>$HOSTNAME$</tt>: The name of the host</li>"
                   "<li><tt>$_HOSTTAGS$</tt>: List of host tags</li>"
                   "<li><tt>$_HOSTADDRESS_4$</tt>: The IPv4 address of the host</li>"
                   "<li><tt>$_HOSTADDRESS_6$</tt>: The IPv6 address of the host</li>"
                   "<li><tt>$_HOSTADDRESS_FAMILY$</tt>: The primary address family of the host</li>"
                   "</ul>"
                   "All custom attributes defined for the host are available as <tt>$_HOST[VARNAME]$</tt>. "
                   "Replace <tt>[VARNAME]</tt> with the <i>upper case</i> name of your variable. "
                   "For example, a host attribute named <tt>foo</tt> with the value <tt>bar</tt> would result in "
                   "the macro <tt>$_HOSTFOO$</tt> being replaced with <tt>bar</tt> ")


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

# permissions = None -> every user can use this mode, permissions
# are checked by the mode itself. Otherwise the user needs at
# least wato.use and - if he makes actions - wato.edit. Plus wato.*
# for each permission in the list.
modes = {
   # ident,               permissions, handler function
   "main"               : ([], mode_main),
   "folder"             : (["hosts"], mode_folder),
   "newfolder"          : (["hosts", "manage_folders"], lambda phase: mode_editfolder(phase, True)),
   "editfolder"         : (["hosts" ], lambda phase: mode_editfolder(phase, False)),
   "newhost"            : (["hosts", "manage_hosts"], lambda phase: mode_edit_host(phase, new=True, is_cluster=False)),
   "newcluster"         : (["hosts", "manage_hosts"], lambda phase: mode_edit_host(phase, new=True, is_cluster=True)),
   "rename_host"        : (["hosts", "manage_hosts"], mode_rename_host),
   "bulk_rename_host"   : (["hosts", "manage_hosts"], mode_bulk_rename_host),
   "bulk_import"        : (["hosts", "manage_hosts"], ModeBulkImport),
   "host_attrs"         : (["hosts", "manage_hosts"], lambda phase: mode_custom_attrs(phase, "host")),
   "edit_host_attr"     : (["hosts", "manage_hosts"], lambda phase: mode_edit_custom_attr(phase, "host")),
   "edit_host"          : (["hosts"], lambda phase: mode_edit_host(phase, new=False, is_cluster=None)),
   "parentscan"         : (["hosts"], mode_parentscan),
   "inventory"          : (["hosts"], ModeDiscovery),
   "diag_host"          : (["hosts", "diag_host"], mode_diag_host),
   "object_parameters"  : (["hosts", "rulesets"], mode_object_parameters),
   "search"             : (["hosts"], mode_search),
   "bulkinventory"      : (["hosts", "services"], mode_bulk_discovery),
   "bulkedit"           : (["hosts", "edit_hosts"], mode_bulk_edit),
   "bulkcleanup"        : (["hosts", "edit_hosts"], mode_bulk_cleanup),
   "random_hosts"       : (["hosts", "random_hosts"], mode_random_hosts),
   "changelog"          : ([], ModeActivateChanges),
   "auditlog"           : (["auditlog"], ModeAuditLog),
   "globalvars"         : (["global"], mode_globalvars),
   "edit_configvar"     : (["global"], mode_edit_configvar),
   "ldap_config"        : (["global"], mode_ldap_config),
   "edit_ldap_connection": (["global"], mode_edit_ldap_connection),
   "static_checks"      : (["rulesets"], ModeStaticChecksRulesets),
   "check_plugins"      : ([], mode_check_plugins),
   "check_manpage"      : ([], mode_check_manpage),

   "ruleeditor"         : (["rulesets"], ModeRuleEditor),
   "rule_search"        : (["rulesets"], ModeRuleSearch),
   "rulesets"           : (["rulesets"], ModeRulesets),
   "edit_ruleset"       : ([], ModeEditRuleset),
   "new_rule"           : ([], ModeNewRule),
   "edit_rule"          : ([], ModeEditRule),

   "host_groups"        : (["groups"], ModeHostgroups),
   "service_groups"     : (["groups"], ModeServicegroups),
   "contact_groups"     : (["users"],  ModeContactgroups),
   "edit_host_group"    : (["groups"], ModeEditHostgroup),
   "edit_service_group" : (["groups"], ModeEditServicegroup),
   "edit_contact_group" : (["users"], ModeEditContactgroup),
   "notifications"      : (["notifications"], mode_notifications),
   "notification_rule"  : (["notifications"], lambda phase: mode_notification_rule(phase, False)),
   "user_notifications" : (["users"], lambda phase: mode_user_notifications(phase, False)),
   "notification_rule_p": (None, lambda phase: mode_notification_rule(phase, True)), # for personal settings
   "user_notifications_p":(None, lambda phase: mode_user_notifications(phase, True)), # for personal settings
   "timeperiods"        : (["timeperiods"], mode_timeperiods),
   "edit_timeperiod"    : (["timeperiods"], mode_edit_timeperiod),
   "import_ical"        : (["timeperiods"], mode_timeperiod_import_ical),
   "sites"              : (["sites"], ModeDistributedMonitoring),
   "edit_site"          : (["sites"], ModeEditSite),
   "edit_site_globals"  : (["sites"], ModeEditSiteGlobals),
   "users"              : (["users"], mode_users),
   "edit_user"          : (["users"], mode_edit_user),
   "user_attrs"         : (["users"], lambda phase: mode_custom_attrs(phase, "user")),
   "edit_user_attr"     : (["users"], lambda phase: mode_edit_custom_attr(phase, "user")),
   "roles"              : (["users"], mode_roles),
   "role_matrix"        : (["users"], mode_role_matrix),
   "edit_role"          : (["users"], mode_edit_role),
   "hosttags"           : (["hosttags"], mode_hosttags),
   "edit_hosttag"       : (["hosttags"], mode_edit_hosttag),
   "edit_auxtag"        : (["hosttags"], mode_edit_auxtag),
   "pattern_editor"     : (["pattern_editor"], mode_pattern_editor),
   "icons"              : (["icons"], mode_icons),
   "download_agents"    : (["download_agents"], mode_download_agents),
   "backup"             : (["backups"], ModeBackup),
   "backup_targets"     : (["backups"], ModeBackupTargets),
   "backup_job_state"   : (["backups"], ModeBackupJobState),
   "edit_backup_target" : (["backups"], ModeEditBackupTarget),
   "edit_backup_job"    : (["backups"], ModeEditBackupJob),
   "backup_keys"        : (["backups"], ModeBackupKeyManagement),
   "backup_edit_key"    : (["backups"], ModeBackupEditKey),
   "backup_upload_key"  : (["backups"], ModeBackupUploadKey),
   "backup_download_key": (["backups"], ModeBackupDownloadKey),
   "backup_restore"     : (["backups"], ModeBackupRestore),
   "passwords"          : (["passwords"], ModePasswords),
   "edit_password"      : (["passwords"], ModeEditPassword),
   "read_only"          : (["set_read_only"], ModeManageReadOnly),
}

builtin_host_attribute_names = []

loaded_with_language = False
def load_plugins(force):
    global builtin_host_attribute_names

    global loaded_with_language
    if loaded_with_language == current_language and not force:
        # Do not cache the custom attributes. They can be created by the user
        # during runtime, means they need to be loaded during each page request.
        # But delete the old definitions before to also apply removals of attributes
        if builtin_host_attribute_names:
            declare_custom_host_attrs()
        return

    # Reset global vars
    global extra_buttons, modules
    extra_buttons = []
    modules = []

    initialize_host_attribute_structures()
    undeclare_all_host_attributes()
    load_notification_table()
    initialize_global_configvars()

    # Initialize watolib things which are needed before loading the WATO plugins.
    # This also loads the watolib plugins. Then the globals of the watolib.py are
    # loaded into the wato.py namespace. This "repeats" the watolib star import above
    # together with things from the plugins. What a hack!
    # TODO: Clearly separate the watolib and wato
    globals().update(load_watolib_plugins())

    register_builtin_host_tags()

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
         _("Access to the historic audit log. A user with write "
           "access can delete the audit log. "
           "The currently pending changes can be seen by all users "
           "with access to WATO."),
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

    load_web_plugins("wato", globals())

    declare_host_tag_attributes(force = True)

    builtin_host_attribute_names = all_host_attribute_names()
    declare_custom_host_attrs()

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language


#.
#   .--External API--------------------------------------------------------.
#   |      _____      _                        _      _    ____ ___        |
#   |     | ____|_  _| |_ ___ _ __ _ __   __ _| |    / \  |  _ \_ _|       |
#   |     |  _| \ \/ / __/ _ \ '__| '_ \ / _` | |   / _ \ | |_) | |        |
#   |     | |___ >  <| ||  __/ |  | | | | (_| | |  / ___ \|  __/| |        |
#   |     |_____/_/\_\\__\___|_|  |_| |_|\__,_|_| /_/   \_\_|  |___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Functions called by others that import wato (such as views)         |
#   '----------------------------------------------------------------------'

# Return a list with all the titles of the paths'
# components, e.g. "muc/north" -> [ "Main Directory", "Munich", "North" ]
def get_folder_title_path(path, with_links=False):
    # In order to speed this up, we work with a per HTML-request cache
    cache_name = "wato_folder_titles" + (with_links and "_linked" or "")
    cache = html.set_cache_default(cache_name, {})
    if path not in cache:
        cache[path] = Folder.folder(path).title_path(with_links)
    return cache[path]


# Return the title of a folder - which is given as a string path
def get_folder_title(path):
    folder = Folder.folder(path)
    if folder:
        return folder.title()
    else:
        return path


# Create an URL to a certain WATO folder when we just know its path
def link_to_folder_by_path(path):
    return "wato.py?mode=folder&folder=" + html.urlencode(path)


# Create an URL to the edit-properties of a host when we just know its name
def link_to_host_by_name(host_name):
    return "wato.py?" + html.urlencode_vars(
    [("mode", "edit_host"), ("host", host_name)])



