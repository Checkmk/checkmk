#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#   +----------------------------------------------------------------------+
#   |               ____                _                                  |
#   |              |  _ \ ___  __ _  __| |  _ __ ___   ___                 |
#   |              | |_) / _ \/ _` |/ _` | | '_ ` _ \ / _ \                |
#   |              |  _ <  __/ (_| | (_| | | | | | | |  __/                |
#   |              |_| \_\___|\__,_|\__,_| |_| |_| |_|\___|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A few words about the implementation details of WATO.                |
#   +----------------------------------------------------------------------+

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
# Yes. Global variables are bad. But we use them anyway. Please go away
# if you do not like this. Global variables - if properly used - can make
# implementation a lot easier and clearer. Of course we could pack everything
# into a class and use class variables. But what's the difference?
#
# g_folders -> A dictionary of all folders, the key are there paths,
#              the values are dictionaries. Keys beginning
#              with a period are not persisted. Important keys are:
#
#   ".folders"        -> List of subfolders. This key is present even for leaf folders.
#   ".parent"         -> parent folder (not name, but Python reference!)
#   ".name"           -> OS name of the folder
#   ".path"           -> absolute path of folder
#   ".hosts"          -> Hosts in that folder. This key is present even if there are no hosts.
#                        If the hosts in the folder have not been loaded yet, then the key 
#                        is missing.
#   "title"           -> Title/alias of that folder
#   "attributes"      -> Attributes to be inherited to subfolders and hosts
#   "num_hosts"       -> number of hosts in this folder (this is identical to 
#                        to len() of the entry ".hosts" but is persisted for
#                        performance issues.
# 
# g_folder -> The folder object representing the folder the user is 
#             currently operating in. 
#
# g_root_folder -> The folder object representing the root folder

#   +----------------------------------------------------------------------+
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Importing, Permissions, global variables                             |
#   +----------------------------------------------------------------------+

import config

import sys, pprint, socket, re, subprocess, time, datetime, tarfile, StringIO
from lib import *
import htmllib

config.declare_permission("use_wato",
     _("Use WATO"),
     _("This permissions allows users to use WATO - Check_MK's Web Administration Tool.<br>"
     "Please make sure, that they also have the permission for the WATO snapin."),
     [ "admin", "user" ])

root_dir     = defaults.check_mk_configdir + "/wato/"
var_dir      = defaults.var_dir + "/wato/"
snapshot_dir = var_dir + "/snapshots/"

g_root_folder = None # pointer to root folder
g_folder      = None # pointer to current folder

#   +----------------------------------------------------------------------+
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
#   +----------------------------------------------------------------------+

def page_handler():
    if not config.may("use_wato"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    declare_host_tag_attributes() # create attributes out of tag definitions
    load_all_folders()            # load information about all folders
    set_current_folder()          # set g_folder from HTML variable
    load_hosts(g_folder)          # load information about hosts
    title = g_folder["title"]

    current_mode = html.var("mode", "folder")
    modefunc = mode_functions.get(current_mode)

    # except Exception, e:
    #     html.header("Error")
    #     html.show_error(e)
    #     html.footer()
    #     return


    # Do actions (might switch mode)
    action_message = None
    if html.has_var("_transid"):
        try:
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
                        html.write("</div>")
                        html.footer()
                    return
                modefunc = mode_functions.get(newmode, mode_folder)
                current_mode = newmode
                html.set_var("mode", newmode) # will be used by makeuri

        except MKUserError, e:
            action_message = e.message
            html.add_user_error(e.varname, e.message)

    # Title
    mode_title = modefunc("title")
    if mode_title:
        title += " - " + mode_title
    html.header(title)
    html.write("<script type='text/javascript' src='js/wato.js'></script>")
    html.write("<div class=wato>\n")

    try:
        # Show contexts buttons
        html.begin_context_buttons()
        modefunc("buttons")
        for inmode, buttontext, target in extra_buttons:
            if inmode == current_mode:
                if '/' == target[0] or target.startswith('../') or '://' in target:
                    html.context_button(buttontext, target)
                else:
                    html.context_button(buttontext, make_link([("mode", target)]))
        html.end_context_buttons()

        # Show outcome of action
        if html.has_users_errors():
            html.show_error(action_message)
        elif action_message:
            html.message(action_message)

        # Show content
        modefunc("content")

    except Exception, e:
        import traceback
        html.show_error(traceback.format_exc().replace('\n', '<br />'))

    html.write("</div>\n")
    html.footer()


#   +----------------------------------------------------------------------+
#   |   ____                           _____     _     _                   |
#   |  |  _ \ __ _  __ _  ___  ___ _  |  ___|__ | | __| | ___ _ __ ___     |
#   |  | |_) / _` |/ _` |/ _ \/ __(_) | |_ / _ \| |/ _` |/ _ \ '__/ __|    |
#   |  |  __/ (_| | (_| |  __/\__ \_  |  _| (_) | | (_| |  __/ |  \__ \    |
#   |  |_|   \__,_|\__, |\___||___(_) |_|  \___/|_|\__,_|\___|_|  |___/    |
#   |              |___/                                                   |
#   +----------------------------------------------------------------------+
#   | Code creating the actual web pages: handling of folders              |
#   +----------------------------------------------------------------------+

def mode_folder(phase):
    if phase == "title":
        return None

    elif phase == "buttons":
        folder_status_button()
        html.context_button(_("Properties"), make_link_to([("mode", "editfolder")], g_folder), "properties")
        html.context_button(_("New folder"), make_link([("mode", "newfolder")]), "newfolder")
        html.context_button(_("New host"), make_link([("mode", "newhost")]), "new")
        html.context_button(_("Backup / Restore"), make_link([("mode", "snapshot")]))
        changelog_button()
        search_button()
    
    elif phase == "action":
        if html.var("_search"): # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.var("_delete_folder") and html.transaction_valid():
            delname = html.var("_delete_folder")
            if delname in g_folder[".folders"]:
                del_folder = g_folder[".folders"][delname]
                if len(del_folder[".folders"]) > 0:
                    raise MKUserError(None, _("The folder %s cannot be deleted, it still contains some subfolders.")
                    % del_folder["title"])
                return delete_folder_after_confirm(del_folder)
            else:
                raise MKGeneralException(_("You called this page with a non-existing folder/file %s") % delname)

        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.var("_delete_host")
        if delname and delname in g_folder[".hosts"]:
            return delete_host_after_confirm(delname)

        # Move single hosts to other files
        move_to = html.var("_move_host_to")
        hostname = html.var("host")
        if move_to and hostname:
            move_host_to(hostname, move_to)
            return

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        if html.var("_bulk_inventory"):
            return "bulkinventory"

        selected_hosts = get_hostnames_from_checkboxes()
        if len(selected_hosts) == 0:
            raise MKUserError(None,
            _("Please select some hosts before doing bulk operations on hosts."))

        # Deletion
        if html.var("_bulk_delete"):
            return delete_hosts_after_confirm(selected_hosts)

        # Move
        elif html.var("_bulk_move"):
            target_file = html.var("bulk_moveto")
            if not target_file:
                raise MKUserError("bulk_moveto", _("Please select the destination file"))
            num_moved = move_hosts_to(selected_hosts, target_file)
            return None, _("Successfully moved %d hosts to %s") % (num_moved, target_file)

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
            return move_to_imported_folders(selected_hosts)

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"

    else:
        render_folder_path()
        have_something = show_subfolders(g_folder)
        have_something = show_hosts(g_folder) or have_something
        if not have_something:
            html.write("<div class=info>" + 
            _("There are no sub folders and no hosts in this folder. ") +
            "</div>")


def show_subfolders(folder):
    if len(folder[".folders"]) == 0:
        return False

    html.write("<h3>" + _("Subfolders") + "</h3>")
    html.write("<table class=data>\n")
    html.write("<tr><th class=left>" + _("Actions") + "</th><th>" + _("Title") + "</th>")

    for attr, topic in host_attributes:
        if attr.show_in_table() and attr.show_in_folder():
            html.write("<th>%s</th>" % attr.title())

    if not config.wato_hide_filenames:
        html.write("<th>%s</th>" % _("Directory"))
    html.write("<th class=right>" + _("Hosts") + "</th></tr>\n")

    odd = "even"

    for entry in api.sort_by_title(folder[".folders"].values()):
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)

        name = entry[".name"]
        folder_path = entry[".path"]

        edit_url     = make_link_to([("mode", "editfolder")], entry)
        delete_url   = make_action_link([("mode", "folder"), ("_delete_folder", entry[".name"])])
        enter_url    = make_link_to([], entry)

        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td>")


        # Title and filename
        html.write('<td class=takeall><a href="%s">%s</a></td>' % 
                    (enter_url, entry["title"]))

        # Attributes for Hosts
        for attr, topic in host_attributes:
            if attr.show_in_table() and attr.show_in_folder():
                attrname = attr.name()
                if attrname in entry.get("attributes", {}):
                    tdclass, content = attr.paint(entry["attributes"][attrname], "")
                else:
                    tdclass, content = "", ""
                html.write('<td class="%s">%s</td>' % (tdclass, content))

        # Internal foldername
        if not config.wato_hide_filenames:
            html.write("<td>%s</td>" % name)

        # Number of hosts
        html.write("<td>%s</td>" % num_hosts_in(entry, recurse=True))

        html.write("</tr>")
    html.write("</table>")
    return True
    


def mode_editfolder(phase, new):
    global g_folder

    if new:
        page_title = _("Create new folder")
        name, title, roles = None, None, []
        mode = "new"
    else:
        page_title = _("Edit Properties")
        name  = g_folder[".name"]
        title = g_folder["title"]
        roles = g_folder["roles"]
        mode = "edit"

    if phase == "title":
        return page_title

    elif phase == "buttons":
        # In editing mode, we always edit the *current* folder, i.e. that
        # one g_folder points to. In new mode the new folder is created
        # as a subfolder of g_folder
        if new:
            target_folder = g_folder
        else:
            target_folder = find_folder(g_folder[".path"][:-1])

        html.context_button(_("Abort"), make_link([("mode", "folder")]), "abort")
            
    elif phase == "action":
        # Title
        title = html.var_utf8("title")
        if not title:
            raise MKUserError("title", _("Please supply a title."))

        # OS filename
        if new:
            if not config.wato_hide_filenames:
                name = html.var("name", "").strip()
                check_wato_foldername("name", name)
            else:
                name = create_wato_foldername(title)

        # Roles and Permissions
        roles = [ role for role in config.roles if html.var("role_" + role) ]

        attributes = collect_attributes()
        attributes_changed = not new and attributes != g_folder.get("attributes", {})

        if new:
            newpath = g_folder[".path"] + "/" + name
            new_folder = { 
                ".name"       : name,
                ".path"       : newpath,
                "title"      : title, 
                "roles"      : roles,
                "attributes" : attributes,
                ".folders"   : {},
                ".hosts"     : {},
                "num_hosts"  : 0,
            }
            g_folders[newpath] = new_folder
            g_folder[".folders"][name] = new_folder
            call_hook_folder_created(new_folder)

            log_audit(new_folder, "new-folder", _("Created new folder %s") % title)

        else:
            log_pending(g_folder, "edit-folder", "Edited properties of folder %s" % title)

            g_folder["title"]      = title
            g_folder["roles"]      = roles
            g_folder["attributes"] = attributes

        
        html.reload_sidebar() # refresh WATO snapin. FIXME: Geht das nicht besser?
        save_folder_and_hosts(g_folder) # save folder metainformation

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        if attributes_changed:
            rewrite_config_files_below(the_folder) # due to inherited attributes
            log_pending(the_folder, "edit-folder", _("Changed attributes of folder %s") % title)
            call_hook_hosts_changed(the_folder)

        return "folder"


    else:
        html.begin_form("editfolder")
        html.write('<table class="form">\n')
        
        # title
        html.write("<tr><td class=legend colspan=2>Title</td><td class=content>")
        html.text_input("title", title)
        html.set_focus("title")
        html.write("</td></tr>\n")

        # folder name (omit this for root folder)
        if not (not new and g_folder == g_root_folder):
            if not config.wato_hide_filenames:
                html.write("<tr><td class=legend colspan=2>" 
                    + _("Internal directory name") + "<br><i>"
                    + _("This is the name of subdirectory where the files and<br> "
                    "other folders will be created. You cannot change this later") +
                    "</i></td><td class=content>")

                if new:
                    html.text_input("name")
                else:
                    html.write(name)

                html.write("</td></tr>\n")

        # permissions
        html.write("<tr><td class=legend colspan=2>" 
                   + _("Grant access to") + "</td><td class=content>")
        for role in config.roles:
            html.checkbox("role_" + role, role in g_folder["roles"])
            html.write(" " + role + "<br>")
        html.write("</td></tr>")

        # Attributes inherited to hosts
        if have_folder_attributes():
            html.write("<tr><td class=title colspan=3>")
            html.write(_("The following attributes will be inherited to all hosts "
                         "in this folder"))
            html.write("</td></tr>")
            if new:
                attributes = {}
                parent = g_folder
            else:
                attributes = g_folder.get("attributes", {})
                parent = g_folder.get(".parent")

            configure_attributes({"folder": attributes}, "folder", parent, g_folder)

        html.write('<tr><td colspan=3 class="buttons">')
        html.button("save", _("Save &amp; Finish"), "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()
        

def check_wato_foldername(htmlvarname, name):
    if name in g_folder[".folders"]:
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))
    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))
    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(htmlvarname, _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))


