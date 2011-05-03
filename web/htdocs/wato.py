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
     "Use WATO",
     "This permissions allows users to use WATO - Check_MK's Web Administration Tool.<br>"
     "Please make sure, that they also have the permission for the WATO snapin.",
     [ "admin", "user" ])

conf_dir = defaults.var_dir + "/web/wato"

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
        raise MKAuthException("You are not allowed to use WATO!")

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
    html.header("Check_MK WATO - %s - %s" % (title, modefunc("title")))
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
        return "Folder contents"

    elif phase == "buttons":
        html.context_button("Properties", make_link_to([("mode", "editfolder")], g_folder["path"]))
        html.context_button("New folder", make_link([("mode", "newfolder")]))
        html.context_button("New file", make_link([("mode", "newfile")]))
        changelog_button()
    
    elif phase == "action":
        if html.var("_delete") and html.transaction_valid():
            delname = html.var("_delete")
            if delname in g_folder["folders"]:
                del_folder = g_folder["folders"][delname]
                if len(del_folder["files"]) > 0:
                    raise MKUserError(None, "The folder %s cannot be deleted, it still contains some files."
                    % del_folder["title"])
                if len(del_folder["folders"]) > 0:
                    raise MKUserError(None, "The folder %s cannot be deleted, it still contains subfolders."
                    % del_folder["title"])
                return delete_folder_after_confirm(del_folder)
            elif delname in g_folder["files"]:
                del_file = g_folder["files"][delname]
                return delete_file_after_confirm(del_file)
            else:
                raise MKGeneralException("You called this page with a non-existing folder/file %s" % delname)

    else:
        html.write("Contents of folder ")
        render_folder_path()
        html.write("<p>")

        show_filefolder_list(g_folder, "folder", "Subfolders")
        show_filefolder_list(g_folder, "file",   "Files")


def show_filefolder_list(thing, what, title):
    # Show list of files
    if len(thing[what + "s" ]) > 0:
        html.write("<h3>%s</h3>" % title)
        html.write("<table class=data>\n")
        html.write("<tr><th>Title</th><th>Hosts</th><th>Actions</th>\n")
        odd = "even"
        for entry in thing[what + "s"].values():
            name = entry["name"]
            if what == "folder":
                folder_path = entry["path"]
                filename = None
            else:
                folder_path = thing["path"]
                filename = name

            edit_url     = make_link_to([("mode", "edit" + what)], folder_path, filename)
            delete_url   = make_action_link([("mode", "folder"), ("_delete", entry["name"])])
            enter_url    = make_link_to([], folder_path, filename)
            if what == "file":
                num_hosts = entry["num_hosts"]
            else:
                num_hosts = count_files(entry)

            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)

            html.write('<td class=takeall><a href="%s">%s</a></td>' % 
                        (enter_url, entry["title"]))
            html.write("<td>%d</td>" % num_hosts)
            html.write("<td>")
            html.buttonlink(edit_url, "Properties")
            html.buttonlink(delete_url, "Delete")
            html.write("</td>")
            html.write("</tr>")
        html.write("</table>")
    else:
        html.write("<h3>There are no %s in this folder.</h3>" % title.lower())
    


