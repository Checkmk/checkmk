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

import sys, pprint, socket, re, subprocess, time
from lib import *
import htmllib

config.declare_permission("use_wato",
     _("Use WATO"),
     _("This permissions allows users to use WATO - Check_MK's Web Administration Tool.<br>"
     "Please make sure, that they also have the permission for the WATO snapin."),
     [ "admin", "user" ])

conf_dir = defaults.var_dir + "/wato"

g_root_folder = None # pointer to root folder
g_folder      = None # pointer to current folder
g_file        = None # pointer to current file
g_files       = None # dictionary of all files (key = tuple-path)
g_pathname    = ""   # textual path name of current folder

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

def page_handler(h):
    global html
    html = h

    if not config.may("use_wato"):
        raise MKAuthException(_("You are not allowed to use WATO!"))

    declare_host_tag_attributes()
    load_folder_config()
    get_folder_and_file() # sets g_root_folder and g_pathname

    if g_file:
        title = g_file["title"]
        read_the_configuration_file()
    else:
        title = g_folder["title"]

    default_mode = g_file and "file" or "folder"
    current_mode = html.var("mode", default_mode)
    modefunc = mode_functions.get(current_mode)

    # Do actions (might switch mode)
    action_message = None
    if html.has_var("_transid"):
        try:
            result = modefunc("action")
            if type(result) == tuple:
                newmode, action_message = result
            else:
                newmode = result

            # if newmode is not None, then the mode has been changed
            if newmode != None:
                if newmode == "": # no further information: configuration dialog, etc.
                    if action_message:
                        html.message(action_message)
                    if g_html_head_open:
                        html.write("</div>")
                        html.footer()
                    return
                modefunc = mode_functions.get(newmode, mode_file)
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

    # Show contexts buttons
    html.begin_context_buttons()
    modefunc("buttons")
    for inmode, buttontext, targetmode in extra_buttons:
        if inmode == current_mode:
            html.context_button(buttontext, make_link([("mode", targetmode)]))
    html.end_context_buttons()

    # Show outcome of action
    if html.has_users_errors():
        html.show_error(action_message)
    elif action_message:
        html.message(action_message)

    # Show content
    modefunc("content")

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
        html.context_button(_("Properties"), make_link_to([("mode", "editfolder")], g_folder[".path"]))
        html.context_button(_("New folder"), make_link([("mode", "newfolder")]))
        html.context_button(_("New host list"), make_link([("mode", "newfile")]))
        changelog_button()
        search_button()
    
    elif phase == "action":
        if html.var("_delete") and html.transaction_valid():
            delname = html.var("_delete")
            if delname in g_folder[".folders"]:
                del_folder = g_folder[".folders"][delname]
                if len(del_folder[".files"]) > 0:
                    raise MKUserError(None, _("The folder %s cannot be deleted, it still contains some files.")
                    % del_folder["title"])
                if len(del_folder[".folders"]) > 0:
                    raise MKUserError(None, _("The folder %s cannot be deleted, it still contains subfolders.")
                    % del_folder["title"])
                return delete_folder_after_confirm(del_folder)
            elif delname in g_folder[".files"]:
                del_file = g_folder[".files"][delname]
                return delete_file_after_confirm(del_file)
            else:
                raise MKGeneralException(_("You called this page with a non-existing folder/file %s") % delname)

    else:
        render_folder_path()
        show_filefolder_list(g_folder, "folder", _("Subfolders"))
        show_filefolder_list(g_folder, "file",   _("Host lists"))


def show_filefolder_list(thing, what, title):
    # Show list of files
    if len(thing["." + what + "s" ]) > 0:
        html.write("<h3>%s</h3>" % title)
        html.write("<table class=data>\n")
        html.write("<tr><th>" + _("Actions") + "</th><th>" + _("Title") + "</th>")

        for attr in host_attributes:
            if attr.show_in_table() and attr.show_in_folder():
                html.write("<th>%s</th>" % attr.title())

        if not config.wato_hide_filenames:
            html.write("<th>%s</th>" % what.title())
        html.write("<th>" + _("Hosts") + "</th></tr>\n")

        odd = "even"

        for entry in sort_by_title(thing["." + what + "s"].values()):
            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)

            name = entry[".name"]
            if what == "folder":
                folder_path = entry[".path"]
                filename = None
            else:
                folder_path = thing[".path"]
                filename = name

            edit_url     = make_link_to([("mode", "edit" + what)], folder_path, filename)
            delete_url   = make_action_link([("mode", "folder"), ("_delete", entry[".name"])])
            enter_url    = make_link_to([], folder_path, filename)

            html.write("<td>")
            html.buttonlink(edit_url, _("Properties"))
            html.buttonlink(delete_url, _("Delete"))
            if what == "file":
                html.buttonlink(enter_url, _("Hosts"))
            html.write("</td>")


            # Title and filename
            html.write('<td class=takeall><a href="%s">%s</a></td>' % 
                        (enter_url, entry["title"]))

            # Attributes for Hosts
            for attr in host_attributes:
                if attr.show_in_table() and attr.show_in_folder():
                    attrname = attr.name()
                    if attrname in entry.get("attributes", {}):
                        tdclass, content = attr.paint(entry["attributes"][attrname], "")
                    else:
                        tdclass, content = "", ""
                    html.write('<td class="%s">%s</td>' % (tdclass, content))

            # Internal filename
            if not config.wato_hide_filenames:
                html.write("<td>%s</td>" % name)

            # Number of hosts
            if what == "file":
                num_hosts = entry.get("num_hosts")
            else:
                num_hosts = count_hosts(entry)
            if num_hosts != None:
                html.write("<td>%d</td>" % num_hosts)
            else:
                html.write("<td>?</td>")

            html.write("</tr>")
        html.write("</table>")
    else:
        html.write("<h3>" + _("There are no %s in this folder.") % title.lower() + "</h3>" )
    