def create_wato_foldername(title, in_folder = None):
    if in_folder == None:
        in_folder = g_folder

    basename = convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if name not in in_folder[".folders"]:
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


def convert_title_to_filename(title):
    converted = ""
    for c in title.lower():
        if c == u'ä':
            converted += 'ae'
        elif c == u'ö':
            converted += 'oe'
        elif c == u'ü':
            converted += 'ue'
        elif c == u'ß':
            converted += 'ss'
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return str(converted)


def show_hosts(folder):
    # We assume that the hosts of the folder already have been loaded
    if len(folder[".hosts"]) == 0:
        return False

    html.write("<h3>" + _("Hosts") + "</h3>")
    html.begin_form("search")
    html.text_input("search")
    html.button("_search", _("Search"))
    html.set_focus("search")
    html.hidden_fields()
    html.end_form()
    html.write("<p>")

    hostnames = g_folder[".hosts"].keys()
    hostnames.sort()

    # Show table of hosts in this folder
    colspan = 6
    html.begin_form("hosts", None, "POST", onsubmit = 'add_row_selections(this);')
    html.write("<table class=data>\n")
    html.write("<tr><th class=left></th><th></th><th>" + _("Hostname") + "</th>")

    for attr, topic in host_attributes:
        if attr.show_in_table():
            html.write("<th>%s</th>" % attr.title())
            colspan += 1

    html.write("<th class=right>" + _("Move To") + "</th>")
    html.write("</tr>\n")
    odd = "odd"

    def bulk_actions(at_least_one_imported, top = False):
        # bulk actions
        html.write('<tr class="data %s0">' % odd)
        html.write("<td colspan=%d>" % colspan)
        html.jsbutton('_markall', _('X'), 'javascript:toggle_all_rows();')
        html.write(' ' + _("On all selected hosts:\n"))
        html.button("_bulk_delete", _("Delete"))
        html.button("_bulk_edit", _("Edit"))
        html.button("_bulk_cleanup", _("Cleanup"))
        html.button("_bulk_inventory", _("Inventory"))
        host_move_combo(None, top)
        if at_least_one_imported:
            html.button("_bulk_movetotarget", _("Move to Target Folders"))
        html.write("</td></tr>\n")

    search_text = html.var("search")

    # Remember if that host has a target folder (i.e. was imported with
    # a folder information but not yet moved to that folder). If at least
    # one host has a target folder, then we show an additional bulk action.
    at_least_one_imported = False
    more_than_ten_items = False
    for num, hostname in enumerate(hostnames):
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder)

        if effective.get("imported_folder"):
            at_least_one_imported = True

        if num == 11:
            more_than_ten_items = True

    # Add the bulk action buttons also to the top of the table when this
    # list shows more than 10 rows
    if more_than_ten_items:
        bulk_actions(at_least_one_imported, top = True)

    # Now loop again over all hosts and display them
    for hostname in hostnames:
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder)

        # Rows with alternating odd/even styles
        html.write('<tr class="data %s0">' % odd)
        odd = odd == "odd" and "even" or "odd" 

        # Column with actions (buttons)
        edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
        services_url = make_link([("mode", "inventory"), ("host", hostname)])
        clone_url    = make_link([("mode", "newhost"), ("clone", hostname)])
        delete_url   = make_action_link([("mode", "folder"), ("_delete", hostname)])

        html.write('<td class=checkbox>')
        html.write("<input type=checkbox name=\"%s\" value=%d />" % (hostname, colspan))
        html.write('</td>\n')

        html.write("<td class=buttons>")
        html.buttonlink(edit_url,     _("Edit"))
        html.buttonlink(services_url, _("Services"))
        html.buttonlink(clone_url,    _("Clone"))
        html.buttonlink(delete_url,   _("Delete"))
        html.write("</td>\n")

        # Hostname with link to details page (edit host)
        html.write('<td><a href="%s">%s</a></td>\n' % (edit_url, hostname))

        # Show attributes
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attr.show_in_table():
                if attrname in host:
                    tdclass, tdcontent = attr.paint(host.get(attrname), hostname)
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                html.write('<td class="%s">' % tdclass)
                html.write(tdcontent)
                html.write("</td>\n")

        # Move to
        html.write("<td>")
        host_move_combo(hostname)
        html.write("</td>\n")
        html.write("</tr>\n")

    bulk_actions(at_least_one_imported)
    html.write("</table>\n")

    html.hidden_fields()
    html.end_form()

    html.javascript('g_selected_rows = %s;\n'
                    'init_rowselect();' % repr(hostnames))
    return True


# Create list of all hosts that are select with checkboxes in the current file
def get_hostnames_from_checkboxes():
    hostnames = g_folder[".hosts"].keys()
    hostnames.sort()

    selected = []
    if html.var('selected_rows', '') != '':
        selected = html.var('selected_rows', '').split(',')

    selected_hosts = []
    search_text = html.var("search")
    for name in hostnames:
        if (not search_text or (search_text.lower() in name.lower())) \
            and name in selected:
            selected_hosts.append(name)
    return selected_hosts