# what is either "file" or "folder"
def mode_editfolder(phase, what, new):
    global g_folder

    if what == "folder":
        the_thing = g_folder
    else:
        the_thing = g_file

    # In editing mode, we always edit the *current* folder, i.e. that
    # one g_folder points to. In new mode the new folder is created
    # within g_folder
    if new:
        page_title = "Create new " + what
        name, title, roles = None, None, []
        mode = "new"
    else:
        page_title = "Edit %s %s" % (what, g_folder["name"])
        if what == "file":
            page_title += "/" + g_file["name"]
        name  = the_thing["name"]
        title = the_thing["title"]
        roles = the_thing["roles"]
        mode = "edit"

    if phase == "title":
        return page_title

    elif phase == "buttons":
        if what == "folder" and not new:
            target_folder = find_folder(g_folder["path"][:-1])
        else:
            target_folder = g_folder
        html.context_button("Abort", make_link([("mode", "folder")]))

    elif phase == "action":
        if new:
            name = html.var("name").strip()
            check_wato_filename("name", name, what)

        title = html.var("title")
        if not title:
            raise MKUserError("title", "Please supply a title.")

        roles = [ role for role in config.roles if html.var("role_" + role) ]
        
        if new:
            if what == "file" and not name.endswith(".mk"):
                name += ".mk"
            newpath = g_folder["path"] + (name,)
            new_thing = { 
                "name"  : name,
                "path"  : newpath,
                "title" : title, 
                "roles" : roles,
            }
            if what == "folder":
                new_thing.update({ 
                    "folders" : {},
                    "files" : {},
                })
            else:
                new_thing["num_hosts"] = 0
                g_files[newpath] = new_thing
            
            g_folder[what + "s"][name] = new_thing
            log_audit(new_thing, "new-" + what, u"Created new %s %s" % 
                    (what, title))

        else:
            the_thing["title"] = title
            the_thing["roles"] = roles

        save_folder_config()
        return "folder"


    else:
        html.begin_form("edit" + what)
        html.write('<table class="form">\n')
        
        # title
        html.write("<tr><td class=legend>Title</td><td class=content>")
        html.text_input("title", title)
        html.set_focus("title")
        html.write("</td></tr>\n")

        # folder/file name (omit this for root folder)
        if not (what == "folder" and not new and g_folder == g_root_folder):
            if what == "folder":
                html.write("<tr><td class=legend>Internal directory name<br>"
                    "<i>This is the name of subdirectory where the files and<br> "
                    "other folders will be created. You cannot change this later</i>"
                    "</td><td class=content>")
            else:
                html.write("<tr><td class=legend>Internal file name<br>"
                    "<i>This is the name of Check_MK configuration file where<br>"
                    "the hosts will be created. It well automatically get the<br>"
                    "extension <tt>.mk</tt>. Do not specify this extension here.<br>"
                    "You cannot change the file name later.</i>"
                    "</td><td class=content>")

            if new:
                html.text_input("name")
            else:
                html.write(name)

            html.write("</td></tr>\n")

        # permissions
        html.write("<tr><td class=legend>Grant access to</td><td class=content>")
        for role in config.roles:
            html.checkbox("role_" + role, role in g_folder["roles"])
            html.write(" " + role + "<br>")
        html.write("</td></tr>")

        html.write('<tr><td class="legend button" colspan=2>')
        html.button("save", "Save &amp; Finish", "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()
        

def check_wato_filename(htmlvarname, name, what):
    if what == "folder" and name in g_folder["folders"]:
        raise MKUserError(htmlvarname, "A folder with that name already exists.")
    elif what == "file" and name in g_folder["files"]:
        raise MKUserError(htmlvarname, "A file with that name already exists.")
    if not name:
        raise MKUserError(htmlvarname, "Please specify a name.")
    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(htmlvarname, "Invalid %s name. Only the characters a-z, A-Z, 0-9, _ and - are allowed." % what)

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
        html.context_button("Back", make_link_to([("mode", "folder")], g_folder["path"]))
        html.context_button("Properties", make_link_to([("mode", "editfile")], g_folder["path"], g_file["name"]))
        html.context_button("New host", make_link([("mode", "newhost")]))
        changelog_button()
    
    elif phase == "action":
        # Deletion of single hosts
        delname = html.var("_delete")
        if delname and delname in g_hosts:
            return delete_host_after_confirm(delname)

        # Move single hosts to other files
        move_to = html.var("_move_host_to")
        hostname = html.var("host")
        if move_to and hostname:
            move_host_to(hostname, move_to)

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        if html.var("_bulk_inventory"):
            return "bulkinventory"

        selected_hosts = get_hostnames_from_checkboxes()
        if len(selected_hosts) == 0:
            raise MKUserError("sel_" + hostnames[0], 
            "Please select some hosts before doing bulk operations on hosts.")

        # Deletion
        if html.var("_bulk_delete"):
            return delete_hosts_after_confirm(selected_hosts)


    elif len(g_hosts) == 0:
        html.write("There are no hosts in this file.")

    else:
        html.write("Hosts in file ")
        render_folder_path()
        html.write("<p>")

        # Show table of hosts in this file
        html.begin_form("hosts")
        html.hidden_fields()
        html.write("<table class=data>\n")
        html.write("<tr><th></th><th></th><th>Hostname</th>"
                   "<th>IP&nbsp;Address</th><th>Tags</th><th>Alias</th><th>Move To</th></tr>\n")
        odd = "odd"

        hostnames = g_hosts.keys()
        hostnames.sort()
        for hostname in hostnames:
            alias, ipaddress, tags = g_hosts[hostname]

            # Rows with alternating odd/even styles
            html.write('<tr class="data %s0">' % odd)
            odd = odd == "odd" and "even" or "odd" 

            # Check box (if none is checked, then the default is to check all)
            selected_hosts = get_hostnames_from_checkboxes()
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
            html.buttonlink(edit_url, "Edit")
            html.buttonlink(services_url, "Services")
            html.buttonlink(clone_url, "Clone")
            html.buttonlink(delete_url, "Delete")
            html.write("</td>")

            # Hostname with link to edit form
            html.write('<td><a href="%s">%s</a></td>' % (edit_url, hostname))

            # IP address and DNS lookup
            tdclass = ""
            if not ipaddress:
                try:
                    ip = socket.gethostbyname(hostname)
                    ipaddress = "%s&nbsp;(DNS)" % ip
                    tdclass = ' class="dns"'
                except:
                    ipaddress = "(hostname not resolvable!)"
                    tdclass = ' class="dnserror"'
            html.write("<td%s>%s</td>" % (tdclass, ipaddress))

            # Further static information
            html.write("<td>%s</td>" % ",&nbsp;".join(tags))
            html.write("<td class=takeall>%s</td>" % (alias and alias or ""))
            html.write("<td>")
            host_move_combo(hostname)
            html.write("</td>")
            html.write("</tr>\n")

        # bulk actions
        html.write('<tr class="data %s0">' % odd)
        html.write('<td><button class=checkall onclick="wato_check_all(\'wato_select\');return false;">X</button>')
        html.write("</td><td colspan=6>On all selected hosts:\n")
        html.button("_bulk_delete", "Delete")
        html.button("_bulk_edit", "Edit")
        html.button("_bulk_inventory", "Bulk inventory")
        host_move_combo("", "Move To: ")
        html.write("</td></tr>\n")

        html.write("</table>\n")
        html.end_form()
    
# Create list of all hosts that are select with checkboxes in the current file
def get_hostnames_from_checkboxes():
    hostnames = g_hosts.keys()
    hostnames.sort()
    selected_hosts = []
    for name in hostnames:
        if html.var("sel_" + name):
            selected_hosts.append(name)
    return selected_hosts


def render_linkinfo(linkinfo):
    if ':' in linkinfo:
        pathname, host = linkinfo.split(':', 1)
        path = tuple(pathname[1:].split("/"))
        if path in g_files:
            the_file = g_files[path]
            the_folder = find_folder(path[:-1])
            hosts = read_configuration_file(the_folder, the_file)
            if host in hosts:
                url = html.makeuri_contextless([("mode", "edithost"), ("filename", pathname), ("host", host)])
                title = host
            else:
                return host
        else:
            return host
    elif linkinfo[0] == '/':
        path = tuple(linkinfo[1:].split("/"))
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


def mode_changelog(phase):
    if phase == "title":
        return "Change log"

    elif phase == "buttons":
        html.context_button("Back", make_link([("mode", "folder")]))

    elif phase == "action":
        if html.check_transaction():
            try:
	        check_mk_automation("restart")
            except Exception, e:
                raise MKUserError(None, str(e))
            log_commit_pending() # flush logfile with pending actions
	    log_audit(None, "activate-config", "Configuration activated, monitoring server restarted")
	    return None, "The new configuration has been successfully activated."

    else:
        pending = parse_audit_log("pending")
        if len(pending) > 0:
            message = "<h1>Changes which are not yet activated:</h1>"
            message += render_audit_log(pending, "pending")
            message += '<a href="%s" class=button>Activate Changes!</a>' % \
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())])
            html.show_warning(message)
        else:
            html.write("<p>No pending changes, monitoring server is up to date.</p>")

        audit = parse_audit_log("audit")
        if len(audit) > 0:
            html.write("<b>All Changes</b>")
            html.write(render_audit_log(audit, "audit"))
        else:
            html.write("<p>Logfile is empty. No host has been created or changed yet.</p>")
        