# what is either "file" or "folder"
def mode_editfolder(phase, what, new):
    global g_folder

    if what == "folder":
        the_thing = g_folder
        the_what = _("folder")
    else:
        the_thing = g_file
        the_what = _("host list")

    # In editing mode, we always edit the *current* folder, i.e. that
    # one g_folder points to. In new mode the new folder is created
    # within g_folder
    if new:
        page_title = _("Create new ") + the_what
        name, title, roles = None, None, []
        mode = "new"
    else:
        page_title = _("Edit Properties")
        name  = the_thing[".name"]
        title = the_thing["title"]
        roles = the_thing["roles"]
        mode = "edit"

    if phase == "title":
        return page_title

    elif phase == "buttons":
        if what == "folder" and not new:
            target_folder = find_folder(g_folder[".path"][:-1])
        else:
            target_folder = g_folder
        if what == "file" and not new:
            html.context_button(_("Abort"), make_link([("mode", "file")]))
        else:
            html.context_button(_("Abort"), make_link([("mode", "folder")]))
            

    elif phase == "action":
        # Title
        title = html.var_utf8("title")
        if not title:
            raise MKUserError("title", _("Please supply a title."))

        # OS filename
        if new:
            if not config.wato_hide_filenames:
                name = html.var("name", "").strip()
                if what == "file" and not name.endswith(".mk"):
                    name += ".mk"
                check_wato_filename("name", name, what)
            else:
                name = create_wato_filename(title, what)

        # Roles and Permissions
        roles = [ role for role in config.roles if html.var("role_" + role) ]

        attributes = collect_attributes()
        attributes_changed = not new and attributes != the_thing.get("attributes", {})

        if new:
            newpath = g_folder[".path"] + (name,)
            new_thing = { 
                ".name"       : name,
                ".path"       : newpath,
                "title"      : title, 
                "roles"      : roles,
                "attributes" : attributes,
            }
            if what == "folder":
                new_thing.update({ 
                    ".folders" : {},
                    ".files" : {},
                })
            else:
                new_thing["num_hosts"] = 0
                g_files[newpath] = new_thing
            
            g_folder["." + what + "s"][name] = new_thing
            log_audit(new_thing, "new-" + what, _("Created new %s %s") % (the_what, title))

        else:
            the_thing["title"]      = title
            the_thing["roles"]      = roles
            the_thing["attributes"] = attributes

        if what == "folder":
           html.reload_sidebar() # refresh WATO snapin

        save_folder_config()

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        if attributes_changed:
            if what == "file":
                rewrite_config_file(g_folder, the_thing)
            else:
                rewrite_config_files_below(the_thing) # due to inherited attributes
            log_pending(the_thing, "edit-" + what, _("Changed attributes of %s %s") % (the_what, title))
            call_hook_host_changed(the_thing)

        return "folder"


    else:
        html.begin_form("edit" + what)
        html.write('<table class="form">\n')
        
        # title
        html.write("<tr><td class=legend colspan=2>Title</td><td class=content>")
        html.text_input("title", title)
        html.set_focus("title")
        html.write("</td></tr>\n")

        # folder/file name (omit this for root folder)
        if not (what == "folder" and not new and g_folder == g_root_folder):
            if not config.wato_hide_filenames:
                if what == "folder":
                    html.write("<tr><td class=legend colspan=2>" + _("Internal directory name") + "<br><i>"
                        + _("This is the name of subdirectory where the files and<br> "
                        "other folders will be created. You cannot change this later") +
                        "</i></td><td class=content>")
                else:
                    html.write("<tr><td class=legend colspan=2>" + _("Internal file name") + "<br><i>"
                        + _("This is the name of Check_MK configuration file where<br>"
                        "the hosts will be created. It well automatically get the<br>"
                        "extension <tt>.mk</tt>. Do not specify this extension here.<br>"
                        "You cannot change the file name later.") + "</i>"
                        "</td><td class=content>")

                if new:
                    html.text_input("name")
                else:
                    html.write(name)

                html.write("</td></tr>\n")

        # permissions
        html.write("<tr><td class=legend colspan=2>" + _("Grant access to") + "</td><td class=content>")
        for role in config.roles:
            html.checkbox("role_" + role, role in g_folder["roles"])
            html.write(" " + role + "<br>")
        html.write("</td></tr>")

        # Attributes inherited to hosts
        if have_folder_attributes():
            html.write("<tr><td class=title colspan=3>")
            html.write(_("The following attributes will be inherited to all hosts "
                         "in this %s") % the_what)
            html.write("</td></tr>")
            if new:
                attributes = { }
                parent = g_folder
            else:
                attributes = the_thing.get("attributes", {})
                parent = g_folder.get(".parent")

            configure_attributes({what: attributes}, "folder", parent, the_thing)

        html.write('<tr><td colspan=3 class="buttons">')
        html.button("save", _("Save &amp; Finish"), "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()
        

def check_wato_filename(htmlvarname, name, what):
    if what == "file":
        if not name.endswith(".mk"):
            raise MKUserError(htmlvarname, _("The name of the file must end with .mk"))
        name = name[:-3]
    if what == "folder" and name in g_folder[".folders"]:
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))
    elif what == "file" and name in g_folder[".files"]:
        raise MKUserError(htmlvarname, _("A file with that name already exists."))
    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))
    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(htmlvarname, _("Invalid %s name. Only the characters a-z, A-Z, 0-9, _ and - are allowed.") % what)

def create_wato_filename(title, what):
    basename = convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if what == "folder" and name not in g_folder[".folders"]:
            break
        elif what == "file" and name + ".mk" not in g_folder[".files"]:
            break
        c += 1
        name = "%s-%d" % (basename, c)
    if what == "file":
        return name + ".mk"
    else:
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

#   +----------------------------------------------------------------------+
#   |       ____                           _   _           _               |
#   |      |  _ \ __ _  __ _  ___  ___ _  | | | | ___  ___| |_ ___         |
#   |      | |_) / _` |/ _` |/ _ \/ __(_) | |_| |/ _ \/ __| __/ __|        |
#   |      |  __/ (_| | (_| |  __/\__ \_  |  _  | (_) \__ \ |_\__ \        |
#   |      |_|   \__,_|\__, |\___||___(_) |_| |_|\___/|___/\__|___/        |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+
#   | Code creating the actual web pages: handling of hosts                |
#   +----------------------------------------------------------------------+