# Form for host details (new, clone, edit)
def mode_edithost(phase, new):
    hostname = html.var("host") # may be empty in new/clone mode

    clonename = html.var("clone")
    if clonename and clonename not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page with an invalid host name."))
    
    if clonename:
        title = _("Create clone of %s") % clonename
        host = g_folder[".hosts"][clonename]
        mode = "clone"
    elif not new and hostname in g_folder[".hosts"]:
        title = _("Edit host ") + hostname
        host = g_folder[".hosts"][hostname]
        mode = "edit"
    else:
        title = _("Create new host")
        host = {}
        mode = "new"

    if phase == "title":
        return title

    elif phase == "buttons":
        if not new:
            host_status_button(hostname, "hoststatus")
        html.context_button(_("Abort"), make_link([("mode", "folder")]), "abort")
        if not new:
            html.context_button(_("Services"), make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_host_after_confirm(hostname)

        host = collect_attributes()

        # handle clone & new
        if new:
            if not hostname:
                raise MKUserError("host", _("Please specify a host name"))
            elif hostname in g_folder[".hosts"]:
                raise MKUserError("host", _("A host with this name already exists."))
            elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                raise MKUserError("host", _("Invalid host name: must contain only characters, digits, dash, underscore and dot."))

        if hostname:
            go_to_services = html.var("services")
            if html.check_transaction():
                g_folder[".hosts"][hostname] = host
                if new:
                    message = _("Created new host %s.") % hostname
                    log_pending(hostname, "create-host", message) 
                    g_folder["num_hosts"] += 1
                else:
                    log_pending(hostname, "edit-host", _("Edited properties of host [%s]") % hostname)
                save_folder_and_hosts(g_folder)
                call_hook_hosts_changed(g_folder)
            if new:
                return go_to_services and "firstinventory" or "folder"
            else:
                return go_to_services and "inventory" or "folder"


    else:
        html.begin_form("edithost")
        html.write('<table class="form">\n')

        # host name
        html.write("<tr><td class=legend colspan=2>" + _("Hostname") + "</td><td class=content>")
        if hostname and mode == "edit":
            html.write(hostname)
        else:
            html.text_input("host")
            html.set_focus("host")
        html.write("</td></tr>\n")

        configure_attributes({hostname: host}, "host", parent = g_folder)

        html.write('<tr><td class="buttons" colspan=3>')
        html.button("save", _("Save &amp; Finish"), "submit")
        if not new:
            html.button("delete", _("Delete host!"), "submit")
        html.button("services", _("Save &amp; go to Services"), "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()


def mode_inventory(phase, firsttime):
    hostname = html.var("host")
    if hostname not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page for a non-existing host."))

    if phase == "title":
        title = _("Services of host %s") % hostname
        if html.var("_scan"):
            title += _(" (live scan)")
        else:
            title += _(" (cached data)")
        return title

    elif phase == "buttons":
        host_status_button(hostname, "host")
        html.context_button(_("Folder"), make_link([("mode", "folder")]))
        html.context_button(_("Edit host"), make_link([("mode", "edithost"), ("host", hostname)]))
        html.context_button(_("Full Scan"), html.makeuri([("_scan", "yes")]))

    elif phase == "action":
        if html.check_transaction():
            cache_options = not html.var("_scan") and [ '--cache' ] or []
            table = check_mk_automation("try-inventory", cache_options + [hostname])
            table.sort()
            active_checks = {}
            new_target = "folder"
            for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
                if (html.has_var("_cleanup") or html.has_var("_fixall")) and st in [ "vanished", "obsolete" ]:
                    pass
                elif (html.has_var("_activate_all") or html.has_var("_fixall")) and st == "new":
                    active_checks[(ct, item)] = paramstring
                else:
                    varname = "_%s_%s" % (ct, item)
                    if html.var(varname, "") != "":
                        active_checks[(ct, item)] = paramstring

            check_mk_automation("set-autochecks", [hostname], active_checks)
            message = _("Saved check configuration of host [%s] with %d services") % (hostname, len(active_checks)) 
            log_pending(hostname, "set-autochecks", message) 
            return new_target, message
        return "folder"


    else:
        show_service_table(hostname, firsttime)

#   +----------------------------------------------------------------------+
#   |             ____                        _           _                |
#   |            / ___| _ __   __ _ _ __  ___| |__   ___ | |_              |
#   |            \___ \| '_ \ / _` | '_ \/ __| '_ \ / _ \| __|             |
#   |             ___) | | | | (_| | |_) \__ \ | | | (_) | |_              |
#   |            |____/|_| |_|\__,_| .__/|___/_| |_|\___/ \__|             |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Dialog for backup/restore/creation of snapshotsp                     |
#   +----------------------------------------------------------------------+


def mode_snapshot(phase):
    if phase == "title":
        return _("Backup/Restore")
    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        html.context_button(_("Create Snapshot"), make_action_link([("mode", "snapshot"),("_create_snapshot","Yes")]))
        return
    elif phase == "action":
        if html.has_var("_download_file"):
            # FIXME: HTML Variable pruefen, kein join verwenden
            download_file = os.path.join(snapshot_dir, html.var("_download_file"))
            if os.path.exists(download_file):
                html.req.headers_out['Content-Disposition'] = 'Attachment; filename=' + html.var("_download_file")
                html.req.headers_out['content_type'] = 'application/x-tar'
                html.write(open(download_file).read())
                return False
        # create snapshot
        elif html.has_var("_create_snapshot"):
            if html.check_transaction():
                create_snapshot()
                return None, _("Snapshot created.")
            else:
                return None
        # upload snapshot
        elif html.has_var("_upload_file"):
            if html.var("_upload_file") == "":
                raise MKUserError(None, _("You need to select a file for upload"))

                return None
            if html.check_transaction():
                restore_snapshot(None, html.var('_upload_file'))
                return None, _("Successfully uploaded configuration.")
            else:
                return None
        # delete file
        elif html.has_var("_delete_file"):
            delete_file = html.var("_delete_file")
            c = wato_confirm(_("Confirm delete snapshot"),
                             _("Are you sure you want to delete the snapshot <br><br>%s?") %
                                delete_file
                            )
            if c:
                # FIXME: kein join verwenden
                os.remove(os.path.join(snapshot_dir, delete_file))
                return None, _("Snapshot deleted.")
            elif c == False: # not yet confirmed
                return ""
            else:
                return None  # browser reload
        # restore snapshot
        elif html.has_var("_restore_snapshot"):
            snapshot_file = html.var("_restore_snapshot")
            c = wato_confirm(_("Confirm restore snapshot"),
                             _("Are you sure you want to restore the snapshot <br><br>%s ?") %
                                snapshot_file
                            )
            if c:
                restore_snapshot(snapshot_file)
                return None, _("Snapshot restored.")
            elif c == False: # not yet confirmed
                return ""
            else:
                return None  # browser reload
        return False
    else:
        snapshots = []
        if os.path.exists(snapshot_dir):
            for f in os.listdir(snapshot_dir):
                snapshots.append(f)
        snapshots.sort(reverse=True)

        if len(snapshots) == 0:
            html.write("<div class=info>" + _("There are no snapshots available.") + "</div>")
        else:
            html.write('<table class=data>')
            html.write('<h3>' + _("Snapshots") + '</h3>')

            odd = "odd"
            for name in snapshots:
                odd = odd == "odd" and "even" or "odd"
                html.write('<tr class="data %s0"><td>' % odd)
                html.buttonlink(make_action_link([("mode","snapshot"),("_restore_snapshot", name)]), _("Restore"))
                html.buttonlink(make_action_link([("mode","snapshot"),("_delete_file", name)]), _("Delete"))
                html.write("<td>")
                html.write('<a href="%s">%s</a>' % (make_action_link([("mode","snapshot"),("_download_file", name)]), name))
            html.write('</table>')

        html.write("<h3>" + _("Restore from uploaded file") + "</h3>")
        html.begin_form("upload_form", None, "POST")
        html.upload_file("_upload_file")
        html.button("upload_button", _("Restore from file"), "submit")
        html.hidden_fields()
        html.end_form()


def create_snapshot():
    if not os.path.exists(snapshot_dir):
       os.mkdir(snapshot_dir)

    snapshot_name = "wato-snapshot-%s.tar.gz" % time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    # FIXME: kein join verwenden
    tar = tarfile.open(os.path.join(snapshot_dir, snapshot_name),"w:gz")

    len_abs = len(defaults.check_mk_configdir)
    for root, dirs, files in os.walk(defaults.check_mk_configdir):
        for filename in files:
            tar.add(os.path.join(root,filename), os.path.join(root[len_abs:], filename))
    tar.close()

    log_audit(None, "snapshot-created", _("Created snapshot %s") % snapshot_name)

    # Maintenance, remove old snapshots
    snapshots = []
    for f in os.listdir(snapshot_dir):
        snapshots.append(f)
    snapshots.sort(reverse=True)
    while len(snapshots) > config.max_snapshots:
        log_pending(None, "snapshot-removed", _("Removed snapshot %s") % snapshots[-1])
        # FIXME: kein join verwenden
        os.remove(os.path.join(snapshot_dir,snapshots.pop()))

def restore_snapshot( filename, tarstream = None ):
    if not os.path.exists(snapshot_dir):
       os.mkdir(snapshot_dir)

    del_config_dir()
    if filename:
        # FIXME: kein join verwenden
        if not os.path.exists(os.path.join(snapshot_dir, filename)):
            raise MKGeneralException(_("Snapshot does not exist %s" % filename))
        snapshot = tarfile.open(os.path.join(snapshot_dir, filename), "r:gz")
    elif tarstream:
        stream = StringIO.StringIO()
        stream.write(tarstream)
        stream.seek(0)
        snapshot = tarfile.open(None, "r:gz", stream)
    else:
        return

    snapshot.extractall(defaults.check_mk_configdir)
    snapshot.close()
    log_pending(None, "snapshot-restored", _("Restored snapshot %s") % (filename or _('from uploaded file')))

def del_config_dir():
    if not defaults.check_mk_configdir.endswith("conf.d"):
        raise MKGeneralException("ERROR: config directory seems incorrect. check_mk_configdir %s" % defaults.check_mk_configdir)
    # Clear directories, DANGER
    for root, dirs, files in os.walk(defaults.check_mk_configdir):
        for f in files:
            if (f.endswith('.mk') and not '.' in f[:-3]) or (f.endswith('.mk.wato') and not '.' in f[:-8]) or f == '.wato':
                os.remove(os.path.join(root, f))


#   +----------------------------------------------------------------------+
#   |                   ____                      _                        |
#   |                  / ___|  ___  __ _ _ __ ___| |__                     |
#   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
#   |                   ___) |  __/ (_| | | | (__| | | |                   |
#   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Dialog for searching for hosts - globally in all files               |
#   +----------------------------------------------------------------------+

def mode_search(phase):
    if phase == "title":
        return _("Search for hosts in %s and below" % (g_folder["title"]))

    elif phase == "buttons":
        html.context_button(_("Back"), make_link_to([("mode", "folder")], g_folder), "back")

    elif phase == "action":
        pass

    else:
        html.write("<table><tr><td>\n")

        ## # Show search form
        html.begin_form("search")
        html.write("<table class=form>")

        # host name
        html.write("<tr><td class=legend colspan=2>" + _("Hostname") + "</td><td class=content>")
        html.text_input("host")
        html.set_focus("host")
        html.write("</td></tr>\n")

        # Attributes
        configure_attributes({}, "search", parent = None)
        
        # Button
        html.write('<tr><td class="buttons" colspan=3>')
        html.button("_global", _("Search globally"), "submit")
        html.button("_local", _("Search in %s") % g_folder["title"], "submit")
        html.write("</td></tr>\n")
        

        
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()

        # Show search results
        if html.transaction_valid():
            html.write("</td><td>")
            crit = {
                ".name" : html.var("host"),
            }
            crit.update(collect_attributes(do_validate = False))

            html.write("<h3>" + _("Search results:") + "</h3>")
            if html.has_var("_local"):
                folder = g_folder
            else:
                folder = g_root_folder

            # html.write("<pre>%s</pre>" % pprint.pformat(crit))
            if not search_hosts_in_folder(folder, crit):
                html.message(_("No matching hosts found."))

        html.write("</td></tr></table>")



def search_hosts_in_folder(folder, crit):
    num_found = 0
    for f in folder[".files"].values():
        num_found += search_hosts_in_file(folder, f, crit)
    for f in folder[".folders"].values():
        num_found += search_hosts_in_folder(f, crit)
    return num_found


def tuple_starts_with(t1, t2):
    return t1[0:len(t2)] == t2

def search_hosts_in_file(the_folder, the_file, crit):
    found = []
    hosts = load_hosts_file(the_folder, the_file)
    for hostname, host in hosts.items():
        if crit[".name"] and crit[".name"].lower() not in hostname.lower():
            continue

        # Compute inheritance
        effective = effective_attributes(host, the_file)

        # Check attributes
        dont_match = False
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attrname in crit and  \
                not attr.filter_matches(crit[attrname], effective.get(attrname), hostname):
                dont_match = True
                break
        if dont_match: 
           continue

        found.append((hostname, host, effective))

    if found:
        render_folder_path(the_folder, the_file, True)
        found.sort()
        html.write("<table class=data><tr><th>%s</th>" % (_("Hostname"), ))
        for attr, topic in host_attributes:
            if attr.show_in_table():
                html.write("<th>%s</th>" % attr.title())
        html.write("</tr>")

        even = "even"
        for hostname, host, effective in found:
            even = even == "even" and "odd" or "even"
            host_url =  make_link_to([("mode", "edithost"), ("host", hostname)], the_folder, the_file[".name"])
            html.write('<tr class="data %s0"><td><a href="%s">%s</a></td>\n' % 
               (even, host_url, hostname))
            for attr, topic in host_attributes:
                attrname = attr.name()
                if attr.show_in_table():
                    if attrname in host:
                        tdclass, content = attr.paint(host[attrname], hostname)
                    else:
                        tdclass, content = attr.paint(effective[attrname], hostname)
                        tdclass += " inherited"
                    html.write('<td class="%s">%s</td>' % (tdclass, content))
        html.write("</tr>\n")
        html.write("</table><br>\n")

    return len(found)


def move_to_imported_folders(hosts):
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
    targets = {}
    for hostname in hosts:
        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_file) 
        imported_folder = effective.get('imported_folder')
        if imported_folder == None:
            continue
        targets.setdefault(imported_folder, []).append(hostname)

        # Remove target folder information, now that the hosts are
        # at their target position.
        del host['imported_folder']

    # Now handle each target folder
    num_moved = 0
    for imported_folder, hosts in targets.items():
        # Next problem: The folder path in imported_folder refers 
        # to the Alias of the folders, not to the internal file
        # name. And we need to create folders not yet existing.
        target_file = create_target_file_from_aliaspath(imported_folder)
        num_moved += move_hosts_to(hosts, target_file) 

    save_folder_config()
    html.reload_sidebar() # refresh WATO snapin
    return None, _("Successfully moved %d hosts to their original folder destinations.") % num_moved


def create_target_file_from_aliaspath(aliaspath):
    # The alias path is a '/' separated path of folder titles.
    # An empty path is interpreted as root path. The actual file
    # name is the host list with the name "Hosts". 
    if aliaspath == "":
        folder = g_root_folder
    else:
        parts = aliaspath.split("/")
        folder = g_root_folder
        while len(parts) > 0: 
            # Look in current folder for subfolder with the target name
            for name, f in folder.get(".folders", {}).items(): 
                if f["title"] == parts[0]:
                    folder = f
                    parts = parts[1:]
                    break
            else: # not found. Create this folder
                name = create_wato_foldername(parts[0], folder)
                new_folder = {
                    ".name" : name,
                    ".path" : folder[".path"] + (name,),
                    "title" : parts[0],
                    "roles" : folder["roles"],
                    "attributes" : {}, 
                    ".folders" : {},
                    ".files" : {},
                }
                folder[".folders"][name] = new_folder
                folder = new_folder
                parts = parts[1:]

    # Now folder points to the folder the host needs to be created
    # in. In that folder we put the host into the host list "hosts.mk". 
    if "hosts.mk" not in folder[".files"]:
        new_file = {
            ".name" : "hosts.mk",
            ".path" : folder[".path"] + ("hosts.mk",),
            "title" : _("Hosts"),
            "roles" : folder["roles"],
            "attributes" : {},
            "num_hosts" : 0, 
        }
        folder[".files"]["hosts.mk"] = new_file 
        g_files[new_file[".path"]] = new_file

    the_file = folder[".files"]["hosts.mk"]
    return "/" + "/".join(the_file[".path"])







 






#   +----------------------------------------------------------------------+
#   |  ____        _ _      ___                      _                     |
#   | | __ ) _   _| | | __ |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _   |
#   | |  _ \| | | | | |/ /  | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |  |
#   | | |_) | |_| | |   <   | || | | \ V /  __/ | | | || (_) | |  | |_| |  |
#   | |____/ \__,_|_|_|\_\ |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |  |
#   |                                                              |___/   |
#   +----------------------------------------------------------------------+
#   | When the user wants to scan the services of multiple hosts at once   |
#   | this function is used. There is no fine-tuning possibility. We       |
#   | simply do something like -I or -II on the list of hosts.             |
#   +----------------------------------------------------------------------+

def mode_bulk_inventory(phase):
    if phase == "title":
        return _("Bulk service detection (inventory)")

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.var("_item"):
            how = html.var("how")
            hostname = html.var("_item")
            try:
                counts = check_mk_automation("inventory", [how, hostname])
                result = repr([ 'continue', 1, 0 ] + list(counts)) + "\n"
                result += _("Inventorized %s<br>\n") % hostname
                log_pending(hostname, "bulk-inventory", _("Inventorized host: %d added, %d removed, %d kept, %d total services") % counts)
            except Exception, e:
                result = repr([ 'failed', 1, 1, 0, 0, 0, 0, ]) + "\n"
                result += _("Error during inventory of %s: %s<br>\n") % (hostname, e)
            html.write(result)
            return ""
        return

    # interactive progress is *not* done in action phase. It
    # renders the page content itself.
    hostnames = get_hostnames_from_checkboxes()

    if html.var("_start"):
        # Start interactive progress
        interactive_progress(
            hostnames,         # list of items
            _("Bulk inventory"),  # title
            [ (_("Total hosts"), 0), (_("Failed hosts"), 0), (_("Services added"), 0), (_("Services removed"), 0), 
              (_("Services kept"), 0), (_("Total services"), 0) ], # stats table
            [ ("mode", "folder") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
        )

    else:
        html.begin_form("bulkinventory", None, "POST")
        html.hidden_fields()

        # Mode of action
        html.write(_("<p>You have selected <b>%d</b> hosts for bulk inventory. "
                   "Check_MK inventory will automatically find and configure "
                   "services to be checked on your hosts.</p>") % len(hostnames))
        html.write("<table class=form>")
        html.write("<tr><td class=legend>" + _("Mode") + "</td><td class=content>")
        html.radiobutton("how", "new",     True,  _("Find only new services") + "<br>")
        html.radiobutton("how", "remove",  False, _("Remove obsolete services") + "<br>")
        html.radiobutton("how", "fixall",  False, _("Find new &amp; remove obsolete") + "<br>")
        html.radiobutton("how", "refresh", False, _("Refresh all services (tabula rasa)") + "<br>")
        html.write("</td></tr>")

        # Check type (first we need a Check_MK automation service for getting the list of checktype)
        # html.write("<tr><td class=legend>Checktype</td><td class=content>")
        # selection = check_mk_automation('get-checktypes')
        # html.sorted_select("check_command", [("", "all types")] + [(x,x) for x in selection])
        # html.write("</td></tr>")

        # Start button 
        html.write('<tr><td colspan=2 class="buttons">')
        html.button("_start", _("Start!"))
        html.write("</tr>")

        html.write("</table>")

#   +----------------------------------------------------------------------+
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
#   +----------------------------------------------------------------------+

def mode_bulk_edit(phase):
    if phase == "title":
        return _("Bulk edit hosts")

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            changed_attributes = collect_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_folder[".hosts"][hostname]
                host.update(changed_attributes)
                log_pending(hostname, "bulk-edit", _("Changed attributes of host %s in bulk mode") % hostname)
            save_folder_and_hosts(g_folder)
            call_hook_hosts_changed(g_file)
            return "folder"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_folder[".hosts"][hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk edit. You can now change "
               "host attributes for all selected hosts at once. ") % len(hostnames))
    html.write(_("If a select is set to <i>don't change</i> then currenty not all selected "
    "hosts share the same setting for this attribute. If you leave that selection, all hosts "
    "will keep their individual settings.") + "</p>")

    html.begin_form("bulkedit", None, "POST")
    html.write("<table class=form>")
    configure_attributes(hosts, "bulk", parent = g_folder)
    html.write('<tr><td colspan=3 class="buttons">')
    html.button("_save", _("Save &amp; Finish"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


def mode_bulk_cleanup(phase):
    if phase == "title":
        return _("Bulk removal of explicit attributes")

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            to_clean = bulk_collect_cleaned_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_folder[".hosts"][hostname]
                num_cleaned = 0
                for attrname in to_clean:
                    num_cleaned += 1
                    if attrname in host:
                        del host[attrname]
                if num_cleaned > 0:
                    log_pending(hostname, "bulk-cleanup", _("Cleaned %d attributes of host %s in bulk mode") % (
                    num_cleaned, hostname))
            save_hosts(g_folder)
            call_hook_hosts_changed(g_file)
            return "folder"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_folder[".hosts"][hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
    "explicit attribute values from hosts. The hosts will then inherit attributes "
    "configured at the host list or folders or simply fall back to the builin "
    "default values.") % len(hostnames))
    html.write("</p>")

    html.begin_form("bulkcleanup", None, "POST")
    html.write("<table class=form>")
    if not bulk_cleanup_attributes(g_folder, hosts):
        html.write("<tr><td class=buttons>")
        html.write(_("The selected hosts have no explicit attributes"))
        html.write("</td></tr>\n")
    else:
        html.write('<tr><td colspan=2 class="buttons">')
        html.button("_save", _("Save &amp; Finish"))
        html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


def bulk_collect_cleaned_attributes():
    to_clean = []
    for attr, topic in host_attributes:
        attrname = attr.name()
        if html.get_checkbox("_clean_" + attrname) == True:
            to_clean.append(attrname)
    return to_clean


def bulk_cleanup_attributes(the_file, hosts):
    num_shown = 0
    for attr, topic in host_attributes:
        attrname = attr.name()

        # only show attributes that at least on host have set
        num_haveit = 0
        for hostname, host in hosts.items():
            if attrname in host:
                num_haveit += 1

        if num_haveit == 0:
            continue

        # If the attribute is mandatory and no value is inherited
        # by file or folder, the attribute cannot be cleaned.
        container = the_file
        is_inherited = False
        while container:
            if "attributes" in container and attrname in container["attributes"]:
                is_inherited = True
                inherited_value = container["attributes"][attrname]
                break
            container = container.get(".parent")


        num_shown += 1

        # Legend and Help
        html.write("<tr><td class=legend>%s" % attr.title())
        if attr.help():
            html.write("<br><i>%s</i>" % attr.help())
        html.write("</td>")
        html.write("<td class=content>")

        if attr.is_mandatory() and not is_inherited:
            html.write(_("This attribute is mandatory and there is no value "
                         "defined in the host list or any parent folder."))
        else:
            html.checkbox("_clean_%s" % attrname, False)
            html.write(" clean this attribute on <b>%s</b> hosts" % 
                (num_haveit == len(hosts) and "all selected" or str(num_haveit)))
        html.write("</td></tr>")

    return num_shown > 0



#   +----------------------------------------------------------------------+
#   |                    _                 __ _ _                          |
#   |                   | |    ___   __ _ / _(_) | ___                     |
#   |                   | |   / _ \ / _` | |_| | |/ _ \                    |
#   |                   | |__| (_) | (_| |  _| | |  __/                    |
#   |                   |_____\___/ \__, |_| |_|_|\___|                    |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Handling of the audit logfiles                                       |
#   +----------------------------------------------------------------------+

def mode_changelog(phase):
    if phase == "title":
        return _("Change log")

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        if log_exists("pending"):
            html.context_button(_("Activate Changes!"), 
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())]), "apply", True)
        if log_exists("audit"):
            html.context_button(_("Clear Audit Log"),
                html.makeuri([("_action", "clear"), ("_transid", html.current_transid())]), "trash")
            html.context_button(_("Download Audit Log"),
                html.makeuri([("_action", "csv"), ("_transid", html.current_transid())]), "csv")

    elif phase == "action":
        if html.var("_action") == "clear":
            return clear_audit_log_after_confirm()

        elif html.var("_action") == "csv":
            return export_audit_log()

        elif html.check_transaction():
                create_snapshot()
                try:
                    check_mk_automation("restart")
                    call_hook_activate_changes()
                except Exception, e:
                    raise MKUserError(None, str(e))
                log_commit_pending() # flush logfile with pending actions
                log_audit(None, "activate-config", _("Configuration activated, monitoring server restarted"))
                return None, _("The new configuration has been successfully activated.")


    else:
        pending = parse_audit_log("pending")
        render_audit_log(pending, "pending")

        audit = parse_audit_log("audit")
        render_audit_log(audit, "audit")


