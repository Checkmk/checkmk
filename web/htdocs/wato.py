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

#!/usr/bin/python
# encoding: utf-8

# -----------------------------------------------------------------
#       ___       _ _   
#      |_ _|_ __ (_) |_ 
#       | || '_ \| | __|
#       | || | | | | |_ 
#      |___|_| |_|_|\__|
#                       
# -----------------------------------------------------------------

import config

import sys, pprint, socket, re, subprocess, time
from lib import *
import htmllib

# Problem hier: Das ganze funktioniert noch nicht in der local/-Hierarchie
# from mod_python import importer
# config = importer.import_module("config", path = ["/omd/sites/wato/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

config.declare_permission("use_wato",
     "Use WATO",
     "This permissions allows users to use WATO - Check_MK's Web Administration Tool.<br>"
     "Please make sure, that they also have the permission for the WATO snapin.",
     [ "admin", "user" ])

conf_dir = defaults.var_dir + "/wato"

# -----------------------------------------------------------------
#       __  __       _       
#      |  \/  | __ _(_)_ __  
#      | |\/| |/ _` | | '_ \ 
#      | |  | | (_| | | | | |
#      |_|  |_|\__,_|_|_| |_|
#                            
# -----------------------------------------------------------------
# Der Seitenaufbau besteht aus folgenden Teilen:
# 1. Kontextbuttons (wo kann man von hier aus hinspringen, ohne Aktion)
# 2. Verarbeiten einer Aktion, falls eine gültige Transaktion da ist
# 3. Anzeigen von Inhalten
#
# Der Trick: welche Inhalte angezeigt werden, hängt vom Ausgang der Aktion
# ab. Wenn man z.B. bei einem Host bei "Create new host" auf [Save] klickt,
# dann kommt bei Erfolg die Inventurseite, bei Misserfolg bleibt man
# auf der Neuanlegen-Seite.
#
# Dummerweise kann ich aber die Kontextbuttons erst dann anzeigen, wenn
# ich den Ausgang der Aktion kenne. Daher wird zuerst die Aktion ausgeführt,
# welche aber keinen HTML-Code ausgeben darf.

def page_handler(h):
    global html
    html = h

    if not config.may("use_wato"):
        raise MKAuthException("You are not allowed to use WATO!")

    load_folder_config()

    global g_folder, g_file
    g_folder, g_file = get_folder_and_file()
    if g_file:
        title = g_file["title"]
        read_the_configuration_file()
    else:
        title = g_folder["title"]

    modefuncs = {
        "folder"         : mode_folder,
        "newfolder"      : lambda phase: mode_editfolder(phase, True),
        "editfolder"     : lambda phase: mode_editfolder(phase, False),
        "newhost"        : lambda phase: mode_edithost(phase, True),
        "edithost"       : lambda phase: mode_edithost(phase, False),
        "firstinventory" : lambda phase: mode_inventory(phase, True),
        "inventory"      : lambda phase: mode_inventory(phase, False),
        "changelog"      : mode_changelog,
        "hostindex"      : mode_hostindex,
    }
    default_mode = g_file and mode_hostindex or mode_folder
    modefunc = modefuncs.get(html.var("mode"), default_mode)

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
                    html.write("</div>")
                    html.footer()
                    return
                modefunc = modefuncs.get(newmode, mode_hostindex)
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


# -----------------------------------------------------------------
#       ____                       
#      |  _ \ __ _  __ _  ___  ___ 
#      | |_) / _` |/ _` |/ _ \/ __|
#      |  __/ (_| | (_| |  __/\__ \
#      |_|   \__,_|\__, |\___||___/
#                  |___/           
# -----------------------------------------------------------------