def mode_file(phase):

    if phase == "title":
        return "Hosts list"

    elif phase == "buttons":
        html.context_button(_("Back"), make_link_to([("mode", "folder")], g_folder[".path"]))
        html.context_button(_("Properties"), make_link_to([("mode", "editfile")], g_folder[".path"], g_file[".name"]))
        html.context_button(_("New host"), make_link([("mode", "newhost")]))
        changelog_button()
        search_button()
    
    elif phase == "action":
        if html.var("_search"): # just commit to search form
            return

        # Deletion of single hosts
        delname = html.var("_delete")
        if delname and delname in g_hosts:
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

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"

    elif len(g_hosts) == 0:
        render_folder_path()
        html.write("<div class=info>" + _("There are no hosts in this file.") + "</div>")

    else:
        render_folder_path()
        html.write("<p>")

        html.begin_form("search")
        html.text_input("search")
        html.button("_search", _("Search"))
        html.set_focus("search")
        html.hidden_fields()
        html.end_form()
        html.write("<p>")

        hostnames = g_hosts.keys()
        hostnames.sort()

        # Show table of hosts in this file
        colspan = 5
        html.begin_form("hosts", None, "POST")
        html.write("<table class=data>\n")
        html.write("<tr><th></th><th></th><th>" + _("Hostname") + "</th>")
        
        for attr in host_attributes:
            if attr.show_in_table():
                html.write("<th>%s</th>" % attr.title())
                colspan += 1

        html.write("<th>" + _("Move To") + "</th>")
        html.write("</tr>\n")
        odd = "odd"

        search_text = html.var("search")
        selected_hosts = get_hostnames_from_checkboxes()
        for hostname in hostnames:
            if search_text and (search_text.lower() not in hostname.lower()):
                continue

            host = g_hosts[hostname]
            effective = effective_attributes(host, g_file)

            # Rows with alternating odd/even styles
            html.write('<tr class="data %s0">' % odd)
            odd = odd == "odd" and "even" or "odd" 

            # Check box (if none is checked, then the default is to check all)
            def_value = selected_hosts == []
            html.write("<td>")
            html.checkbox("sel_%s" % hostname, def_value, 'wato_select')
            html.write("</td>")

            # Column with actions (buttons)
            edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
            services_url = make_link([("mode", "inventory"), ("host", hostname)])
            clone_url    = make_link([("mode", "newhost"), ("clone", hostname)])
            delete_url   = make_action_link([("mode", "file"), ("_delete", hostname)])

            html.write("<td>")
            html.buttonlink(edit_url, _("Edit"))
            html.buttonlink(services_url, _("Services"))
            html.buttonlink(clone_url, _("Clone"))
            html.buttonlink(delete_url, _("Delete"))
            html.write("</td>")

            # Hostname with link to edit form
            html.write('<td><a href="%s">%s</a></td>' % (edit_url, hostname))

            # Show attributes
            for attr in host_attributes:
                attrname = attr.name()
                if attr.show_in_table():
                    if attrname in host:
                        tdclass, tdcontent = attr.paint(host.get(attrname), hostname)
                    else:
                        tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                        tdclass += " inherited"
                    html.write('<td class="%s">' % tdclass)
                    html.write(tdcontent)
                    html.write("</td>")

            # Move to
            html.write("<td>")
            host_move_combo(hostname)
            html.write("</td>")
            html.write("</tr>\n")

        # bulk actions
        html.write('<tr class="data %s0"><td>' % odd)
        html.jsbutton('_markall', 'X', 'javascript:wato_check_all(\'wato_select\');')
        html.write("</td><td colspan=%d>" % colspan)
        html.write(_("On all selected hosts:\n"))
        html.button("_bulk_delete", _("Delete"))
        html.button("_bulk_edit", _("Edit"))
        html.button("_bulk_cleanup", _("Cleanup"))
        html.button("_bulk_inventory", _("Inventory"))
        host_move_combo(None)
        html.write("</td></tr>\n")

        html.write("</table>\n")

        # Important: remove selected hosts from the hidden fields. Otherwise
        # hosts once selected will be selected for ever...
        for host in hostnames:
            varname = "sel_%s" % host
            if html.has_var(varname):
                html.del_var("sel_%s" % host)
        html.hidden_fields()

        html.end_form()

# Create list of all hosts that are select with checkboxes in the current file
def get_hostnames_from_checkboxes():
    hostnames = g_hosts.keys()
    hostnames.sort()
    selected_hosts = []
    search_text = html.var("search")
    for name in hostnames:
        if (not search_text or (search_text.lower() in name.lower())) \
            and html.var("sel_" + name):
            selected_hosts.append(name)
    return selected_hosts