def log_entry(linkinfo, action, message, logfilename):
    if type(message) == unicode:
        message = message.encode("utf-8")
    make_nagios_directory(var_dir)
    if type(linkinfo) == dict and linkinfo[".path"] in g_folders:
        link = linkinfo[".path"]
    elif linkinfo == None:
        link = "-"
    else:
        link = linkinfo

    log_file = var_dir + logfilename
    f = create_user_file(log_file, "ab")
    f.write("%d %s %s %s " % (int(time.time()), link, html.req.user, action))
    f.write(message)
    f.write("\n")


def log_audit(linkinfo, what, message):
    log_entry(linkinfo, what, message, "audit.log")


def log_pending(linkinfo, what, message):
    log_entry(linkinfo, what, message, "pending.log")
    log_entry(linkinfo, what, message, "audit.log")

def log_commit_pending():
    pending = var_dir + "pending.log"
    if os.path.exists(pending):
        os.remove(pending)

def clear_audit_log():
    path = var_dir + "audit.log"
    if os.path.exists(path):
        newpath = path + time.strftime(".%Y-%m-%d")
        if os.path.exists(newpath):
            n = 1
            while True:
                n += 1
                with_num = newpath + "-%d" % n
                if not os.path.exists(with_num):
                    newpath = with_num
                    break
        os.rename(path, newpath)

def clear_audit_log_after_confirm():
    c = wato_confirm(_("Confirm deletion of audit logfile"),
                     _("Do you really want to clear audit logfile?"))
    if c:
        clear_audit_log()
        return None, _("Cleared audit logfile.")
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def parse_audit_log(what):
    path = var_dir + what + ".log"
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip().decode("utf-8")
            entries.append(line.split(None, 4))
        entries.reverse()
        return entries
    return []

def log_exists(what):
    path = var_dir + what + ".log"
    return os.path.exists(path)



def render_linkinfo(linkinfo):
    if ':' in linkinfo:
        pathname, hostname = linkinfo.split(':', 1)
        path = tuple(pathname[1:].split("/"))
        if path in g_files:
            the_file = g_files[path]
            the_folder = find_folder(path[:-1])
            hosts = load_hosts_file(the_folder, the_file)
            if hostname in hosts:
                url = html.makeuri_contextless([("mode", "edithost"), ("folder", pathname), ("host", hostname)])
                title = hostname
            else:
                return hostname
        else:
            return hostname
    elif linkinfo[0] == '/':
        path = tuple(linkinfo[1:].strip("/").split("/"))
        if path in g_files:
            url = html.makeuri_contextless([("mode", "folder"), ("filename", linkinfo)])
            title = g_files[path]["title"]
        elif find_folder(path):
            url = html.makeuri_contextless([("mode", "folder"), ("filename", linkinfo)])
            title = find_folder(path)["title"]
        else:
            return linkinfo
    else:
        return ""

    return '<a href="%s">%s</a>' % (url, title)