def mode_folder(phase):
    if phase == "title":
        return "Folder contents"

    elif phase == "buttons":
        html.context_button("New folder", make_link([("mode", "newfolder")]))
        html.context_button("New file", make_link([("mode", "newfile")]))
        changelog_button()
    
    elif phase == "action":
        pass

    else:
        html.write("Contents of folder ")
        path = ()
        for p in g_folder["path"]:
            html.write('<a href="%s">%s</a> / ' % (make_link([], path), g_folders[path]["title"]))
            path += (p,)
        html.write(g_folder["title"])
        html.write("<p>")


        if len(g_folder["folders"]) > 0:
            html.write("<b>Subfolders</b>")
            html.write("<table class=data>\n")
            html.write("<tr><th>Title</th><th>Actions</th>\n")
            odd = "even"
            for subfolder in g_folder["folders"].values():
                name = subfolder["name"]
                path = subfolder["path"]
                edit_url     = make_link([("mode", "editfolder")], path)
                delete_url   = make_action_link([("mode", "folder"), ("_delete", name)], path)
                enter_url    = make_link([], path)

                odd = odd == "odd" and "even" or "odd" 
                html.write('<tr class="data %s0">' % odd)

                html.write('<td class=takefall><a href="%s">%s</a></td>' % 
                            (enter_url, subfolder["title"]))
                html.write("<td>")
                html.buttonlink(edit_url, "Edit")
                html.buttonlink(delete_url, "Delete")
                html.write("</td>")
                html.write("</tr>")
            html.write("</table>")


def mode_editfolder(phase, new):
    # In editing mode, we always edit the *current* folder, i.e. that
    # one g_folder points to. In new mode the new folder is created
    # within g_folder
    if new:
        title = "Create new folder"
        name, title, roles = None, None, []
        mode = "new"
    else:
        title = "Edit folder " + g_folder["name"]
        name = g_folder["name"]
        title = g_folder["title"]
        roles = g_folder["roles"]
        mode = "edit"

    if phase == "title":
        return title

    elif phase == "buttons":
        # Abort-Button must go to parent!
        global g_folder
        old_g_folder = g_folder
        g_folder = g_folders[g_folder["path"][:-1]]
        html.context_button("Abort", make_link([("mode", "folder")]))
        g_folder = old_g_folder

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_folder_after_confirm(hostname)

        if new:
            name = html.var("name")
            if name in g_folder["folders"]:
                raise MKUserError("name", "A folder with that name already exists")
            if not re.match("^[-a-z0-9A-Z_]*$", name):
                raise MKUserError("name", "Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed.")

        else:
            name = g_folder["name"]


        title = html.var("title")
        if not title:
            raise MKUserError("title", "Please supply a title for your folder")

        roles = [ role for role in config.roles if html.var("role_" + role) ]
        
        if new:
            newpath = g_folder["path"] + (name,)
            new_folder = { 
                "name" : name,
                "path" : newpath,
                "title" : title, 
                "roles" : roles,
                "folders" : {},
                "files" : {},
            }
            g_folder["folders"][name] = new_folder
            g_folders[newpath] = new_folder
            global g_folder
            g_folder = new_folder

        else:
            g_folder["title"] = title
            g_folder["roles"] = roles

        save_folder_config()
        return "folder"


    else:
        html.begin_form("editfolder")
        html.write('<table class="form bg_brighten">\n')
        
        # title
        html.write("<tr><td class=legend>Title</td><td class=content>")
        html.text_input("title", title)
        html.write("</td></tr>\n")

        # folder name
        html.write("<tr><td class=legend>Internal directory name<br>"
        "<i>This is the name of subdirectory where the files and<br> "
        "other folders will be created. You cannot change this later</i>"
        "</td><td class=content>")
        if new:
            html.text_input("name")
            html.set_focus("name")
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
        if not new:
            html.button("delete", "Delete this folder!", "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()
        

def mode_hostindex(phase):
    if phase == "title":
        return "Hosts list"

    elif phase == "buttons":
        html.context_button("Create new host", make_link([("mode", "newhost")]))
        changelog_button()
    
    elif phase == "action":
        # Deletion of hosts
        delname = html.var("_delete")
        if delname and delname in g_hosts:
            return delete_host_after_confirm(delname)

        move_to = html.var("_move_host_to")
        hostname = html.var("host")
        if move_to and hostname:
            move_host_to(hostname, move_to)

    else:
        # Show table of hosts in this file
        html.write("<table class=data>\n")
        html.write("<tr><th></th><th>Hostname</th>"
                   "<th>IP&nbsp;Address</th><th>Tags</th><th>Alias</th><th>Move To</th></tr>\n")
        odd = "even"

        hostnames = g_hosts.keys()
        hostnames.sort()
        for hostname in hostnames:
            alias, ipaddress, tags = g_hosts[hostname]
            edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
            services_url = make_link([("mode", "inventory"), ("host", hostname)])
            clone_url    = make_link([("mode", "newhost"), ("clone", hostname)])
            delete_url   = make_action_link([("mode", "hostindex"), ("_delete", hostname)])

            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)
    
            html.write("<td>")
            html.buttonlink(edit_url, "Edit")
            html.buttonlink(services_url, "Services")
            html.buttonlink(clone_url, "Clone")
            html.buttonlink(delete_url, "Delete")
            html.write("</td>")
            html.write('<td><a href="%s">%s</a></td>' % (edit_url, hostname))
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
            html.write("<td>%s</td>" % ",&nbsp;".join(tags))
            html.write("<td class=takeall>%s</td>" % (alias and alias or ""))
            html.write("<td>")
            host_move_combo(hostname)
            html.write("</td>")
            html.write("</tr>\n")

        html.write("</table>\n")
    