# Form for host details (new, clone, edit)
def mode_edithost(phase, new):
    hostname = html.var("host") # may be empty in new/clone mode

    clonename = html.var("clone")
    if clonename and clonename not in g_hosts:
        raise MKGeneralException(_("You called this page with an invalid host name."))
    
    if clonename:
        title = _("Create clone of %s") % clonename
        host = g_hosts[clonename]
        mode = "clone"
    elif not new and hostname in g_hosts:
        title = _("Edit host ") + hostname
        host = g_hosts[hostname]
        mode = "edit"
    else:
        title = _("Create new host")
        host = {}
        mode = "new"

    if phase == "title":
        return title

    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "file")]))
        if not new:
            html.context_button(_("Services"), make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "file"
            else:
                return delete_host_after_confirm(hostname)

        host = collect_attributes()

        # handle clone & new
        if new:
            if not hostname:
                raise MKUserError("host", _("Please specify a host name"))
            elif hostname in g_hosts:
                raise MKUserError("host", _("A host with this name already exists."))
            elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                raise MKUserError("host", _("Invalid host name: must contain only characters, digits, dash, underscore and dot."))

        if hostname:
            go_to_services = html.var("services")
            if html.check_transaction():
                g_hosts[hostname] = host
                if new:
                    message = _("Created new host %s.") % hostname
                    log_pending(hostname, "create-host", message) 
                    g_file["num_hosts"] += 1
                else:
                    log_pending(hostname, "edit-host", _("Edited properties of host [%s]") % hostname)
                write_the_configuration_file()
                call_hook_host_changed(g_file)
            if new:
                return go_to_services and "firstinventory" or "file"
            else:
                return go_to_services and "inventory" or "file"


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

        configure_attributes({hostname: host}, "host", g_file)

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
    if hostname not in g_hosts:
        raise MKGeneralException(_("You called this page for a non-existing host."))

    if phase == "title":
        title = _("Services of host %s") % hostname
        if html.var("scan"):
            title += _(" (live scan)")
        else:
            title += _(" (cached data)")
        return title

    elif phase == "buttons":
        html.context_button(_("Host list"), make_link([("mode", "file")]))
        html.context_button(_("Edit host"), make_link([("mode", "edithost"), ("host", hostname)]))
        html.context_button(_("Full Scan"), html.makeuri([("scan", "yes")]))

    elif phase == "action":
        if html.check_transaction():
            cache_options = not html.var("scan") and [ '--cache' ] or []
            table = check_mk_automation("try-inventory", cache_options + [hostname])
            table.sort()
            active_checks = {}
            new_target = "file"
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
        return "file"


    else:
        show_service_table(hostname, firsttime)

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
        html.context_button(_("Back"), make_link_to([("mode", "folder")], g_folder[".path"]))

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
        configure_attributes({}, "search", None)
        
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
    hosts = read_configuration_file(the_folder, the_file)
    for hostname, host in hosts.items():
        if crit[".name"] and crit[".name"].lower() not in hostname.lower():
            continue

        # Compute inheritance
        effective = effective_attributes(host, the_file)

        # Check attributes
        dont_match = False
        for attr in host_attributes:
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
        for attr in host_attributes:
            if attr.show_in_table():
                html.write("<th>%s</th>" % attr.title())
        html.write("</tr>")

        even = "even"
        for hostname, host, effective in found:
            even = even == "even" and "odd" or "even"
            host_url =  make_link_to([("mode", "edithost"), ("host", hostname)], the_folder[".path"], the_file[".name"])
            html.write('<tr class="data %s0"><td><a href="%s">%s</a></td>\n' % 
               (even, host_url, hostname))
            for attr in host_attributes:
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
        html.context_button(_("Back"), make_link([("mode", "file")]))
        return

    elif phase == "action":
        if html.var("_item"):
            how = html.var("how")
            hostname = html.var("_item")
            try:
                counts = check_mk_automation("inventory", [how, hostname])
                result = repr([ 'continue', 0 ] + list(counts)) + "\n"
                result += _("Inventorized %s<br>\n") % hostname
                log_pending(hostname, "bulk-inventory", _("Inventorized host: %d added, %d removed, %d kept, %d total services") % counts)
            except Exception, e:
                result = repr([ 'failed', 1, 0, 0, 0, 0, ]) + "\n"
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
            [ (_("Failed hosts"), 0), (_("Services added"), 0), (_("Services removed"), 0), 
              (_("Services kept"), 0), (_("Total services"), 0) ], # stats table
            [ ("mode", "file") ], # URL for "Stop/Finish" button
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
        html.context_button(_("Back"), make_link([("mode", "file")]))
        return

    elif phase == "action":
        if html.check_transaction():
            changed_attributes = collect_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_hosts[hostname]
                host.update(changed_attributes)
                log_pending(hostname, "bulk-edit", _("Changed attributes of host %s in bulk mode") % hostname)
            write_the_configuration_file()
            call_hook_host_changed(g_file)
            return "file"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_hosts[hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk edit. You can now change "
               "host attributes for all selected hosts at once. ") % len(hostnames))
    html.write(_("If a select is set to <i>don't change</i> then currenty not all selected "
    "hosts share the same setting for this attribute. If you leave that selection, all hosts "
    "will keep their individual settings.") + "</p>")

    html.begin_form("bulkedit", None, "POST")
    html.write("<table class=form>")
    configure_attributes(hosts, "bulk", g_file)
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
        html.context_button(_("Back"), make_link([("mode", "file")]))
        return

    elif phase == "action":
        if html.check_transaction():
            to_clean = bulk_collect_cleaned_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_hosts[hostname]
                num_cleaned = 0
                for attrname in to_clean:
                    num_cleaned += 1
                    if attrname in host:
                        del host[attrname]
                if num_cleaned > 0:
                    log_pending(hostname, "bulk-cleanup", _("Cleaned %d attributes of host %s in bulk mode") % (
                    num_cleaned, hostname))
            write_the_configuration_file()
            call_hook_host_changed(g_file)
            return "file"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_hosts[hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
    "explicit attribute values from hosts. The hosts will then inherit attributes "
    "configured at the host list or folders or simply fall back to the builin "
    "default values.") % len(hostnames))
    html.write("</p>")

    html.begin_form("bulkcleanup", None, "POST")
    html.write("<table class=form>")
    if not bulk_cleanup_attributes(g_file, hosts):
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
    for attr in host_attributes:
        attrname = attr.name()
        if html.get_checkbox("_clean_" + attrname) == True:
            to_clean.append(attrname)
    return to_clean


def bulk_cleanup_attributes(the_file, hosts):
    num_shown = 0
    for attr in host_attributes:
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
#   |                 ____  _     _      _                                 |
#   |                / ___|(_) __| | ___| |__   __ _ _ __                  |
#   |                \___ \| |/ _` |/ _ \ '_ \ / _` | '__|                 |
#   |                 ___) | | (_| |  __/ |_) | (_| | |                    |
#   |                |____/|_|\__,_|\___|_.__/ \__,_|_|                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Functions called from the WATO sidebar snapin                        |
#   +----------------------------------------------------------------------+

def render_link_tree(h, format):
    global html
    html = h

    load_folder_config()

    def render_folder(f):

        subfolders = f[".folders"]
        path = f[".path"]
        filename = "/" + "/".join(path) + "/"
        if len(path) > 0:
            url = "wato.py?filename=" + htmllib.urlencode(filename)
            if len(subfolders) == 0:
                title = format % (url, f["title"])
            else:
                title = '<a target=main href="%s">%s</a>' % (url, f["title"]) 
        else:
            title  = '<a target=main href="wato.py">%s</a>' % f["title"]

        if len(subfolders) > 0:
            html.begin_foldable_container('wato', filename, False, title)
            for sf in sort_by_title(subfolders.values()):
                render_folder(sf)
            html.end_foldable_container()
        else:
            html.write(title)

    render_folder(g_root_folder)


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
        html.context_button(_("Back"), make_link([("mode", "folder")]))
        if log_exists("pending"):
            html.context_button(_("Activate Changes!"), 
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())]), True)
        if log_exists("audit"):
            html.context_button(_("Clear Audit Log"),
                html.makeuri([("_action", "clear"), ("_transid", html.current_transid())]))

    elif phase == "action":
        if html.var("_action") == "clear":
            return clear_audit_log_after_confirm()
        elif html.check_transaction():
                try:
                    check_mk_automation("restart")
                except Exception, e:
                    raise MKUserError(None, str(e))
                log_commit_pending() # flush logfile with pending actions
                log_audit(None, "activate-config", _("Configuration activated, monitoring server restarted"))
                return None, _("The new configuration has been successfully activated.")


    else:
        pending = parse_audit_log("pending")
        if len(pending) > 0:
            message = "<h1>" + _("Changes which are not yet activated:") + "</h1>"
            message += render_audit_log(pending, "pending")
            html.show_warning(message)
        else:
            html.write("<p>" + _("No pending changes, monitoring server is up to date.") + "</p>")

        audit = parse_audit_log("audit")
        if len(audit) > 0:
            html.write("<b>" + _("All Changes") + "</b>")
            html.write(render_audit_log(audit, "audit"))
        else:
            html.write("<p>" + _("Logfile is empty. No host has been created or changed yet.") + "</p>")
        