def get_timerange(t):
    st    = time.localtime(int(t))
    start = int(time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
    end   = start + 86399
    return start, end

def fmt_date(t):
    return time.strftime('%Y-%m-%d', time.localtime(t))

def fmt_time(t):
    return time.strftime('%H:%M:%S', time.localtime(t))

def paged_log(log):
    start = html.var('start', None)
    if not start:
        start = time.time()
    start_time, end_time = get_timerange(int(start))

    previous_log_time = None
    next_log_time     = None
    first_log_index   = None
    last_log_index    = None
    for index, (t, linkinfo, user, action, text) in enumerate(log):
        t = int(t)
        if t >= end_time:
            # This log is too new
            continue
        elif first_log_index is None and t < end_time and t >= start_time:
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

def display_paged((start_time, end_time, previous_log_time, next_log_time)):
    html.write('<div class=paged_controls>')

    html.write(' <b>%s</b> ' % (_('%s to %s') % (fmt_date(start_time),
                                                 fmt_date(end_time))))

    if previous_log_time is not None:
        html.buttonlink(html.makeuri([('start', previous_log_time)]), _("<"),
                        title = '%s: %s' % (_("Older events"), fmt_date(previous_log_time)))
    else:
        html.buttonlink(html.makeuri([]), _("<"), disabled = True)

    html.buttonlink(html.makeuri([('start', get_timerange(int(time.time()))[0])]), _("o"),
                    title = _("Todays events"))

    if next_log_time is not None:
        html.buttonlink(html.makeuri([('start', next_log_time)]), _(">"),
                        title = '%s: %s' % (_("Newer events"), fmt_date(next_log_time)))
    else:
        html.buttonlink(html.makeuri([]), _(">"), disabled = True)
    html.write('</div>')


def render_audit_log(log, what, with_filename = False):
    htmlcode = ''
    if what == 'audit':
        log, times = paged_log(log)
        empty_msg = _("The logfile is empty. No host has been created or changed yet.")
    elif what == 'pending':
        empty_msg = _("No pending changes, monitoring server is up to date.")

    if len(log) == 0:
        htmlcode += "<div class=info>%s</div>" % empty_msg
        return
    elif what == 'audit':
        htmlcode += "<b>" + _("All Changes") + "</b>"
    elif what == 'pending':
        htmlcode += "<h1>" + _("Changes which are not yet activated:") + "</h1>"

    if what == 'audit':
        display_paged(times)

    htmlcode += '<table class="wato auditlog">'
    even = "even"
    for t, linkinfo, user, action, text in log:
        even = even == "even" and "odd" or "even"
        htmlcode += '<tr class="%s0">' % even
        htmlcode += '<td>%s</td>' % render_linkinfo(linkinfo)
        htmlcode += '<td>%s</td><td>%s</td><td>%s</td><td width="100%%">%s</td></tr>\n' % (
                                          fmt_date(float(t)), fmt_time(float(t)), user, text)
    htmlcode += "</table>"

    if what == 'audit':
        html.write(htmlcode)
        display_paged(times)
    else:
        html.show_warning(htmlcode)

def export_audit_log():
    html.req.content_type = "text/csv; charset=UTF-8"
    filename = 'wato-auditlog-%s_%s.csv' % (fmt_date(time.time()), fmt_time(time.time()))
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
    for t, linkinfo, user, action, text in parse_audit_log("audit"):
        if linkinfo == '-':
            linkinfo = ''
        html.write(','.join((fmt_date(int(t)), fmt_time(int(t)), linkinfo,
                             user, action, '"' + text + '"')) + '\n')
    return False

#   +----------------------------------------------------------------------+
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Functions needed at various places                                   |
#   +----------------------------------------------------------------------+

def check_mk_automation(command, args=[], indata=""):
    # Gather the command to use for executing --automation calls to check_mk
    # - First try to use the check_mk_automation option from the defaults
    # - When not set try to detect the command for OMD or non OMD installations
    #   - OMD 'own' apache mode or non OMD: check_mk --automation
    #   - OMD 'shared' apache mode: Full path to the binary and the defaults
    sudoline = None
    if defaults.check_mk_automation:
        commandargs = defaults.check_mk_automation.split()
        cmd = commandargs + [ command, '--' ] + args
    else:
        omd_mode, omd_site = html.omd_mode()
        if not omd_mode or omd_mode == 'own':
            commandargs = [ 'check_mk', '--automation' ]
            cmd = commandargs  + [ command, '--' ] + args
        else: # OMD shared mode
            commandargs = [ 'sudo', '/bin/su', '-', omd_site, '-c', 'check_mk --automation' ]
            cmd = commandargs[:-1] + [ commandargs[-1] + ' ' + ' '.join([ command, '--' ] + args) ]
            sudoline = "%s ALL = (root) NOPASSWD: /bin/su - %s -c check_mk\\ --automation\\ *" % (html.apache_user(), omd_site)

    sudo_msg = ''
    if commandargs[0] == 'sudo':
        if not sudoline:
            if commandargs[1] == '-u': # skip -u USER in /etc/sudoers
                sudoline = "%s ALL = (%s) NOPASSWD: %s *" % (html.apache_user(), commandargs[2], " ".join(commandargs[3:]))
            else:
                sudoline = "%s ALL = (root) NOPASSWD: %s *" % (html.apache_user(), commandargs[0], " ".join(commandargs[1:]))
            
        sudo_msg = ("<p>The webserver is running as user which has no rights on the "
                    "needed Check_MK/Nagios files.<br />Please ensure you have set-up "
                    "the sudo environment correctly. e.g. proceed as follows:</p>\n"
                    "<ol><li>install sudo package</li>\n"
                    "<li>Append the following to the <code>/etc/sudoers</code> file:\n"
                    "<pre># Needed for WATO - the Check_MK Web Administration Tool\n"
                    "Defaults:%s !requiretty\n"
                    "%s\n"
                    "</pre></li>\n"
                    "<li>Retry this operation</li></ol>\n" %
                    (html.apache_user(), sudoline))

    try:
        # This debug output makes problems when doing bulk inventory, because
        # it garbles the non-HTML response output
        # if config.debug:
        #     html.write("<div class=message>Running <tt>%s</tt></div>\n" % " ".join(cmd))
        p = subprocess.Popen(cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception, e:
        if commandargs[0] == 'sudo':
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s<br /><br >%s" % (commandargs[0], e, sudo_msg))
        else:
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s" % (commandargs[0], e))
    p.stdin.write(repr(indata))
    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    if exitcode != 0:
        raise MKGeneralException("Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>%s" %
              (" ".join(cmd), exitcode, outdata, sudo_msg))
    try:
        return eval(outdata)
    except Exception, e:
        raise MKGeneralException("Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
                      (" ".join(cmd), e, outdata))



def host_status_button(hostname, viewname):
    html.context_button(_("Status"), 
       "view.py?" + htmllib.urlencode_vars([
           ("view_name", viewname), 
           ("folder", g_folder[".path"]),
           ("host",     hostname),
           ("site",     "")]), 
           "status")  # TODO: support for distributed WATO

def folder_status_button(viewname = "allhosts"):
    html.context_button(_("Status"), 
       "view.py?" + htmllib.urlencode_vars([
           ("view_name", viewname), 
           ("folder", g_folder[".path"])]), 
           "status")  # TODO: support for distributed WATO




def folder_dir(the_folder):
    return root_dir + the_folder[".path"]

#   +----------------------------------------------------------------------+
#   |          _                    _    ______                            |
#   |         | |    ___   __ _  __| |  / / ___|  __ ___   _____           |
#   |         | |   / _ \ / _` |/ _` | / /\___ \ / _` \ \ / / _ \          |
#   |         | |__| (_) | (_| | (_| |/ /  ___) | (_| |\ V /  __/          |
#   |         |_____\___/ \__,_|\__,_/_/  |____/ \__,_| \_/ \___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Helper functions for loading and saving folder and hosts data.       |
#   | Hosts are loaded separately from the folders. This is for perfor-    |
#   | mance reasons. In most cases information about the hosts is needed   |
#   | only for the current folder. Keep in mind: WATO is designed for      |
#   | handling 100k hosts.                                                 |
#   +----------------------------------------------------------------------+

# Save one folder (i.e. make sure the directory exist and write its .wato file)
def save_folder(folder):
    # Remove temporary entries from the dictionary
    cleaned = dict([(k, v) for (k, v) in folder.iteritems() if not k.startswith('.') ])

    # Create the directory with the correct permissions (in case it doesn't exist)
    dir = folder_dir(folder)
    make_nagios_directory(dir)

    wato_filename = dir + "/.wato"
    config.write_settings_file(wato_filename, cleaned)

def save_folder_and_hosts(folder):
    save_folder(folder)
    save_hosts(folder)


# Save a folder and all of its subfolders (recursively)
def save_folders(folder):
    save_folder(folder)
    for subfolder in folder[".folders"].values():
        save_folders(subfolder)


def save_all_folders():
    save_folders(g_root_folder)

# Load the meta-data of a folder (it's .wato file), register
# it in g_folders, load recursively all subfolders and then
# return the folder object. The case the .wato file is missing 
# it will be assume to contain default values.
def load_folder(dir, name="", path=""):
    fn = dir + "/.wato"
    try:
        folder = eval(file(fn).read())
    except:
        # .wato missing or invalid
        folder = { 
            "roles"     : [ "admin" ], 
            "title"     : name and name or _("Main directory"),
            "num_hosts" : 0,
        }

    folder[".name"]    = name
    folder[".path"]    = path
    folder[".folders"] = {}

    # Now look subdirectories
    for entry in os.listdir(dir):
        if entry[0] == '.': # entries '.' and '..'
            continue

        p = dir + "/" + entry

        if os.path.isdir(p):
            if path == "":
                subpath = entry
            else:
                subpath = path + "/" + entry
            f = load_folder(p, entry, subpath)
            f[".parent"] = folder
            folder[".folders"][entry] = f
    
    g_folders[path] = folder
    return folder

# Load the information about all folders - except the hosts
def load_all_folders():
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    global g_root_folder, g_folders
    g_folders = {}
    g_root_folder = load_folder(root_dir)


# ----------------------------------


# Find the folder by its path. 
def find_folder(path, in_folder = None):
    if in_folder == None:
        in_folder = g_root_folder

    if len(path) == 0:
        return in_folder
    else:
        parts = path.split("/", 1)
        name = parts[0]
        if name in in_folder[".folders"]:
            if len(parts) == 1:
                return in_folder[".folders"][name]
            else:
                return find_folder(parts[1], in_folder[".folders"][name])
        else:
            return None


def find_host(host):
    return find_host_in(host, g_root_folder)

def find_host_in(host, folder):
    for f in folder.get(".files", {}).values():
        hosts = load_hosts_file(folder, f)
        if host in hosts:
            return f[".path"]

    for f in folder.get(".folders", {}).values():
        p = find_host_in(host, f)
        if p != None:
            return p

def num_hosts_in(folder, recurse):
    if not "num_hosts" in folder:
        load_hosts(folder)
        save_folder_info(folder)

    if not recurse:
        return folder["num_hosts"]

    num = 0
    for subfolder in folder[".folders"]:
        num += num_hosts_in(subfolder, True)
    num += folder["num_hosts"]
    return num


# Load all hosts from all configuration files.
def load_all_hosts(base_folder = None):
    if base_folder == None:
        base_folder = g_root_folder
    hosts = {}
    for f in base_folder[".files"].values():
        hosts.update(load_hosts_file(base_folder, f))
    for f in base_folder[".folders"].values():
        hosts.update(load_all_hosts(f))
    return hosts

def load_hosts(folder):
    if ".hosts" not in folder:
        folder[".hosts"] = load_hosts_file(folder)
        folder["num_hosts"] = len(folder[".hosts"])


def load_hosts_file(folder):
    hosts = {}

    filename = root_dir + folder[".path"] + "/hosts.mk"
    if os.path.exists(filename):
        variables = {
            "ALL_HOSTS"          : ['@all'],
            "all_hosts"          : [],
            "ipaddresses"        : {},
            "extra_host_conf"    : { "alias" : [] },
            "extra_service_conf" : { "_WATO" : [] },
            "host_attributes"    : {},
        }
        execfile(filename, variables, variables)
        for h in variables["all_hosts"]:

            parts = h.split('|')
            hostname = parts[0]

            # Get generic attributes of that host
            host = variables["host_attributes"].get(hostname)
            if host == None: # Legacy file: reconstruct values
                host = {}
                # Some of the attributes are handled with special care. We do not 
                # want them to be redundant in the configuration file. We 
                # want to stay compatible with check_mk.
                ipaddress = variables["ipaddresses"].get(hostname)
                aliases = host_extra_conf(hostname, variables["extra_host_conf"]["alias"]) 
                if len(aliases) > 0:
                    alias = aliases[0]
                else:
                    alias = None
                host["alias"]     = alias 
                host["ipaddress"] = ipaddress

                # Retrieve setting for each individual host tag
                tags = set([ tag for tag in parts[1:] if tag != 'wato' and not tag.endswith('.mk') ])
                for attr, topic in host_attributes:
                    if isinstance(attr, HostTagAttribute):
                        tagvalue = attr.get_tag_value(tags)
                        host[attr.name()] = tagvalue
            hosts[hostname]   = host


    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))
    return hosts


def rewrite_config_files_below(folder):
    for fo in folder[".folders"].values():
        rewrite_config_files_below(fo)
    rewrite_config_file(folder)

def rewrite_config_file(folder):
    load_hosts(folder)
    save_hosts(folder)


def save_hosts(folder):
    folder_path = folder[".path"]
    dirname = root_dir + folder_path
    filename = dirname + "/hosts.mk"
    hosts = folder.get(".hosts", [])
    if len(hosts) == 0:
        if os.path.exists(filename):
            os.remove(filename)
        return

    all_hosts = []
    ipaddresses = {}
    aliases = []
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        host = hosts[hostname]
        effective = effective_attributes(host, folder)

        # Make special handling of attributes configured in a special way 
        # in check_mk
        alias     = effective.get("alias")
        ipaddress = effective.get("ipaddress")

        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag.
        tags = set([])
        for attr, topic in host_attributes:
            if isinstance(attr, HostTagAttribute):
                value = effective.get(attr.name())
                tags.update(attr.get_tag_list(value))

        if alias:
            aliases.append((alias, [hostname]))
        all_hosts.append("|".join([hostname] + list(tags) + [ folder_path, 'wato' ]))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    out = file(filename, "w")
    out.write("# Written by Check_MK Webconf\n# encoding: utf-8\n\n")
    if len(all_hosts) > 0:
        out.write("all_hosts += ")
        out.write(pprint.pformat(all_hosts))
        if len(aliases) > 0:
            out.write("\n\nif 'alias' not in extra_host_conf:\n"
                    "    extra_host_conf['alias'] = []\n")
            out.write("\nextra_host_conf['alias'] += ")
            out.write(pprint.pformat(aliases))
        if len(ipaddresses) > 0:
            out.write("\n\nipaddresses.update(")
            out.write(pprint.pformat(ipaddresses))
            out.write(")")
        out.write("\n")

    # all WATO information to Check_MK's inventory checks (needed for link in Multisite)
    out.write("\n\nif '_WATO' not in extra_service_conf:\n"
            "    extra_service_conf['_WATO'] = []\n")
    out.write("\nextra_service_conf['_WATO'] += [ \n"
              "  ('%s', [ 'wato', '%s' ], ALL_HOSTS, [ 'Check_MK inventory' ] ) ]\n" % 
              (folder_path, folder_path))

    # Add custom macros for attributes that are to be present in Nagios
    custom_macros = {}
    for hostname, host in hosts.items():
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attrname in effective:
                value = effective.get(attrname)
                nagstring = attr.to_nagios(value)
                if nagstring != None:
                    if attrname not in custom_macros:
                        custom_macros[attrname] = {}
                    custom_macros[attrname][hostname] = nagstring
    for attrname, entries in custom_macros.items():
        macrolist = []
        for hostname, nagstring in entries.items():
            macrolist.append((nagstring, [hostname]))
        if len(macrolist) > 0:
            out.write("\n# %s\n" % host_attribute[attrname].title())
            out.write("if '_%s' not in extra_host_conf:\n" % attrname.upper())
            out.write("    extra_host_conf['_%s'] = []\n" % attrname.upper())
            out.write("extra_host_conf['_%s'] += \\\n%s\n" % (attrname.upper(), pprint.pformat(macrolist)))

    # Write information about all host attributes into special variable - even
    # values stored for check_mk as well.
    out.write("\n# Host attributes (needed for WATO)\n")
    out.write("host_attributes.update(%s)\n" % pprint.pformat(hosts))