# Form for host details (new, clone, edit)
def mode_edithost(phase, new):
    hostname = html.var("host") # may be empty in new/clone mode

    clonename = html.var("clone")
    if clonename and clonename not in g_hosts:
        raise MKGeneralException("You called this page with an invalid host name.")
    
    if clonename:
        title = "Create clone of %s" % clonename
        alias, ipaddress, tags = g_hosts[clonename]
        mode = "clone"
    elif not new and hostname in g_hosts:
        title = "Edit host " + hostname
        alias, ipaddress, tags = g_hosts[hostname]
        mode = "edit"
    else:
        title = "Create new host"
        alias, ipaddress, tags = None, None, []
        mode = "new"

    if phase == "title":
        return title

    elif phase == "buttons":
        html.context_button("Abort", make_link([("mode", "file")]))
        if not new:
            html.context_button("Services", make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "file"
            else:
                return delete_host_after_confirm(hostname)

        alias = html.var("alias")
        if not alias:
            alias = None # make sure no alias is set - not an empty one

        ipaddress = html.var("ipaddress")
        if not ipaddress: 
            ipaddress = None # make sure no IP address is set
            try:
                ip = socket.gethostbyname(hostname)
            except:
                raise MKUserError("ipaddress", "Hostname <b><tt>%s</tt></b> cannot be resolved into an IP address. "
                            "Please check hostname or specify an explicit IP address." % hostname)

        tags = set([])
        for tagno, (tagname, taglist) in enumerate(config.host_tags):
            value = html.var("tag_%d" % tagno)
            if value:
                tags.add(value)
                for entry in taglist:
                    if entry[0] == value and len(entry) > 2:
                        tags.update(entry[2]) # extra tags

        # handle clone & new
        if new:
            if not hostname:
                raise MKUserError("host", "Please specify a host name")
            elif hostname in g_hosts:
                raise MKUserError("host", "A host with this name already exists.")
            elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                raise MKUserError("host", "Invalid host name: must contain only characters, digits, dash, underscore and dot.")

        if hostname:
            go_to_services = html.var("services")
            if html.check_transaction():
                g_hosts[hostname] = (alias, ipaddress, tags)
                if new:
                    message = "Created new host %s." % hostname
                    log_pending(hostname, "create-host", message) 
                    g_file["num_hosts"] += 1
                else:
                    log_pending(hostname, "edit-host", "Edited properties of host [%s]" % hostname)
                write_the_configuration_file()
            if new:
                return go_to_services and "firstinventory" or "file"
            else:
                return go_to_services and "inventory" or "file"


    else:
        html.begin_form("edithost")
        html.write('<table class="form bg_brighten">\n')

        # host name
        html.write("<tr><td class=legend>Hostname</td><td class=content>")
        if hostname and mode == "edit":
            html.write(hostname)
        else:
            html.text_input("host")
            html.set_focus("host")
        html.write("</td></tr>\n")

        # alias
        html.write("<tr><td class=legend>Alias<br><i>(optional)</i></td><td class=content>")
        html.text_input("alias", alias)
        html.write("</td></tr>\n")

        # IP address
        html.write("<tr><td class=legend>IP-Address<br>"
                "<i>Leave empty for automatic<br>"
                "IP address lookup via DNS</td><td class=content>")
        html.text_input("ipaddress", ipaddress)
        html.write("</td></tr>\n")

        # Host tags
        found_tags = []
        for tagno, (tagname, taglist) in enumerate(config.host_tags):
            # get current value of tag
            tagvalue = None
            duplicate = False
            for entry in taglist:
                tag = entry[0]
                descr = entry[1]
                if tag in tags:
                    if tagvalue:
                        duplicate = True
                    tagvalue = tag 

            tagvar = "tag_%d" % tagno
            html.write("<tr><td class=legend>%s</td>" % tagname)
            html.write("<td class=content>")
            html.select(tagvar, [e[:2] for e in taglist], tagvalue)
            if duplicate: # tag not unique before editing
                html.write("(!)")
            html.write("</td></tr>\n")

        html.write('<tr><td class="legend button" colspan=2>')
        html.button("save", "Save &amp; Finish", "submit")
        if not new:
            html.button("delete", "Delete host!", "submit")
        html.button("services", "Save &amp; got to Services", "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()


def mode_inventory(phase, firsttime):
    hostname = html.var("host")
    if hostname not in g_hosts:
        raise MKGeneralException("You called this page for a non-existing host.")

    if phase == "title":
        return "Services of host %s" % hostname

    elif phase == "action":
        if html.check_transaction():
            table = check_mk_automation("try-inventory", [hostname])
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
            message = "Saved check configuration of host [%s] with %d services" % (hostname, len(active_checks)) 
            log_pending(hostname, "set-autochecks", message) 
            return new_target, message
        return "file"

    elif phase == "buttons":
        html.context_button("Host list", make_link([("mode", "file")]))
        html.context_button("Edit host", make_link([("mode", "edithost"), ("host", hostname)]))

    else:
        show_service_table(hostname, firsttime)

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
        return "Bulk service detection (inventory)"

    elif phase == "buttons":
        if html.var("_start"):
            html.context_button("Back", html.makeuri([]))
        else:
            html.context_button("Back", html.makeuri([("mode", "file")]))
        return

    elif phase == "action":
        if html.var("_item"):
            how = html.var("how")
            hostname = html.var("_item").encode("utf-8")
            try:
                counts = check_mk_automation("inventory", [how, hostname])
                result = repr([ 'continue' ] + list(counts)) + "\n"
                result += "Inventorized %s<br>\n" % hostname
            except Exception, e:
                result = repr([ 'pause', 0, 0, 0, 0, ]) + "\n"
                result += "Error during inventory of %s: %s<br>\n" % (hostname, e)
            html.write(result)
            return ""
        return

    # interactive progress is *not* done in action phase. It
    # renders the page content itself.

    if html.var("_start"):
        hostnames = get_hostnames_from_checkboxes()
        # Start interactive progress
        interactive_progress(
            hostnames,         # list of items
            "Bulk inventory",  # title
            [ ("Services added", 0), ("Services removed", 0), ("Services kept", 0), ("Total services", 0) ], # stats table
            [ ("mode", "file") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
        )

    else:
        html.begin_form("bulkinventory")
        html.hidden_fields()

        # Mode of action
        html.write("<table class=form>")
        html.write("<tr><td class=legend>Mode</td><td class=content>")
        html.radiobutton("how", "new",     True,  "Find only new services<br>")
        html.radiobutton("how", "remove",  False, "Remove obsolete services<br>")
        html.radiobutton("how", "fixall",  False, "Find new &amp; remove obsolete<br>")
        html.radiobutton("how", "refresh", False, "Refresh all services (tabula rasa)<br>")
        html.write("</td></tr>")

        # Check type (first we need a Check_MK automation service for getting the list of checktype)
        # html.write("<tr><td class=legend>Checktype</td><td class=content>")
        # selection = check_mk_automation('get-checktypes')
        # html.sorted_select("check_command", [("", "all types")] + [(x,x) for x in selection])
        # html.write("</td></tr>")

        # Start button 
        html.write('<tr><td colspan=2 class="legend button">')
        html.button("_start", "Start!")
        html.write("</tr>")

        html.write("</table>")



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
        path = f["path"]
        if len(path) > 0:
            filename = "/" + "/".join(path) + "/"
            url = "wato.py?filename=" + htmllib.urlencode(filename)
            html.write(format % (url, f["title"]))
        else:
            html.write('<a target=main href="wato.py">%s</a>' % f["title"])

        subfolders = f["folders"]
        if len(subfolders) > 0:
            html.write('<ul>')
            for sf in subfolders.values():
                render_folder(sf)
            html.write('</ul>')

    render_folder(g_root_folder)


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


def log_entry(linkinfo, action, message, logfilename):
    make_nagios_directory(conf_dir)
    if linkinfo in g_files.values():
        link = file_os_path(linkinfo)
    elif type(linkinfo) == dict and find_folder(linkinfo["path"]):
        link = file_os_path(linkinfo) + "/"
    elif linkinfo == None:
        link = "-"
    else: # hostname
        link = file_os_path(g_file) + ":" + linkinfo

    log_file = conf_dir + "/" + logfilename
    f = create_user_file(log_file, "ab")
    f.write("%d %s %s %s " % (int(time.time()), link, html.req.user, action))
    f.write(message.encode("utf-8"))
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


def check_mk_automation(command, args=[], indata=""):
    # Gather the command to use for executing --automation calls to check_mk
    # - First try to use the check_mk_automation option from the defaults
    # - When not set try to detect the command for OMD or non OMD installations
    #   - OMD 'own' apache mode or non OMD: check_mk --automation
    #   - OMD 'shared' apache mode: Full path to the binary and the defaults
    sudoline = None
    if defaults.check_mk_automation:
        commandargs = defaults.check_mk_automation.split()
        cmd = commandargs + [ command ] + args
    else:
        omd_mode, omd_site = html.omd_mode()
        if not omd_mode or omd_mode == 'own':
            commandargs = [ 'check_mk', '--automation' ]
            cmd = commandargs  + [ command ] + args
        else: # OMD shared mode
            commandargs = [ 'sudo', '/bin/su', '-', omd_site, '-c', 'check_mk --automation' ]
            cmd = commandargs[:-1] + [ commandargs[-1] + ' ' + ' '.join([ command ] + args) ]
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
    parts = folder["path"]
    if type(file) == dict:
        parts += (file["name"],)
    elif file:
        parts += (file,)

    return defaults.check_mk_configdir + "/" + "/".join(parts)

def load_folder_config():
    global g_root_folder, g_files

    path = conf_dir + "/folders.mk"
    if os.path.exists(path):
        g_root_folder = eval(file(path).read())
    else:
        g_root_folder = { 
            "name" : "", 
            "title" : "Main directory", 
            "files" : {}, 
            "folders" : {}, 
            "roles" : [ "admin" ],
        }

    # make each folder and file know its own path
    g_files = {}
    def add_path_info(path, folder):
        folder["path"] = path
        for name, subfolder in folder["folders"].items():
            subpath = path + (name,)
            add_path_info(subpath, subfolder)
        for name, subfile in folder["files"].items():
            filepath = path + (name,)
            subfile["path"] = filepath
            g_files[filepath] = subfile

    add_path_info((), g_root_folder)


def save_folder_config():
    # save, but remove redundancy before saving. Only save recursive ROOT folder,
    # omit explicit other folders. And remove redundant path information

    def clean_folder(folder):
        cleaned = dict(folder.items())
        del cleaned["path"]

        cleaned["folders"] = {}
        for name, subfolder in folder["folders"].items():
            cleaned["folders"][name] = clean_folder(subfolder)

        cleaned["files"] = {}
        for name, subfile in folder["files"].items():
            newfile = dict(subfile.items())
            del newfile["path"]
            cleaned["files"][name] = newfile

        return cleaned

    make_nagios_directory(conf_dir)
    config.write_settings_file(conf_dir + "/folders.mk", clean_folder(g_root_folder))

def find_folder(path, in_folder = None):
    if in_folder == None:
        in_folder = g_root_folder

    if len(path) == 0:
        return in_folder
    else:
        name, rest = path[0], path[1:]
        if name not in in_folder["folders"]:
            return None
        else:
            return find_folder(rest, in_folder["folders"][name])

def count_files(folder):
    num = 0
    for f in folder["files"].values():
        num += f["num_hosts"]
    for sf in folder["folders"].values():
        num += count_files(sf)
    return num

# Load all hosts from all configuration files.
def load_all_hosts(base_folder = None):
    if base_folder == None:
        base_folder = g_root_folder
    hosts = {}
    for f in base_folder["files"].values():
        hosts.update(read_configuration_file(base_folder, f))
    for f in base_folder["folders"].values():
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
        }
        execfile(path, variables, variables)
        for h in variables["all_hosts"]:
            parts = h.split('|')
            hostname = parts[0]
            tags = set([ tag for tag in parts[1:] if tag != 'wato' and not tag.endswith('.mk') ])
            ipaddress = variables["ipaddresses"].get(hostname)
            aliases = host_extra_conf(hostname, variables["extra_host_conf"]["alias"]) 
            if len(aliases) > 0:
                alias = aliases[0]
            else:
                alias = None
            hosts[hostname] = (alias, ipaddress, tags)
    return hosts


def write_the_configuration_file():
    write_configuration_file(g_folder, g_file, g_hosts)
    save_folder_config()


def write_configuration_file(folder, thefile, hosts):
    all_hosts = []
    ipaddresses = {}
    aliases = []
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        alias, ipaddress, tags = hosts[hostname]
        if alias:
            aliases.append((alias, [hostname]))
        all_hosts.append("|".join([hostname] + list(tags) + [ thefile["name"], 'wato' ]))
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
              (thefile["name"], thefile["name"]))

def delete_configuration_file(folder, thefile):
    path = make_config_path(folder, thefile)
    if os.path.exists(path):
        os.remove(path)


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
        raise MKGeneralException("You called this page with an invalid WATO filename!")

    parts = g_pathname[1:].split("/")
    path = tuple(parts[:-1])
    filename = parts[-1]

    g_folder = find_folder(path)
    if not g_folder:
        raise MKGeneralException('You called this page with a non-existing folder! '
                                 'Go back to the <a href="wato.py">main index</a>.')
    if filename:
        if filename not in g_folder["files"]:
            raise MKGeneralException('You called this page with a non-existing file! '
                                     'Go back to the <a href="wato.py">main index</a>.')

        g_file = g_folder["files"][filename]
        if config.role not in g_file["roles"]:
            raise MKAuthException("You have no permissions on this configuration file!")

    else:
        g_file = None


# Create link keeping the context to the current folder / file
def make_link(vars):
    folder_path = g_folder["path"]

    if len(folder_path) > 0:
        os_path = "/" + "/".join(folder_path) + "/"
    else:
        os_path = "/"

    if g_file:
        os_path += g_file["name"]

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

def changelog_button():
    pending = parse_audit_log("pending")
    buttontext = "ChangeLog"
    if len(pending) > 0:
        buttontext = "<b>%s (%d)</b>" % (buttontext, len(pending))
        hot = True
    else:
        hot = False
    html.context_button(buttontext, make_link([("mode", "changelog")]), hot)


def show_service_table(hostname, firsttime):
    # Read current check configuration
    table = check_mk_automation("try-inventory", [hostname])
    table.sort()

    html.begin_form("checks", None, "POST")
    fixall = 0
    for entry in table:
        if entry[0] == 'new' and not html.has_var("_activate_all") and not firsttime:
            html.button("_activate_all", "Activate missing")
            fixall += 1
            break
    for entry in table:
        if entry[0] in [ 'obsolete', 'vanished', ]:
            html.button("_cleanup", "Remove exceeding")
            fixall += 1
            break
    if fixall == 2:
        html.button("_fixall", "Fix all missing/exceeding")


    html.button("_save", "Save manual check configuration")
    html.hidden_fields()
    html.write("<table class=data>\n")

    for state_name, state_type, checkbox in [ 
        ( "Available (missing) services", "new", firsttime ),
        ( "Already configured services", "old", True, ),
        ( "Obsolete services (being checked, but should be ignored)", "obsolete", True ),
        ( "Ignored services (configured away by admin)", "ignored", False ),
        ( "Vanished services (checked, but no longer exist)", "vanished", True ),
        ( "Manual services (defined in main.mk)", "manual", None ),
        ( "Legacy services (defined in main.mk)", "legacy", None )
        ]:
        first = True
        trclass = "even"
        for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
            if state_type != st:
                continue
            if first:
                html.write('<tr class=groupheader><td colspan=7><br>%s</td></tr>\n' % state_name)
                html.write("<tr><th>Status</th><th>Checktype</th><th>Item</th>"
                           "<th>Service Description</th><th>Current check</th><th></th></tr>\n")
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
    if not html.transaction_valid():
        return None  # Browser reload

    wato_html_head("Confirm host deletion")
    c = html.confirm("Do you really want to delete the host <tt>%s</tt>?" % delname)
    if c:
        del g_hosts[delname]
        g_file["num_hosts"] -= 1
        write_the_configuration_file()
        log_pending(delname, "delete-host", "Deleted host %s" % delname)
        check_mk_automation("delete-host", [delname])
        return "file"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_hosts_after_confirm(hosts):
    wato_html_head("Confirm deletion of %d hosts" % len(hosts))
    c = html.confirm("Do you really want to delete the %d selected hosts?" % len(hosts))
    if c:
        for delname in hosts:
            del g_hosts[delname]
            g_file["num_hosts"] -= 1
            check_mk_automation("delete-host", [delname])
            log_pending(delname, "delete-host", "Deleted host %s" % delname)
        write_the_configuration_file()
        return "file", "Successfully deleted %d hosts" % len(hosts)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def delete_folder_after_confirm(del_folder):
    wato_html_head("Confirm folder deletion")
    c = html.confirm("Do you really want to delete the folder <tt>%s</tt> (%s)?" 
        % (file_os_path(del_folder), del_folder["title"]))
    if c:
        del g_folder["folders"][del_folder["name"]]
        try:
            os.rmdir(make_conig_path(del_folder))
        except:
            pass

        save_folder_config()
        log_audit(file_os_path(del_folder), "delete-folder", "Deleted empty folder %s"% file_os_path(del_folder))
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 


def delete_file_after_confirm(del_file):
    wato_html_head("Confirm file deletion")
    c = html.confirm("Do you really want to delete the configuration file <tt>%s</tt> (%s), "
                    "which is containing %d hosts?" % (file_os_path(del_file), del_file["title"], del_file["num_hosts"]))
    if c:
        hosts = read_configuration_file(g_folder, del_file)
        for delname in hosts:
            check_mk_automation("delete-host", [delname])
        log_pending(del_file, "delete-file", "Deleted file %s" % del_file["title"])
        del g_files[del_file["path"]]
        del g_folder["files"][del_file["name"]]
        delete_configuration_file(g_folder, del_file)
        save_folder_config()
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 


def file_os_path(f):
    return "/" + "/".join(f["path"]) 

g_html_head_open = False

def wato_html_head(title):
    global g_html_head_open
    g_html_head_open = True
    html.header("Check_MK WATO - " + title)
    html.write("<div class=wato>\n")

def host_move_combo(host = None, title = ""):
    other_files = []
    for path, afile in g_files.items():
        if config.role in afile["roles"] and afile != g_file:
            os_path = "/" + "/".join(path)
            other_files.append((os_path, "%s (%s)" % (afile["title"], os_path)))

    if len(other_files) > 0:
        if title:
            html.write(title)
        selections = [("", "(select file)")] + other_files 
        if host:
            html.hidden_field("host", host)
            uri = html.makeuri([("host", host), ("_transid", html.current_transid() )])
            html.select(None, selections, "", 
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri);
        else:
            html.select("_bulk_moveto", selections, "")


def move_host_to(hostname, target_filename):
    path = tuple(target_filename[1:].split('/'))
    
    if path not in g_files: # invalid file
        return

    if hostname not in g_hosts: # non-existant host
        return

    target_file = g_files[path]
    if target_file == g_file:
        return # target-file is source-file

    folder_path = path[:-1]
    target_folder = find_folder(folder_path)
    if not target_folder:
        return

    if config.role in target_file["roles"]:
        hosts = read_configuration_file(target_folder, target_file)
        hosts[hostname] = g_hosts[hostname]
        target_file["num_hosts"] += 1
        g_file["num_hosts"] -= 1
        del g_hosts[hostname]
        write_configuration_file(target_folder, target_file, hosts)
        write_the_configuration_file()
        log_audit(hostname, "move-host", "Moved host from %s to %s" %
            (file_os_path(g_file), file_os_path(target_file)))

def render_folder_path():

    def render_component(p, title):
        html.write('<a href="%s">%s</a> / ' % (make_link_to([], path), title))

    path = ()
    for p in g_folder["path"]:
        render_component(path, find_folder(path)["title"])
        path += (p,)

    if g_file:
        render_component(g_folder["path"], g_folder["title"])
        html.write(g_file["title"])
    else:
        html.write(g_folder["title"])

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
    html.write("<script type='text/javascript' src='js/wato.js'></script>")
    html.write("<table class=progress>")
    html.write("<tr><th>%s</th></tr>" % title)
    html.write("<tr><td class=log id=progress_log></td></tr>")
    html.write("<tr><td class=bar>")
    html.write("  <table id=progress_bar><tr><td></td><td></td></tr></table>")
    html.write("  </table>")
    html.write("</td></tr>")
    html.write("<tr><td class=stats>")
    html.write("  <table>")
    for num, (label, value) in enumerate(stats):
        html.write("    <tr><th>%s</th><td id='progress_stat%d'>%d</td></tr>" % (label, num, value))
    html.write("  </table>")
    html.write("</td></tr>")
    html.write("<tr><td class=buttons>Und hier die Knöpfe</td></tr>")
    html.write("</table>")
    html.write("<button id='progress_finished' style='display:none'>Finish!</button>")
    json_items = '[ %s ]' % ','.join([ "'" + h + "'" for h in items ])
    html.javascript('progress_scheduler("%s", "%s", 50, %s);' % (html.var('mode'), html.makeuri([]), json_items))

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
   "bulkinventory"  : mode_bulk_inventory,
   "changelog"      : mode_changelog,
   "file"           : mode_file,
}

extra_buttons = [
]


# Load all wato plugins
plugins_path = defaults.web_dir + "/plugins/wato"
for fn in os.listdir(plugins_path):
    if fn.endswith(".py"):
        execfile(plugins_path + "/" + fn)

if defaults.omd_root:
    local_plugins_path = defaults.omd_root + "/local/share/check_mk/web/plugins/wato"
    if os.path.exists(local_plugins_path):
        for fn in os.listdir(local_plugins_path):
            if fn.endswith(".py"):
                execfile(local_plugins_path + "/" + fn)