def log_entry(linkinfo, action, message, logfilename):
    if type(message) == unicode:
        message = message.encode("utf-8")
    make_nagios_directory(conf_dir)
    if linkinfo in g_files.values():
        link = file_os_path(linkinfo)
    elif type(linkinfo) == dict and find_folder(linkinfo[".path"]):
        link = file_os_path(linkinfo) + "/"
    elif linkinfo == None:
        link = "-"
    elif g_file: # hostname
        link = file_os_path(g_file) + ":" + linkinfo
    else:
        link = linkinfo

    log_file = conf_dir + "/" + logfilename
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
    pending = conf_dir + "/pending.log"
    if os.path.exists(pending):
        os.remove(pending)

def clear_audit_log():
    path = conf_dir + "/audit.log"
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
    path = conf_dir + "/" + what + ".log"
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip().decode("utf-8")
            entries.append(line.split(None, 4))
        entries.reverse()
        return entries
    return []

def log_exists(what):
    path = conf_dir + "/" + what + ".log"
    return os.path.exists(path)



def render_linkinfo(linkinfo):
    if ':' in linkinfo:
        pathname, hostname = linkinfo.split(':', 1)
        path = tuple(pathname[1:].split("/"))
        if path in g_files:
            the_file = g_files[path]
            the_folder = find_folder(path[:-1])
            hosts = read_configuration_file(the_folder, the_file)
            if hostname in hosts:
                url = html.makeuri_contextless([("mode", "edithost"), ("filename", pathname), ("host", hostname)])
                title = hostname
            else:
                return hostname
        else:
            return hostname
    elif linkinfo[0] == '/':
        path = tuple(linkinfo[1:].strip("/").split("/"))
        if path in g_files:
            url = html.makeuri_contextless([("mode", "file"), ("filename", linkinfo)])
            title = g_files[path]["title"]
        elif find_folder(path):
            url = html.makeuri_contextless([("mode", "folder"), ("filename", linkinfo)])
            title = find_folder(path)["title"]
        else:
            return linkinfo
    else:
        return ""

    return '<a href="%s">%s</a>' % (url, title)


def render_audit_log(log, what, with_filename = False):
    htmlcode = '<table class="wato auditlog">'
    even = "even"
    for t, linkinfo, user, action, text in log:
        even = even == "even" and "odd" or "even"
        htmlcode += '<tr class="%s0">' % even
        htmlcode += '<td>%s</td>' % render_linkinfo(linkinfo)
        htmlcode += '<td>%s</td><td>%s</td><td>%s</td><td width="100%%">%s</td></tr>\n' % (
                time.strftime("%Y-%m-%d", time.localtime(float(t))),
                time.strftime("%H:%M:%S", time.localtime(float(t))),
                user,
                text)
    htmlcode += "</table>"
    return htmlcode

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

# sort list of folders or files by their title
def sort_by_title(folders):
    def folder_cmp(f1, f2):
        return cmp(f1["title"].lower(), f2["title"].lower())
    folders.sort(cmp = folder_cmp)
    return folders

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


def make_config_path(folder, file = None):
    parts = folder[".path"]
    if type(file) == dict:
        parts += (file[".name"],)
    elif file:
        parts += (file,)

    return defaults.check_mk_configdir + "/" + "/".join(parts)



# Remove all keys beginning with '.' in a folder. Those keys
# keep temporary information (such as a link back to the parent)
# which need not or cannot be persisted.
def clean_dict(d):
    return dict([(k, v) for (k, v) in d.iteritems() if not k.startswith('.') ])

def folder_dir(the_folder):
    return defaults.check_mk_configdir + file_os_path(the_folder)

def save_folder_config():
    # The folder configuration is saved directly in the filesystem. The 
    # configuration for a folder is saved in /.wato, that of a file is saved
    # in thefile.mk.wato.
    save_folder_info(g_root_folder)

def save_folder_info(the_folder):
    dir = folder_dir(the_folder)
    make_nagios_directory(dir)
    fn = dir + "/.wato"
    config.write_settings_file(fn, clean_dict(the_folder))

    for subfolder in the_folder[".folders"].values():
        save_folder_info(subfolder)

    for subfile in the_folder[".files"].values():
        save_file_info(subfile)

def save_file_info(the_file):
    fn = folder_dir(the_file) + ".wato"
    config.write_settings_file(fn, clean_dict(the_file))

# Load the information about all WATO-handles configuration files
# in check_mk/conf.d and also the folder meta-data
def load_folder_config():
    dir = defaults.check_mk_configdir

    global g_root_folder, g_files
    g_files = {}
    g_root_folder = load_folder_info(dir)

def load_folder_info(dir, name = "", path=()):
    fn = dir + "/.wato"
    try:
        the_folder = eval(file(fn).read())
    except:
        the_folder = { 
            "roles" : [ "admin" ], 
            "title" : name and name or _("Main directory")
        }

    the_folder[".name"]    = name
    the_folder[".path"]    = path
    the_folder[".folders"] = {}
    the_folder[".files"]   = {}

    # Now look for WATO files and subdirectories
    for entry in os.listdir(dir):
        if entry[0] == '.':
            continue

        p = dir + "/" + entry

        if os.path.isdir(p):
            f = load_folder_info(p, entry, path + (entry,))
            f[".parent"] = the_folder
            the_folder[".folders"][entry] = f

        elif entry.endswith(".mk.wato"):
            name = entry[:-5]
            f = load_file_info(p, name, path + (name,))
            f[".parent"] = the_folder
            the_folder[".files"][name] = f
    
    return the_folder