def delete_configuration_file(folder, thefile):
    path = folder_dir(folder, thefile)
    if os.path.exists(path):
        os.remove(path) # remove the actual configuration file
    if os.path.exists(path + ".wato"):
        os.remove(path + ".wato") # remove the .wato file


# This is a dummy implementation which works without tags
# and implements only a special case of Check_MK's real logic.
def host_extra_conf(hostname, conflist):
    for value, hostlist in conflist:
        if hostname in hostlist:
            return [value]
    return []

def set_current_folder():
    global g_folder

    if html.has_var("folder"):
        path = html.var("folder")
    else:
        host = html.var("host")
        if host: # find host with full scan. Expensive operation
            path = find_host(host)
            if not path:
                raise MKGeneralException(_("The host <b>%s</b> is not managed by WATO.") % host)
        else: # fall back to root folder
            path = ""

    g_folder = find_folder(path)
    html.set_var("folder", path) # in case of implizit folder selection
    if not g_folder:
        raise MKGeneralException(_('You called this page with a non-existing folder! '
                                 'Go back to the <a href="wato.py">main index</a>.'))


def make_path(filename):
    if not filename or filename == "/":
        return ()
    parts = filename.strip("/").split("/")
    return tuple(parts)

# Create link keeping the context to the current folder / file
def make_link(vars):
    vars = vars + [ ("folder", g_folder[".path"]) ]
    return html.makeuri_contextless(vars)

# Small helper for creating a link with a context to a given folder
def make_link_to(vars, folder):
    vars = vars + [ ("folder", folder[".path"]) ]
    return html.makeuri_contextless(vars)

def make_action_link(vars):
    return make_link(vars + [("_transid", html.current_transid())])

def search_button():
    html.context_button(_("Search"), make_link([("mode", "search")]), "search")

def changelog_button():
    pending = parse_audit_log("pending")
    buttontext = _("ChangeLog")
    if len(pending) > 0:
        buttontext = "<b>%s (%d)</b>" % (buttontext, len(pending))
        hot = True
    else:
        hot = False
    html.context_button(buttontext, make_link([("mode", "changelog")]), "wato_changes", hot)


def show_service_table(hostname, firsttime):
    # Read current check configuration
    cache_options = not html.var("_scan") and [ '--cache' ] or []
    try:
        table = check_mk_automation("try-inventory", cache_options + [hostname])
    except Exception, e:
        html.show_error("Inventory failed for this host: %s" % e)
        return

    table.sort()

    html.begin_form("checks", None, "POST")
    fixall = 0
    for entry in table:
        if entry[0] == 'new' and not html.has_var("_activate_all") and not firsttime:
            html.button("_activate_all", _("Activate missing"))
            fixall += 1
            break
    for entry in table:
        if entry[0] in [ 'obsolete', 'vanished', ]:
            html.button("_cleanup", _("Remove exceeding"))
            fixall += 1
            break
    if fixall == 2:
        html.button("_fixall", _("Fix all missing/exceeding"))

    if len(table) > 0:
        html.button("_save", _("Save manual check configuration"))

    html.hidden_fields()
    if html.var("_scan"):
        html.hidden_field("_scan", "on")

    html.write("<table class=data>\n")

    for state_name, state_type, checkbox in [ 
        ( _("Available (missing) services"), "new", firsttime ),
        ( _("Already configured services"), "old", True, ),
        ( _("Obsolete services (being checked, but should be ignored)"), "obsolete", True ),
        ( _("Ignored services (configured away by admin)"), "ignored", False ),
        ( _("Vanished services (checked, but no longer exist)"), "vanished", True ),
        ( _("Manual services (defined in main.mk)"), "manual", None ),
        ( _("Legacy services (defined in main.mk)"), "legacy", None )
        ]:
        first = True
        trclass = "even"
        for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
            if state_type != st:
                continue
            if first:
                html.write('<tr class=groupheader><td colspan=7><br>%s</td></tr>\n' % state_name)
                html.write("<tr><th>" + _("Status") + "</th><th>" + _("Checktype") + "</th><th>" + _("Item") + "</th>"
                           "<th>" + _("Service Description") + "</th><th>" + _("Current check") + "</th><th></th></tr>\n")
                first = False
            trclass = trclass == "even" and "odd" or "even"
            statename = nagios_short_state_names.get(state, "PEND")
            if statename == "PEND":
                stateclass = "state svcstate statep"
                state = 0 # for tr class
            else:
                stateclass = "state svcstate state%s" % state
            html.write("<tr class=\"data %s%d\"><td class=\"%s\">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>" %
                    (trclass, state, stateclass, statename, ct, item, descr, output))
            if checkbox != None:
                varname = "_%s_%s" % (ct, item)
                html.checkbox(varname, checkbox)
            html.write("</td></tr>\n")
    html.write("</table>\n")
    html.end_form()


def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        del g_folder[".hosts"][delname]
        g_file["num_hosts"] -= 1
        save_current_folder()
        log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        check_mk_automation("delete-host", [delname])
        call_hook_hosts_changed(g_file)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_hosts_after_confirm(hosts):
    c = wato_confirm(_("Confirm deletion of %d hosts") % len(hosts),
                     _("Do you really want to delete the %d selected hosts?") % len(hosts))
    if c:
        for delname in hosts:
            del g_folder[".hosts"][delname]
            g_file["num_hosts"] -= 1
            check_mk_automation("delete-host", [delname])
            log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        save_current_folder()
        call_hook_hosts_changed(g_file)
        return "folder", _("Successfully deleted %d hosts") % len(hosts)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_folder_after_confirm(del_folder):
    msg = _("Do you really want to delete the folder %s?") % del_folder["title"]
    if not config.wato_hide_filenames:
        msg += "<br>" + _("(The directory <tt>%s</tt>)") % folder_dir(del_folder)
    c = wato_confirm(_("Confirm folder deletion"), msg)
                     
    if c:
        del g_folder[".folders"][del_folder[".name"]]
        folder_path = folder_dir(del_folder)
        try:
            os.remove(folder_path + "/.wato")
            os.rmdir(folder_path)
        except:
            pass
        if os.path.exists(folder_path):
            raise MKGeneralException(_("Cannot remove the folder '%s': probably there are "
                                       "still non-WATO files contained in this directory.") % folder_path)

        save_folder_config()
        log_audit(folder_dir(del_folder), "delete-folder", _("Deleted empty folder %s")% folder_dir(del_folder))
        call_hook_folder_deleted(del_folder)
        html.reload_sidebar() # refresh WATO snapin
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 


def delete_file_after_confirm(del_file):
    c = wato_confirm(_("Confirm file deletion"),
                     _("Do you really want to delete the host list <b>%s</b>, "
                       "which is containing %d hosts?") 
                     % (del_file["title"], del_file["num_hosts"]))
    if c:
        hosts = load_hosts_file(g_folder, del_file)
        for delname in hosts:
            check_mk_automation("delete-host", [delname])
        if len(hosts) > 0:
            log_pending(del_file, "delete-file", _("Deleted file %s") % del_file["title"])
        else:
            log_audit(del_file, "delete-file", _("Deleted empty file %s") % del_file["title"])
        del g_files[del_file[".path"]]
        del g_folder[".files"][del_file[".name"]]
        delete_configuration_file(g_folder, del_file)
        save_folder_config()
        call_hook_file_or_folder_deleted('file', del_file)
        call_hook_hosts_changed(g_folder)
        # refresh WATO snapin
        html.reload_sidebar()
        global g_file
        g_file = None
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.var("filled_in") == "confirm":
        wato_html_head(html_title)
    return html.confirm(message)

g_html_head_open = False

def wato_html_head(title):
    global g_html_head_open
    g_html_head_open = True
    html.header(title)
    html.write("<div class=wato>\n")

def host_move_combo(host = None, top = False):
    other_folders = []
    for path, afolder in g_folders.items():
        if config.role in afolder["roles"] and afolder != g_folder:
            os_path = afolder[".path"]
            msg = afolder["title"]
            if os_path:
                msg += " (%s)" % os_path
            other_folders.append((os_path, msg))

    if len(other_folders) > 0:
        selections = [("@", _("(select folder)"))] + other_folders
        if host == None:
            html.button("_bulk_move", _("Move To:"))
            field_name = 'bulk_moveto'
            if top:
                field_name = '_top_bulk_moveto'
                if html.has_var('bulk_moveto'):
                    html.javascript('update_bulk_moveto("%s")' % html.var('bulk_moveto', ''))
            html.select(field_name, selections, "",
                        onchange = "update_bulk_moveto(this.value)",
                        attrs = {'class': 'bulk_moveto'})
        else:
            html.hidden_field("host", host)
            uri = html.makeuri([("host", host), ("_transid", html.current_transid() )])
            html.sorted_select("host_move_%s" % host, selections, "@", 
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri);


def move_hosts_to(hostnames, path):
    if path not in g_folders: # non-existing folder
        return

    target_folder = g_folders[path]
    if target_folder == g_folder:
        return # target and source are the same

    if config.role not in target_folder["roles"]:
        raise MKAuthException(_("You have no change permissions on the target folder"))

    # read hosts currently in target file
    load_hosts(target_folder)
    target_hosts = target_folder[".hosts"]

    num_moved = 0
    for hostname in hostnames:
        if hostname not in g_folder[".hosts"]: # non-existant host
            continue

        target_hosts[hostname] = g_folder[".hosts"][hostname]
        target_folder["num_hosts"] += 1
        g_folder["num_hosts"] -= 1
        del g_folder[".hosts"][hostname]
        if len(hostnames) == 1:
            log_pending(hostname, "move-host", _("Moved host from %s to %s") %
                (g_folder[".path"], target_folder[".path"]))
        num_moved += 1

    save_folder_and_hosts(target_folder)
    save_folder_and_hosts(g_folder)
    call_hook_hosts_changed(g_root_folder)
    if len(hostnames) > 1:
        log_pending(target_file, "move-host", _("Moved %d hosts from %s to %s") %
            (num_moved, g_folder[".path"], target_folder[".path"]))
    return num_moved 
        

def move_host_to(hostname, target_filename):
    move_hosts_to([hostname], target_filename)

def render_folder_path(the_folder = 0, link_to_last = False):

    if the_folder == 0:
        the_folder = g_folder

    def render_component(path, title):
        return '<a href="%s">%s</a>' % (
               html.makeuri_contextless([("folder", path)]), title)

    comps = []
    folder_path = the_folder[".path"]
    if folder_path == "": # root folder
        parts = [ "" ]
    elif '/' not in folder_path:
        parts = [ "", folder_path ] # first directory level
    else:
        parts = [ "" ] + folder_path.split("/")

    path = ""
    for p in parts[:-1]:
        comps.append(render_component(path, find_folder(path)["title"]))
        if path == "":
            path = p
        else:
            path = path + "/" + p

    if link_to_last:
        comps.append(render_component(the_folder[".path"], the_folder["title"]))
    else:
        comps.append("<b>" + the_folder["title"] + "</b>")

    html.write("<div class=folderpath>%s</div>\n" % " / ".join(comps))

#   +----------------------------------------------------------------------+
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
#   +----------------------------------------------------------------------+