def parse_host_names(line):
    newline = ""
    in_hostname = False
    hostname = ""
    for c in line:
        if c == '[':
            in_hostname = True
        elif c == ']':
            in_hostname = False
            newline += host_link(hostname)
        elif in_hostname:
            hostname += c
        else:
            newline += c
    return newline


def host_link(hostname):
    if hostname in g_hosts:
        return '<a href="%s">%s</a>' % (make_link([("mode", "edithost"), ("host", hostname)]), hostname)
    else:
        return hostname


def render_audit_log(log, what, with_filename = False):
    htmlcode = '<table class="wato auditlog bg_brighten">'
    even = "even"
    for t, filename, user, action, text in log:
        text = parse_host_names(text)
        even = even == "even" and "odd" or "even"
        htmlcode += '<tr class="%s0">' % even
        if with_filename:
            if filename != g_filename:
                htmlcode += '<td><a href="wato.py?mode=changelog&filename=%s">%s</a></td>' % (filename, filename)
            else:
                htmlcode += '<td>%s</td>' % filename
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
        html.context_button("Create new host", make_link([("mode", "newhost")]))
        html.context_button("Host list", make_link([("mode", "hostindex")]))

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
            message += render_audit_log(pending, "pending", True)
            message += '<a href="%s" class=button>Activate Changes!</a>' % \
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())])
            html.show_warning(message)
        else:
            html.write("<p>No pending changes, monitoring server is up to date.</p>")

        audit = parse_audit_log("audit")
        if len(audit) > 0:
            html.write("<b>Audit log of configuration file %s</b><br>" % g_filename)
            html.write(render_audit_log(audit, "audit", False))
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
        html.context_button("Abort", make_link([("mode", "hostindex")]))
        if not new:
            html.context_button("Services", make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "hostindex"
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
                write_the_configuration_file()
                if new:
                    message = "Created new host [%s]." % hostname
                    log_pending(hostname, "create-host", message) 
                else:
                    log_pending(hostname, "edit-host", "Edited properties of host [%s]" % hostname)
            if new:
                return go_to_services and "firstinventory" or "hostindex"
            else:
                return go_to_services and "inventory" or "hostindex"


    else:
        html.begin_form("edithost")
        html.write('<table class=form>\n')

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
            new_target = "hostindex"
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
        return "hostindex"

    elif phase == "buttons":
        html.context_button("Host list", make_link([("mode", "hostindex")]))
        html.context_button("Edit host", make_link([("mode", "edithost"), ("host", hostname)]))

    else:
        show_service_table(hostname, firsttime)


# -----------------------------------------------------------------
#       _   _      _                     
#      | | | | ___| |_ __   ___ _ __ ___ 
#      | |_| |/ _ \ | '_ \ / _ \ '__/ __|
#      |  _  |  __/ | |_) |  __/ |  \__ \
#      |_| |_|\___|_| .__/ \___|_|  |___/
#                   |_|                  
#   
# -----------------------------------------------------------------

def log_entry(hostname, action, message, logfilename):
    make_nagios_directory(conf_dir)
    log_dir = conf_dir + "/" + g_filename
    make_nagios_directory(log_dir)
    log_file = log_dir + "/" + logfilename
    create_user_file(log_file, "a").write("%d %s %s %s %s\n" % 
            (int(time.time()), g_filename, html.req.user, action, message))


def log_audit(hostname, what, message):
    log_entry(hostname, what, message, "audit.log")


def log_pending(hostname, what, message):
    log_entry(hostname, what, message, "../pending.log")
    log_entry(hostname, what, message, "audit.log")

def log_commit_pending():
    pending = conf_dir + "/pending.log"
    if os.path.exists(pending):
        os.remove(pending)

def parse_audit_log(what):
    if what == "pending":
        path = "%s/%s.log" % (conf_dir, what)
    else:
        path = "%s/%s/%s.log" % (conf_dir, g_filename, what)
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip()
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
        parts.append(file["name"])
    elif file:
        parts.append(file)

    return defaults.check_mk_configdir + "/" + "/".join(parts)

def read_the_configuration_file():
    global g_hosts
    g_hosts = read_configuration_file(g_folder, g_file)

def read_configuration_file(folder, file):
    hosts = {}

    path = make_config_path(folder, file)
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


def load_folder_config():
    global g_folders
    path = config.config_dir + "/watofolders.mk"
    if os.path.exists(path):
        g_folders = eval(file(path).read())
    else:
        g_folders = { () : { 
            "path" : (), 
            "name" : "", 
            "title" : "ROOT", 
            "files" : {}, 
            "folders" : {}, 
            "roles" : [ "admin" ] } 
        }


def save_folder_config():
    config.write_settings_file(config.config_dir + "/watofolders.mk", g_folders)


def write_the_configuration_file():
    write_configuration_file(g_filename, g_hosts)


def write_configuration_file(filename, hosts):
    all_hosts = []
    ipaddresses = {}
    aliases = []
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        alias, ipaddress, tags = hosts[hostname]
        if alias:
            aliases.append((alias, [hostname]))
        all_hosts.append("|".join([hostname] + list(tags) + [ filename, 'wato' ]))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    path = defaults.check_mk_configdir + "/" + filename
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
              "  ('%s', [ 'wato', '%s' ], ALL_HOSTS, [ 'Check_MK inventory' ] ) ]\n" % (filename, filename))