def load_file_info(fn, name, path):
    try:
        the_file = eval(file(fn).read())
    except:
        the_file = { 
            "roles" : [ "admin" ], 
            "title" : name,
        }

    the_file[".name"] = name
    the_file[".path"] = path

    global g_files
    g_files[path] = the_file
    return the_file


def find_folder(path, in_folder = None):
    if in_folder == None:
        in_folder = g_root_folder

    if len(path) == 0:
        return in_folder
    else:
        name, rest = path[0], path[1:]
        if name not in in_folder[".folders"]:
            return None
        else:
            return find_folder(rest, in_folder[".folders"][name])

def count_hosts(folder):
    num = 0
    for f in folder[".files"].values():
        if "num_hosts" in f:
            num += f["num_hosts"]
        else:
            return None

    for sf in folder[".folders"].values():
        c = count_hosts(sf)
        if c == None:
            return None
        num += c 
    folder["num_hosts"] = num
    return num

# Load all hosts from all configuration files.
def load_all_hosts(base_folder = None):
    if base_folder == None:
        base_folder = g_root_folder
    hosts = {}
    for f in base_folder[".files"].values():
        hosts.update(read_configuration_file(base_folder, f))
    for f in base_folder[".folders"].values():
        hosts.update(load_all_hosts(f))
    return hosts

def read_the_configuration_file():
    global g_hosts
    g_hosts = read_configuration_file(g_folder, g_file)
    g_file["num_hosts"] = len(g_hosts)


def read_configuration_file(folder, thefile):
    hosts = {}

    path = make_config_path(folder, thefile)
    if os.path.exists(path):
        variables = {
            "ALL_HOSTS"          : ['@all'],
            "all_hosts"          : [],
            "ipaddresses"        : {},
            "extra_host_conf"    : { "alias" : [] },
            "extra_service_conf" : { "_WATO" : [] },
            "host_attributes"    : {},
        }
        execfile(path, variables, variables)
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
                for attr in host_attributes:
                    if isinstance(attr, HostTagAttribute):
                        tagvalue = attr.get_tag_value(tags)
                        host[attr.name()] = tagvalue
            hosts[hostname]   = host


    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))
    return hosts


def write_the_configuration_file():
    write_configuration_file(g_folder, g_file, g_hosts)
    save_folder_config()


def rewrite_config_files_below(folder):
    for fi in folder[".files"].values():
        rewrite_config_file(folder, fi)
    for fo in folder[".folders"].values():
        rewrite_config_files_below(fo)

def rewrite_config_file(folder, thefile):
    hosts = read_configuration_file(folder, thefile)
    write_configuration_file(folder, thefile, hosts)


def write_configuration_file(folder, thefile, hosts):
    wato_filename = "/" + "/".join(thefile[".path"])  # used as tag
    all_hosts = []
    ipaddresses = {}
    aliases = []
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        host = hosts[hostname]
        effective = effective_attributes(host, thefile)

        # Make special handling of attributes configured in a special way 
        # in check_mk
        alias     = effective.get("alias")
        ipaddress = effective.get("ipaddress")

        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag.
        tags = set([])
        for attr in host_attributes:
            if isinstance(attr, HostTagAttribute):
                value = effective.get(attr.name())
                tags.update(attr.get_tag_list(value))

        if alias:
            aliases.append((alias, [hostname]))
        all_hosts.append("|".join([hostname] + list(tags) + [ wato_filename, 'wato' ]))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    dir = make_config_path(folder)
    if not os.path.isdir(dir):
        os.makedirs(dir)

    path = make_config_path(folder, thefile)
    out = file(path, "w")
    out.write("# Written by Check_MK Webconf\n\n")
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
              (wato_filename, wato_filename))

    # Add custom macros for attributes that are to be present in Nagios
    custom_macros = {}
    for hostname, host in hosts.items():
        for attr in host_attributes:
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
    path = make_config_path(folder, thefile)
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

def get_folder_and_file():
    global g_folder, g_file, g_pathname

    g_pathname = html.var("filename")
    if not g_pathname:
        g_pathname = "/"
    if g_pathname[0] != '/' :
        raise MKGeneralException(_("You called this page with an invalid WATO filename!"))

    parts = g_pathname[1:].split("/")
    path = tuple(parts[:-1])
    filename = parts[-1]

    g_folder = find_folder(path)
    if not g_folder:
        raise MKGeneralException(_('You called this page with a non-existing folder! '
                                 'Go back to the <a href="wato.py">main index</a>.'))
    if filename:
        if filename not in g_folder[".files"]:
            raise MKGeneralException(_('You called this page with a non-existing file! '
                                     'Go back to the <a href="wato.py">main index</a>.'))

        g_file = g_folder[".files"][filename]
        if config.role not in g_file["roles"]:
            raise MKAuthException(_("You have no permissions on this configuration file!"))

    else:
        g_file = None


# Create link keeping the context to the current folder / file
def make_link(vars):
    folder_path = g_folder[".path"]

    if len(folder_path) > 0:
        os_path = "/" + "/".join(folder_path) + "/"
    else:
        os_path = "/"

    if g_file:
        os_path += g_file[".name"]

    vars = vars + [ ("filename", os_path) ]
    return html.makeuri_contextless(vars)

# Create link creating a context to a given folder / file
def make_link_to(vars, folder_path, filename = None):
    if len(folder_path) > 0:
        os_path = "/" + "/".join(folder_path) + "/"
    else:
        os_path = "/"

    if filename:
        os_path += filename

    vars = vars + [ ("filename", os_path) ]
    return html.makeuri_contextless(vars)


def make_action_link(vars):
    return make_link(vars + [("_transid", html.current_transid())])

def make_action_link_to(vars, folder_path, filename = None):
    return make_link_to(vars + [("_transid", html.current_transid())], folder_path, filename)

def search_button():
    html.context_button(_("Search"), make_link([("mode", "search")]))

def changelog_button():
    pending = parse_audit_log("pending")
    buttontext = _("ChangeLog")
    if len(pending) > 0:
        buttontext = "<b>%s (%d)</b>" % (buttontext, len(pending))
        hot = True
    else:
        hot = False
    html.context_button(buttontext, make_link([("mode", "changelog")]), hot)