def interactive_progress(items, title, stats, finishvars, timewait, success_stats = [], termvars = []):
    if not termvars:
        termvars = finishvars;
    html.write("<center>")
    html.write("<table class=progress>")
    html.write("<tr><th colspan=2>%s</th></tr>" % title)
    html.write("<tr><td colspan=2 class=log><div id=progress_log></div></td></tr>")
    html.write("<tr><td colspan=2 class=bar>")
    html.write("  <table id=progress_bar><tbody><tr><td class=left></td>"
               "<td class=right></td></tr></tbody></table>")
    html.write("  <div id=progress_title></div>")
    html.write("  <img class=glass src=images/perfometer-bg.png />")
    html.write("</td></tr>")
    html.write("<tr><td class=stats>")
    html.write("  <table>")
    for num, (label, value) in enumerate(stats):
        html.write("    <tr><th>%s</th><td id='progress_stat%d'>%d</td></tr>" % (label, num, value))
    html.write("  </table>")
    html.write("</td>")
    html.write("<td class=buttons>")
    html.jsbutton('progress_pause',    _('Pause'),   'javascript:progress_pause()')
    html.jsbutton('progress_proceed',  _('Proceed'), 'javascript:progress_proceed()',  'display:none')
    html.jsbutton('progress_finished', _('Finish'),  'javascript:progress_end()', 'display:none')
    html.jsbutton('progress_retry',    _('Retry Failed Hosts'), 'javascript:progress_retry()', 'display:none')
    html.jsbutton('progress_restart',  _('Restart'), 'javascript:location.reload()')
    html.jsbutton('progress_abort',    _('Abort'),   'javascript:progress_end()')
    html.write("</td></tr>")
    html.write("</table>")
    html.write("</center>")
    json_items    = '[ %s ]' % ','.join([ "'" + h + "'" for h in items ])
    success_stats = '[ %s ]' % ','.join(map(str, success_stats))
    # Remove all sel_* variables. We do not need them for our ajax-calls.
    # They are just needed for the Abort/Finish links. Those must be converted
    # to POST.
    base_url = html.makeuri([], remove_prefix = "sel_")
    html.javascript(('progress_scheduler("%s", "%s", 50, %s, "%s", %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json_items, html.makeuri(finishvars), success_stats, html.makeuri(termvars),))

#   +----------------------------------------------------------------------+
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Attributes of hosts are based on objects and are extendable via      |
#   | WATO plugins.                                                        |
#   +----------------------------------------------------------------------+
class Attribute:
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self, name=None, title=None, help=None, default_value=None):
        self._name = name
        self._title = title
        self._help = help
        self._default_value = default_value

    # Return the name (= identifier) of the attribute
    def name(self):
        return self._name

    # Return the title to be displayed to the user
    def title(self):
        return self._title

    # Return an optional help text
    def help(self):
        return self._help

    # Return the default value for new hosts
    def default_value(self):
        return self._default_value

    # Render HTML code displaying a value
    def paint(self, value, hostname):
        return "", value

    # Wether or not to show this attribute in tables.
    # This value is set by declare_host_attribute
    def show_in_table(self):
        return self._show_in_table
        
    # Wether or not to show this attribute in the edit form.
    # This value is set by declare_host_attribute
    def show_in_form(self):
        return self._show_in_form

    # Wether or not to make this attribute configurable in
    # files and folders (as defaule value for the hosts)
    def show_in_folder(self):
        return self._show_in_folder

    # Wether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory 
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Render HTML input fields displaying the value and 
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, value):
        pass

    # Create value from HTML variables.     
    def from_html_vars(self):
        return None
    
    # Check if the value entered by the user is valid.
    # This method may raise MKUserError in case of invalid user input.
    def validate_input(self):
        pass

    # If this attribute should be present in Nagios as 
    # a host custom macro, then the value of that macro
    # should be returned here - otherwise None
    def to_nagios(self, value):
        return None

    # Checks if the give value matches the search attributes
    # that are represented by the current HTML variables.
    def filter_matches(self, crit, value, hostname):
        return crit == value


# A simple text attribute. It is stored in 
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self, name, title, help = None, default_value="", mandatory = False):
        Attribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory

    def paint(self, value, hostname):
        if not value:
            return "", ""
        else:
            return "", value

    def is_mandatory(self):
        return self._mandatory

    def render_input(self, value):
        if value == None: 
            value = ""
        html.text_input("attr_" + self.name(), value)

    def from_html_vars(self):
        value = html.var_utf8("attr_" + self.name())
        if value == None:
            value = ""
        return value

    def validate_input(self):
        value = self.from_html_vars()
        if self._mandatory and not value:
            raise MKUserError("attr_" + self.name(), 
                  _("Please specify a value for %s") % self.title())

    def filter_matches(self, crit, value, hostname):
        if value == None:  # Host does not have this attribute
            value = ""
        return crit.lower() in value.lower() 