# This is a dummy implementation which works without tags
# and implements only a special case of Check_MK's real logic.
def host_extra_conf(hostname, conflist):
    for value, hostlist in conflist:
        if hostname in hostlist:
            return [value]
    return []

def get_folder_and_file():
    path = html.var("filename", "/")
    if path[0] != '/' :
        raise MKGeneralException("You called this page with an invalid WATO filename!")

    parts = path[1:].split("/")
    path = tuple(parts[:-1])
    filename = parts[-1]

    if path not in g_folders:
        raise MKGeneralException('You called this page with an non-existing folder!'
                                 'Go back to the <a href="wato.py">main index</a>')

    the_folder = g_folders[path]
    the_folder["path"] = path
    if not filename:
        return the_folder, None

    html.write("parts: %s, path: %r, filename: %r, keyes: %r" % \
    (parts, path, filename, the_folder.keys()))
    if not filename in the_folder["files"]:
        raise MKGeneralException('You called this page with an non-existing file! '
                                 'Go back to the <a href="wato.py">main index</a>')

    the_file = the_folder["files"][filename]
    the_file["name"] = filename
    if config.role not in the_file["roles"]:
        raise MKAuthException("You have no permissions on this configuration file!")
    return the_folder, the_file 


def make_link(vars, path = None):
    if path == None:
        path = g_folder["path"]

    if len(path) > 0:
        filename = "/" + "/".join(path) + "/"
    else:
        filename = "/"

    if g_file:
        filename += g_file["name"]
    vars = vars + [ ("filename", filename) ]
    return html.makeuri_contextless(vars)


def make_action_link(vars, path = None):
    return make_link(vars + [("_transid", html.current_transid())], path)


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
        write_the_configuration_file()
        log_pending(delname, "delete-host", "Deleted host [%s]" % delname)
        check_mk_automation("delete-host", [delname])
        return "hostindex"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def wato_html_head(title):
    html.header("Check_MK WATO - " + title)
    html.write("<div class=wato>\n")

def host_move_combo(host):
    other_files = []
    for filename, title, roles in config.config_files:
        if config.role in roles and filename != g_filename:
            other_files.append((filename, title))
    if len(other_files) > 0:
        html.hidden_field("host", host)
        uri = html.makeuri([("host", host), ("_transid", html.current_transid() )])
        html.select(None, [("", "(select file)")] + other_files, 
                "", 
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri);

def move_host_to(hostname, target_filename):
    if target_filename == g_filename or hostname not in g_hosts:
        return

    # Check permissions
    for filename, title, roles in config.config_files:
        if config.role in roles and filename == target_filename:
            hosts = read_configuration_file(target_filename)
            hosts[hostname] = g_hosts[hostname]
            del g_hosts[hostname]
            write_configuration_file(target_filename, hosts)
            write_the_configuration_file()