def show_service_table(hostname, firsttime):
    # Read current check configuration
    cache_options = not html.var("scan") and [ '--cache' ] or []
    table = check_mk_automation("try-inventory", cache_options + [hostname])
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
        del g_hosts[delname]
        g_file["num_hosts"] -= 1
        write_the_configuration_file()
        log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        check_mk_automation("delete-host", [delname])
        call_hook_host_changed(g_file)
        return "file"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_hosts_after_confirm(hosts):
    c = wato_confirm(_("Confirm deletion of %d hosts") % len(hosts),
                     _("Do you really want to delete the %d selected hosts?") % len(hosts))
    if c:
        for delname in hosts:
            del g_hosts[delname]
            g_file["num_hosts"] -= 1
            check_mk_automation("delete-host", [delname])
            log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        write_the_configuration_file()
        call_hook_host_changed(g_file)
        return "file", _("Successfully deleted %d hosts") % len(hosts)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_folder_after_confirm(del_folder):
    c = wato_confirm(_("Confirm folder deletion"),
                     _("Do you really want to delete the folder <tt>%s</tt> (%s)?") 
                % (file_os_path(del_folder), del_folder["title"]))
    if c:
        del g_folder[".folders"][del_folder[".name"]]
        folder_path = make_config_path(del_folder)
        try:
            os.remove(folder_path + "/.wato")
            os.rmdir(folder_path)
        except:
            pass
        if os.path.exists(folder_path):
            raise MKGeneralException(_("Cannot remove the folder '%s': probably there are "
                                       "still non-WATO files contained in this directory.") % folder_path)

        save_folder_config()
        log_audit(file_os_path(del_folder), "delete-folder", _("Deleted empty folder %s")% file_os_path(del_folder))
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
        hosts = read_configuration_file(g_folder, del_file)
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
        call_hook_host_changed(g_folder)
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

def file_os_path(f):
    return "/" + "/".join(f[".path"]) 

g_html_head_open = False

def wato_html_head(title):
    global g_html_head_open
    g_html_head_open = True
    html.header(title)
    html.write("<div class=wato>\n")

def host_move_combo(host = None):
    other_files = []
    for path, afile in g_files.items():
        if config.role in afile["roles"] and afile != g_file:
            os_path = "/" + "/".join(path)
            other_files.append((os_path, "%s (%s)" % (afile["title"], os_path)))

    if len(other_files) > 0:
        selections = [("", _("(select file)"))] + other_files 
        if host == None:
            html.button("_bulk_move", _("Move To:"))
            html.select("bulk_moveto", selections, "")
        else:
            html.hidden_field("host", host)
            uri = html.makeuri([("host", host), ("_transid", html.current_transid() )])
            html.sorted_select(None, selections, "", 
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri);


def move_hosts_to(hostnames, target_filename):
    path = tuple(target_filename[1:].split('/'))
    
    if path not in g_files: # invalid file
        return

    target_file = g_files[path]
    if target_file == g_file:
        return # target-file is source-file

    folder_path = path[:-1]
    target_folder = find_folder(folder_path)
    if not target_folder:
        return

    if config.role not in target_file["roles"]:
        raise MKAuthException(_("You have no change permissions on the target file"))

    # read hosts currently in target file
    target_hosts = read_configuration_file(target_folder, target_file)

    num_moved = 0
    for hostname in hostnames:
        if hostname not in g_hosts: # non-existant host
            continue

        target_hosts[hostname] = g_hosts[hostname]
        target_file["num_hosts"] += 1
        g_file["num_hosts"] -= 1
        del g_hosts[hostname]
        if len(hostnames) == 1:
            log_pending(hostname, "move-host", _("Moved host from %s to %s") %
                (file_os_path(g_file), file_os_path(target_file)))
        num_moved += 1

    write_configuration_file(target_folder, target_file, target_hosts)
    write_the_configuration_file()
    call_hook_host_changed(g_root_folder)
    if len(hostnames) > 1:
        log_pending(target_file, "move-host", _("Moved %d hosts from %s to %s") %
            (num_moved, file_os_path(g_file), file_os_path(target_file)))
    return num_moved 
        

def move_host_to(hostname, target_filename):
    move_hosts_to([hostname], target_filename)

def render_folder_path(the_folder = 0, the_file = 0, link_to_last = False):

    if the_folder == 0:
        the_folder = g_folder
        the_file = g_file

    def render_component(p, title):
        return '<a href="%s">%s</a>' % (
               html.makeuri_contextless([("filename", "/" + "/".join(p))]), title)

    path = ()
    comps = []
    
    for p in the_folder[".path"]:
        comps.append(render_component(path, find_folder(path)["title"]))
        path += (p,)

    if the_file or link_to_last:
        comps.append(render_component(the_folder[".path"], the_folder["title"]))

    if the_file:
        if link_to_last:
            comps.append(render_component(the_file[".path"], the_file["title"]))
        else:
            comps.append("<b>" + the_file["title"] + "</b>")

    if not the_file and not link_to_last:
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