# A simple text attribute that is not editable by the user.
# It can be used to store context information from other
# systems (e.g. during an import of a host database from
# another system).
class FixedTextAttribute(TextAttribute): 
    def __init__(self, name, title, help = None):
        TextAttribute.__init__(self, name, title, help, None)
        self._mandatory = False

    def render_input(self, value):
        if value != None:
            html.hidden_field("attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self):
        return html.var("attr_" + self.name())




class IPAddressAttribute(TextAttribute):
    def __init__(self, name, title, help = None, mandatory = False, dnslookup = False):
        TextAttribute.__init__(self, name, title, help, "", mandatory = mandatory)
        self._dnslookup = dnslookup

    def render_input(self, value):
        if value == None:
            value = ""
        html.text_input("attr_" + self.name(), value, size=15)

    def from_html_vars(self):
        value = html.var("attr_" + self.name())
        if not value:
            value = None
        return value

    def do_dns(self, hostname):
        try:
            ip = socket.gethostbyname(hostname)
            text = "%s&nbsp;(DNS)" % ip
            tdclass = 'dns'
        except:
            ip = None
            text = _("(hostname not resolvable!)")
            tdclass = 'dnserror'
        return ip, tdclass, text
    
    def paint(self, value, hostname):
        if value == None:
            ip, tdclass, text = self.do_dns(hostname)
            return tdclass, text
        else:
            return "", value

    def validate_input(self):
        value = self.from_html_vars()
        if not value and self._dnslookup: # empty -> use DNS
            hostname = html.var("host")
            ip, text, tdclass = self.do_dns(hostname)
            if not ip:
                raise MKUserError("attr_" + self.name(), _("Hostname <b><tt>%s</tt></b> cannot be resolved into an IP address. "
                            "Please check hostname or specify an explicit IP address.") % hostname)

    # On IP-Addresses we always do a prefix-match. We also remove any "*"
    # that the user accidentally adds
    def filter_matches(self, crit, value, hostname):
        if not crit:
            return True

        if not value: # do DNS lookup
            value, tdclass, text = self.do_dns(hostname)
            if not value:
                return False

        return value.lower().startswith(crit.lower().strip("*"))

# Helper function for checking if an ip address is valid
def is_valid_ip_address(ip):
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            raise Exception()
        for x in parts:
            if int(x) < 0 or int(x) > 255:
                raise Exception()
    except:
        return False
    return True

# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self, name, title, help = None, default_value="", mandatory = False):
        TextAttribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory

    def to_nagios(self, value):
        return value.encode("utf-8")

# An attribute for selecting one item out of list using
# a drop down box (<select>). Enumlist is a list of
# pairs of keyword / title. The type of value is string.
# In all cases where no value is defined or the value is
# not in the enumlist, the default value is being used.
class EnumAttribute(Attribute):
    def __init__(self, name, title, help, default_value, enumlist):
        Attribute.__init__(self, name, title, help, default_value)
        self._enumlist = enumlist
        self._enumdict = dict(enumlist)

    def paint(self, value, hostname):
        return "", self._enumdict.get(value, self.default_value())

    def render_input(self, value):
        html.select("attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self):
        return html.var("attr_" + self.name(), self.default_value())


# A selection dropdown for a host tag
class HostTagAttribute(Attribute):
    def __init__(self, nr, tag_definition):
        # In newer days, the tag defitions contain a third
        # element: the id of the tag group - written at the
        # beginning of the tuple. If that is present, we use
        # it as id, otherwise we use the number.
        if len(tag_definition) >= 3:
            name = "tag_" + tag_definition[0]
            tag_definition = tag_definition[1:]
        else:
            name = "tag_%d" % nr

        title, self._taglist = tag_definition 
        Attribute.__init__(self, name, title, "", self._taglist[0][0])

    def paint(self, value, hostname):
        for entry in self._taglist:
            if value == entry[0]:
                return "", entry[1]
        return "", "" # Should never happen, at least one entry should match
                      # But case could occur if tags definitions have been changed.

    def render_input(self, value):
        choices = [e[:2] for e in self._taglist]
        html.select("attr_" + self.name(), choices, value)

    def from_html_vars(self):
        value = html.var("attr_" + self.name())
        if not value:
            value = None
        return value
    

    # Special function for computing the setting of a specific
    # tag group from the total list of tags of a host
    def get_tag_value(self, tags):
        for entry in self._taglist:
            if entry[0] in tags:
                return entry[0]
        return None

    # Return list of host tags to set (handles
    # secondary tags)
    def get_tag_list(self, value):
        for entry in self._taglist:
            if entry[0] == value:
                if len(entry) >= 3:
                    taglist = [ value ] + entry[2]
                else:
                    taglist =  [ value ]
                if taglist[0] == None:
                    taglist = taglist[1:]
                return taglist
        return [] # No matching tag


# Declare an attribute for each host tag configured in multisite.mk
# Also make sure that the tags are reconfigured as soon as the
# configuration of the tags has changed.
configured_host_tags = None
def declare_host_tag_attributes():
    global configured_host_tags
    global host_attributes

    if configured_host_tags != config.host_tags:
        # Remove host tag attributes from list, if existing
        host_attributes = [ (attr, topic) for (attr, topic) in host_attributes if not attr.name().startswith("tag_") ]

        # Also remove those attributes from the speed-up dictionary host_attribute
        for attr in host_attribute.values():
            if attr.name().startswith("tag_"):
                del host_attribute[attr.name()]

        for num, entry in enumerate(config.host_tags):
            declare_host_attribute(HostTagAttribute(num + 1, entry), show_in_table = False, show_in_folder = True, topic = _("Host tags"))

        configured_host_tags = config.host_tags


# Global datastructure holding all attributes (in a defined order)
# as pairs of (attr, topic). Topic is the title under which the 
# attribute is being displayed. All builtin attributes use the
# topic None. As long as only one topic is used, no topics will
# be displayed. They are useful if you have a great number of 
# custom attributes.
host_attributes = []

# Dictionary for quick access
host_attribute = {}

# Declare attributes with this method
def declare_host_attribute(a, show_in_table = True, show_in_folder = True, topic = None, show_in_form = True):
    host_attributes.append((a, topic))
    host_attribute[a.name()] = a
    a._show_in_table  = show_in_table
    a._show_in_folder = show_in_folder
    a._show_in_form   = show_in_form

# Read attributes from HTML variables
def collect_attributes(do_validate = True):
    host = {}
    for attr, topic in host_attributes:
        attrname = attr.name()
        if not html.var("_change_%s" % attrname, False):
            continue

        if do_validate:
            attr.validate_input()
        host[attrname] = attr.from_html_vars()
    return host

def have_folder_attributes():
    for attr, topic in host_attributes:
        if attr.show_in_folder():
            return True
    return False

# Show HTML form for editing attributes. for_what can be:
# "host"   -> normal host edit dialog
# "folder" -> properies of folder or file
# "search" -> search dialog
# "bulk"   -> bulk change
# parent: The parent folder of the objects to configure
# myself: For mode "folder" the folder itself
def configure_attributes(hosts, for_what, parent, myself=None, without_attributes = []):
    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    topics = []
    for attr, topic in host_attributes:
        if topic not in topics and attr.show_in_form():
            topics.append(topic)

    for topic in topics:
        if len(topics) > 1:
            if topic == None:
                title = _("Basic settings")
            else:
                title = topic
            if topic == topics[0]:
                html.write("</table>")
            # html.write("<tr><td colspan=3 class=buttons>")
            html.begin_foldable_container("wato_attributes", title, 
                                          topic == None, title, indent = False)
            html.write("<table class=form>")

        for attr, atopic in host_attributes:
            if atopic != topic:
                continue
            attrname = attr.name()
            if attrname in without_attributes:
                continue # e.g. needed to skip ipaddress in CSV-Import

            # Skip hidden attributes
            if not attr.show_in_form():
                continue

            # In folder not all attributes are shown
            if for_what == "folder" and not attr.show_in_folder():
                continue

            # "bulk": determine, if this attribute has the same setting for all hosts.
            values = []
            num_haveit = 0
            for hostname, host in hosts.items():
                if attrname in host:
                    num_haveit += 1
                    if host[attrname] not in values:
                        values.append(host[attrname])

            # The value of this attribute is unique amongst all hosts if
            # either no host has a value for this attribute, or all have
            # one and have the same value
            unique = num_haveit == 0 or (len(values) == 1 and num_haveit == len(hosts))

            if for_what in [ "host", "folder" ]:
                host = hosts.values()[0]

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "search" mode. 
            inherited_from = None
            inherited_value = None
            has_inherited = False

            if for_what == "host":
                url = make_link_to([("mode", "editfolder")], g_folder)

            container = parent
            while container:
                if attrname in container.get("attributes", {}):
                    url = make_link_to([("mode", "editfolder")], container)
                    inherited_from = _("Inherited from ") + '<a href="%s">%s</a>' % (url, container["title"])
                    inherited_value = container["attributes"][attrname]
                    has_inherited = True
                    break

                container = container.get(".parent")
                what = "folder"

            if not container: # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
                inherited_value = attr.default_value()

            # Legend and Help
            html.write("<tr><td class=legend><h3>%s</h3>" % attr.title())
            if attr.help():
                html.write("<i>%s</i>" % attr.help())
            html.write("</td>")

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

            checkbox_name = "_change_%s" % attrname
            cb = html.get_checkbox(checkbox_name)
            force_entry = False

            # first handle mandatory cases
            if for_what == "folder" and attr.is_mandatory() \
                and myself \
                and some_host_hasnt_set(myself, attrname) \
                and not has_inherited:
                force_entry = True
                active = True
            elif for_what == "host" and attr.is_mandatory() and not has_inherited:
                    force_entry = True
                    active = True
            elif cb != None:
                active = cb # get previous state of checkbox
            elif for_what == "search":
                active = attr.default_value() == "" # show empty text search fields always
            elif for_what == "bulk":
                active = unique and len(values) > 0
            elif for_what == "folder":
                active = attrname in host
            else: # "host"
                active = attrname in host

            html.write('<td class=checkbox>')
            if force_entry:
                html.write("<input type=checkbox name=\"ignored_%s\" CHECKED DISABLED></div>" % checkbox_name)
                html.hidden_field(checkbox_name, "on")
            else:
                html.checkbox(checkbox_name, active, 
                    onclick = "wato_toggle_attribute(this, '%s');" % attrname ) # Only select if value is unique
            html.write("</td>")

            # Now comes the input fields and the inherited / default values
            # as two DIV elements, one of which is visible at one time.
            html.write('<td class=content>')

            # DIV with the input elements
            html.write('<div id="attr_entry_%s" style="%s">' 
              % (attrname, (not active) and "display: none" or ""))
            if len(values) == 1:
                defvalue = values[0]
            else:
                defvalue = attr.default_value()
            attr.render_input(defvalue)
            html.write("</div>")

            # DIV with actual / inherited / default value
            html.write('<div class="inherited" id="attr_default_%s" style="%s">' 
              % (attrname, active and "display: none" or ""))

            # in bulk mode we show inheritance only if *all* hosts inherit
            if for_what == "bulk":
                if num_haveit == 0:
                    html.write("<h3>" + inherited_from + "</h3>")
                    value = inherited_value
                elif not unique:
                    html.write(_("<i>This value differs between the selected hosts.</i>")) 
                else:
                    value = values[0]

            elif for_what in [ "host", "folder" ]:
                html.write("<h3>" + inherited_from + "</h3>")
                value = inherited_value

            if for_what != "search" and not (for_what == "bulk" and not unique):
                tdclass, content = attr.paint(value, "")
                if not content:
                    content = "<i>" + _("(empty)") + "</i>"
                html.write(content)

            html.write("</div>")
            
            html.write("</td></tr>\n")

        if len(topics) > 1:
            html.write("</table>")
            html.end_foldable_container()
            if topic == topics[-1]:
                html.write("<table class=form>")


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder[".folders"].values():
        if some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    load_hosts(folder) # make sure hosts are loaded
    for host in folder[".hosts"].values():
        if attrname not in host:
            return True

    return False

# Compute effective (explicit and inherited) attributes
# for a host. This returns a dictionary with a value for
# each host attribute
def effective_attributes(host, folder):
    chain = [ host ]
    while folder:
        chain.append(folder.get("attributes", {}))
        folder = folder.get(".parent")

    eff = {}
    for a in chain[::-1]:
        eff.update(a)

    # now add default values of attributes for all missing values
    for attr, topic in host_attributes:
        attrname = attr.name()
        if attrname not in eff:
            eff.setdefault(attrname, attr.default_value())

    return eff
    


#   +----------------------------------------------------------------------+
#   |       _   _             _           ___        _    ____ ___         |
#   |      | | | | ___   ___ | | _____   ( _ )      / \  |  _ \_ _|        |
#   |      | |_| |/ _ \ / _ \| |/ / __|  / _ \/\   / _ \ | |_) | |         |
#   |      |  _  | (_) | (_) |   <\__ \ | (_>  <  / ___ \|  __/| |         |
#   |      |_| |_|\___/ \___/|_|\_\___/  \___/\/ /_/   \_\_|  |___|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The API allows addons to query information about configured hosts.   |
#   |                                                                      |
#   | Hooks are a way how addons can add own activities at certain points  |
#   | of time, e.g. when a host as been edited of the changes have been    | 
#   | activated.                                                           |
#   +----------------------------------------------------------------------+ 

# Inform plugins about changes of hosts. the_thing can be:
# a folder, a file or a host

hooks = {}

class API:
    def register_hook(self, name, func):
        hooks.setdefault(name, []).append(func)

    # Get a (flat) dictionary containing all hosts with their *effective*
    # attributes (containing all inherited and default values where appropriate).
    def get_all_hosts(self):
        load_folders()
        return collect_hosts(g_root_folder)

    # Find a folder by its tuple-path
    def get_folder(self, path):
        load_folders()
        the_thing = g_root_folder
        while len(path) > 0:
             c = path[0]
             if c in the_thing[".folders"]:
                 the_thing = the_thing[".folders"][c]
             else:
                 return None
             path = path[1:]

        # add information about hosts and their number
        load_hosts(the_thing)
        return the_thing

    # Find a file by its tuple-path and return it
    # including the hosts
    def get_file(self, path):
        folder = self.get_folder(path[:-1])
        if not folder or not path[-1] in folder[".files"]:
            return None
        the_file = folder[".files"][path[-1]]
        if not the_file:
            return None
        hosts = load_hosts_file(folder, the_file)
        new_file = {}
        new_file.update(the_file)
        new_file[".hosts"] = hosts
        return new_file

    # Find a file or folder by its tuple-path and return
    # it without loading any hosts.
    def get_filefolder(self, path):
        if len(path) == 0:
            return g_root_folder
        elif path[-1].endswith(".mk"):
            folder = self.get_folder(path[:-1])
            if not folder:
                raise MKGeneralException("No WATO folder %s." % (path,))
            if ".files" not in folder:
                raise MKGeneralException("Path %s does not point to a WATO file." % (path,))
            return folder[".files"].get(path[-1])
        else:
            return self.get_folder(path)

    # Get all effective data of a host. The_file must be returned by get_file()
    def get_host(self, the_file, hostname):
        declare_host_tag_attributes()
        host = the_file[".hosts"][hostname]
        eff = effective_attributes(host, the_file)
        eff["name"] = hostname
        return eff

    # Return displayable information about host (call with with result vom get_host())
    def get_host_painted(self, host): 
        declare_host_tag_attributes()
        result = []
        for attr, topic in host_attributes:   
            attrname = attr.name()
            if attrname in host:
                tdclass, content = attr.paint(host[attrname], host["name"])
                result.append((attr.title(), content))
        return result

    # Get information about the folder and directory tree. 
    # This is useful for components that display hosts in 
    # the tree (e.g. the status GUI).
    def get_folder_tree(self):
        load_all_folders()
        return g_root_folder

    # sort list of folders or files by their title
    def sort_by_title(self, folders):
        def folder_cmp(f1, f2):
            return cmp(f1["title"].lower(), f2["title"].lower())
        folders.sort(cmp = folder_cmp)
        return folders

    # Create an URL to a certain WATO path. Path is in string format
    def link_to_path(self, filename):
        return "wato.py?filename=" + htmllib.urlencode(filename)

    # Create an URL to the edit-properties of a host.
    def link_to_host(self, hostname):
        return "wato.py?" + htmllib.urlencode_vars(
        [("mode", "edithost"), ("host", hostname)])

    # Same, but links to services of that host
    def link_to_host_inventory(self, hostname):
        return "wato.py?" + htmllib.urlencode_vars(
        [("mode", "inventory"), ("host", hostname)])

    # Return the title of a folder - which is given as a string path
    def get_folder_title(self, filename):
        load_folders() # TODO: use in-memory-cache
        folder = self.get_filefolder(make_path(filename))
        if folder:
            return folder["title"]
        else:
            return filename

    # BELOW ARE PRIVATE HELPER FUNCTIONS



    def _cleanup_directory(self, thing):
        # drop 'parent' entry, recursively
        def drop_internal(thing):
            new_thing = {}
            new_thing.update(thing)
            if ".parent" in new_thing:
                del new_thing[".parent"]
            if ".files" in new_thing:
                new_thing[".files"] = drop_internal_dict(new_thing[".files"])
            if ".folders" in new_thing:
                new_thing[".folders"] = drop_internal_dict(new_thing[".folders"])
            return new_thing

        def drop_internal_dict(self, thingdict): 
            new_dict = {}
            for name, thing in thingdict.items():
                new_dict[name] = drop_internal(thing)
            return new_dict

        return drop_internal(thing)

api = API()



# internal helper functions for API
def collect_hosts(the_thing):
    if ".folders" in the_thing: # a folder
        hosts = {}
        for fi in the_thing.get(".files", []).values():
            hosts.update(collect_hosts(fi))
        for fo in the_thing[".folders"].values():
            hosts.update(collect_hosts(fo))
        return hosts
    else: # file
        hosts = load_hosts_file(the_thing[".parent"], the_thing)
        effective_hosts = dict([ (hn, effective_attributes(h, the_thing)) 
                               for (hn, h) in hosts.items() ])
        for host in effective_hosts.values():
            host["file"] = the_thing[".path"]
        return effective_hosts

def hook_registered(name):
    """ Returns True if at least one function is registered for the given hook """
    return hooks.get(name, []) != []

def call_hooks(name, *args):
    n = 0
    for hk in hooks.get(name, []):
        n += 1
        try:
            hk(*args)
        except Exception, e:
            import traceback, StringIO
            txt = StringIO.StringIO()
            t, v, tb = sys.exc_info()
            traceback.print_exception(t, v, tb, None, txt)
            html.show_error("<h3>" + _("Error executing hook") + " %s #%d: %s</h3><pre>%s</pre>" % (name, n, e, txt.getvalue()))

def call_hook_hosts_changed(folder):
    if "hosts-changed" in hooks:
        hosts = collect_hosts(folder)
        call_hooks("hosts-changed", hosts)

    # The same with all hosts!
    if "all-hosts-changed" in hooks:
        hosts = collect_hosts(g_root_folder)
        call_hooks("all-hosts-changed", hosts)

def call_hook_folder_created(folder):
    if 'folder-created' in hooks:
        call_hooks("folder-created", folder)

def call_hook_folder_deleted(folder):
    if 'folder-deleted' in hooks:
        call_hooks("folder-deleted", folder)

def call_hook_activate_changes():
    """
    This hook is executed when one applies the pending configuration changes
    from wato.

    But it is only excecuted when there is at least one function
    registered for this host.

    The registered hooks are called with a dictionary as parameter which
    holds all available with the hostnames as keys and the attributes of
    the hosts as values.
    """
    if hook_registered('activate-changes'):
        call_hooks("activate-changes", collect_hosts(g_root_folder))

#   +----------------------------------------------------------------------+
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Prepare plugin-datastructures and load WATO plugins                  |
#   +----------------------------------------------------------------------+


mode_functions = {
   "folder"         : mode_folder,
   "newfolder"      : lambda phase: mode_editfolder(phase, True),
   "editfolder"     : lambda phase: mode_editfolder(phase, False),
   "newhost"        : lambda phase: mode_edithost(phase, True),
   "edithost"       : lambda phase: mode_edithost(phase, False),
   "firstinventory" : lambda phase: mode_inventory(phase, True),
   "inventory"      : lambda phase: mode_inventory(phase, False),
   "search"         : mode_search,
   "bulkinventory"  : mode_bulk_inventory,
   "bulkedit"       : mode_bulk_edit,
   "bulkcleanup"    : mode_bulk_cleanup,
   "changelog"      : mode_changelog,
   "snapshot"       : mode_snapshot,
}

extra_buttons = [
]

load_web_plugins("wato", globals())