def interactive_progress(items, title, stats, finishvars, timewait):
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
    json_items = '[ %s ]' % ','.join([ "'" + h + "'" for h in items ])
    html.javascript(('progress_scheduler("%s", "%s", 50, %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), html.makeuri([]), json_items, html.makeuri(finishvars)))

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


class IPAddressAttribute(TextAttribute):
    def __init__(self, name, title, help = None):
        TextAttribute.__init__(self, name, title, help, "", mandatory = True)

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
    
    def is_mandatory(self):
       return True # empty value allowed, but missing not

    def paint(self, value, hostname):
        if value == None:
            ip, tdclass, text = self.do_dns(hostname)
            return tdclass, text
        else:
            return "", value

    def validate_input(self):
        value = self.from_html_vars()
        if not value: # empty -> use DNS
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


# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self, name, title, help = None, default_value="", mandatory = False):
        TextAttribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory

    def to_nagios(self, value):
        return value.encode("utf-8")


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
        host_attributes = [ attr for attr in host_attributes if not attr.name().startswith("tag_") ]
        for attr in host_attribute.values():
            if attr.name().startswith("tag_"):
                del host_attribute[attr.name()]

        for num, entry in enumerate(config.host_tags):
            declare_host_attribute(HostTagAttribute(num + 1, entry), show_in_table = False, show_in_folder = True)

        configured_host_tags = config.host_tags


# Global datastructure holding all attributes (in a defined order)
host_attributes = []

# Dictionary for quick access
host_attribute = {}

# Declare attributes with this method
def declare_host_attribute(a, show_in_table = True, show_in_folder = True):
    host_attributes.append(a)
    host_attribute[a.name()] = a
    a._show_in_table = show_in_table
    a._show_in_folder = show_in_folder

# Read attributes from HTML variables
def collect_attributes(do_validate = True):
    host = {}
    for attr in host_attributes:
        attrname = attr.name()
        if not html.var("_change_%s" % attrname, False):
            continue

        if do_validate:
            attr.validate_input()
        host[attrname] = attr.from_html_vars()
    return host

def have_folder_attributes():
    for attr in host_attributes:
        if attr.show_in_folder():
            return True
    return False

# Show HTML form for editing attributes. for_what can be:
# "host"   -> normal host edit dialog
# "folder" -> properies of folder or file
# "search" -> search dialog
# "bulk"   -> bulk change
# parent: The parent file/folder of the objects to configure
# myself: For mode "folder" the folder/file itself
def configure_attributes(hosts, for_what, parent, myself=None):
    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))

    for attr in host_attributes:
        attrname = attr.name()

        # In folder/file not all attributes are shown
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

        # Collect information about attribute values inherited from file and folder.
        # This information is just needed for informational display to the user.
        # This does not apply in "search" mode. 
        inherited_from = None
        inherited_value = None
        has_inherited = False

        if for_what == "host":
            what = "file"
            url = make_link_to([("mode", "editfile")], g_folder[".path"], g_file[".name"])
        else:
            what = "folder"

        container = parent
        while container:
            if attrname in container.get("attributes", {}):
                if what != "file":
                    url = make_link_to([("mode", "editfolder")], container[".path"])
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
                onchange="wato_toggle_attribute(this, '%s');" % attrname ) # Only select if value is unique
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


def some_host_hasnt_set(container, attrname):
    if ".folders" in container: # we are a folder:
        for folder in container[".folders"].values():
            if attrname in folder.get("attributes", {}):
                return False
            elif some_host_hasnt_set(folder, attrname):
                return True
        for afile in container[".files"].values():
            if attrname in afile.get("attributes", {}):
                return False
            elif some_host_hasnt_set(afile, attrname):
                return True

    else: # we are a host list
        hosts = read_configuration_file(container[".parent"], container)
        for host in hosts.values():
            if attrname not in host:
                return True
    return False

# Compute effective (explicit and inherited) attributes
# for a host. This returns a dictionary with a value for
# each host attribute
def effective_attributes(host, container):
    chain = [ host ]
    while container:
        chain.append(container.get("attributes", {}))
        container = container.get(".parent")

    eff = {}
    for a in chain[::-1]:
        eff.update(a)

    # now add default values of attributes for all missing values
    for attr in host_attributes:
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
        load_folder_config()
        return collect_hosts(g_root_folder)

    def get_folder(self, path):
        load_folder_config()
        the_thing = g_root_folder
        while len(path) > 0:
             c = path[0]
             if c in the_thing[".folders"]:
                 the_thing = the_thing[".folders"][c]
             else:
                 return None
             path = path[1:]

        # add information about number of hosts
        count_hosts(the_thing)
        return the_thing

    def get_file(self, path):
        folder = self.get_folder(path[:-1])
        if not folder or not path[-1] in folder[".files"]:
            return None
        the_file = folder[".files"][path[-1]]
        if not the_file:
            return None
        hosts = read_configuration_file(folder, the_file)
        new_file = {}
        new_file.update(the_file)
        new_file["hosts"] = hosts
        return new_file


    # Get all effective data of a host. The_file must be returned by get_file()
    def get_host(self, the_file, hostname):
        host = the_file["hosts"][hostname]
        eff = effective_attributes(host, the_file)
        eff["name"] = hostname
        return eff

    # Return displayable information about host
    def get_host_painted(self, host): 
        result = []
        for attr in host_attributes:   
            attrname = attr.name()
            if attrname in host:
                tdclass, content = attr.paint(host[attrname], host["name"])
                result.append((attr.title(), content))
        return result


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
        hosts = read_configuration_file(the_thing[".parent"], the_thing)
        effective_hosts = dict([ (hn, effective_attributes(h, the_thing)) 
                               for (hn, h) in hosts.items() ])
        for host in effective_hosts.values():
            host["file"] = the_thing[".path"]
        return effective_hosts

def call_hooks(name, *args):
    for hk in hooks.get(name, []):
        hk(*args)

def call_hook_host_changed(the_thing): # called for file or folder
    if "hosts-changed" in hooks:
        hosts = collect_hosts(the_thing)
        call_hooks("hosts-changed", hosts)

    # The same with all hosts!
    if "all-hosts-changed" in hooks:
        hosts = collect_hosts(g_root_folder)
        call_hooks("all-hosts-changed", hosts)


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
   "newfolder"      : lambda phase: mode_editfolder(phase, "folder", True),
   "editfolder"     : lambda phase: mode_editfolder(phase, "folder", False),
   "newfile"        : lambda phase: mode_editfolder(phase, "file", True),
   "editfile"       : lambda phase: mode_editfolder(phase, "file", False),
   "newhost"        : lambda phase: mode_edithost(phase, True),
   "edithost"       : lambda phase: mode_edithost(phase, False),
   "firstinventory" : lambda phase: mode_inventory(phase, True),
   "inventory"      : lambda phase: mode_inventory(phase, False),
   "search"         : mode_search,
   "bulkinventory"  : mode_bulk_inventory,
   "bulkedit"       : mode_bulk_edit,
   "bulkcleanup"    : mode_bulk_cleanup,
   "changelog"      : mode_changelog,
   "file"           : mode_file,
}

extra_buttons = [
]


# Load all wato plugins
plugins_path = defaults.web_dir + "/plugins/wato"
if os.path.exists(plugins_path):
    for fn in os.listdir(plugins_path):
        if fn.endswith(".py"):
            execfile(plugins_path + "/" + fn)

if defaults.omd_root:
    local_plugins_path = defaults.omd_root + "/local/share/check_mk/web/plugins/wato"
    if local_plugins_path != plugins_path and os.path.exists(local_plugins_path):
        for fn in os.listdir(local_plugins_path):
            if fn.endswith(".py"):
                execfile(local_plugins_path + "/" + fn)

