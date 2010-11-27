#!/usr/bin/python
# encoding: utf-8

# TODO: Ein Logfile pro filename anlegen, z.B. mit Unterverzeichnis
# var/web/wato/windows/audit.log

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
     "Use Webconfiguration",
     "Only with this permission, users are allowed to use Check_MK web configuration GUI.",
     [ "admin", ])

conf_dir = defaults.var_dir + "/wato/"

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

def page_index(h):
    global html
    html = h

    global g_filename
    g_filename, title = check_filename()
    read_configuration_file()

    modefuncs = {
        "newhost"   :      lambda phase: mode_edithost(phase, True),
        "edithost"  :      lambda phase: mode_edithost(phase, False),
        "firstinventory" : lambda phase: mode_inventory(phase, True),
        "inventory" :      lambda phase: mode_inventory(phase, False),
        "changelog" :      mode_changelog,
    }
    modefunc = modefuncs.get(html.var("mode"), mode_index)

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
                modefunc = modefuncs.get(newmode, mode_index)
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

def mode_index(phase):
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

    else:
        # Show table of hosts in this file
        html.write("<table class=services>\n")
        html.write("<tr><th>Hostname</th><th>Alias</th>"
                   "<th>IP Address</th><th>Tags</th><th>Actions</th></tr>\n")
        odd = "even"

        hostnames = g_hosts.keys()
        hostnames.sort()
        for hostname in hostnames:
            alias, ipaddress, tags = g_hosts[hostname]
            edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
            services_url = make_link([("mode", "inventory"), ("host", hostname)])
            clone_url    = make_link([("mode", "newhost"), ("clone", hostname)])
            delete_url   = make_action_link([("mode", "index"), ("_delete", hostname)])

            odd = odd == "odd" and "even" or "odd" 

            html.write('<tr class="data %s0"><td><a href="%s">%s</a></td>' % 
                    (odd, edit_url, hostname))
            html.write("<td>%s</td>" % (alias and alias or ""))
            tdclass = ""
            if not ipaddress:
                try:
                    ip = socket.gethostbyname(hostname)
                    ipaddress = "(DNS: %s)" % ip
                    tdclass = ' class="dns"'
                except:
                    ipaddress = "(hostname not resolvable!)"
                    tdclass = ' class="dnserror"'
            html.write("<td%s>%s</td>" % (tdclass, ipaddress))
            html.write("<td>%s</td>" % ", ".join(tags))
            html.write("<td>")
            html.buttonlink(edit_url, "Edit")
            html.buttonlink(services_url, "Services")
            html.buttonlink(clone_url, "Clone")
            html.buttonlink(delete_url, "Delete")
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


def render_audit_log(log, what):
    htmlcode = '<table class="wato auditlog %s">'
    even = "even"
    for t, user, action, text in log:
        text = parse_host_names(text)
        even = even == "even" and "odd" or "even"
        htmlcode += '<tr class="%s0"><td>%s</td><td>%s</td><td>%s</td><td width="100%%">%s</td></tr>\n' % (
                even,
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
        html.context_button("Host list", make_link([("mode", "index")]))

    elif phase == "action":
        if html.check_transaction():
            f = os.popen("check_mk -R 2>&1 >/dev/null")
            errors = f.read()
            exitcode = f.close()
            if exitcode:
                raise MKUserError(None, errors)
            else:
                log_commit_pending() # flush logfile with pending actions
                log_audit(None, "activate-config", "Configuration activated, monitoring server restarted")
                return None, "The new configuration has been successfully activated."

    else:

        pending = parse_audit_log("pending")
        if len(pending) > 0:
            message = "<h1>Changes which are not yet activated:</h1>"
            message += render_audit_log(pending, "pending")
            message += '<a href="%s" class=button>Activate Changes!</a>' % \
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid(html.req.user))])
            html.show_warning(message)
        else:
            html.write("<p>No pending changes, monitoring server is up to date.</p>")

        audit = parse_audit_log("audit")
        if len(audit) > 0:
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
    elif hostname in g_hosts:
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
        html.context_button("Abort", make_link([("mode", "index")]))
        if not new:
            html.context_button("Services", make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "index"
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

        tags = []
        for tagno, (tagname, taglist) in enumerate(config.host_tags):
            value = html.var("tag_%d" % tagno)
            if value:
                tags.append(value)

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
                write_configuration_file()
                if new:
                    message = "Created new host [%s]." % hostname
                    log_pending(hostname, "create-host", message) 
                else:
                    log_pending(hostname, "edit-host", "Edited properties of host [%s]" % hostname)
            if new:
                return go_to_services and "firstinventory" or "index"
            else:
                return go_to_services and "inventory" or "index"


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
        html.write("<tr><td class=legend>Alias<br><i>(optional</i></td><td class=content>")
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
            for tag, descr in taglist:
                if tag in tags:
                    if tagvalue:
                        duplicate = True
                    tagvalue = tag 

            tagvar = "tag_%d" % tagno
            html.write("<tr><td class=legend>%s</td>" % tagname)
            html.write("<td class=content>")
            html.select(tagvar, taglist, tagvalue)
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
            table = check_mk_automation("try-inventory", ["tcp", hostname])
            table.sort()
            active_checks = {}
            for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
                varname = "_%s_%s" % (ct, item)
                if html.var(varname, "") != "":
                    active_checks[(ct, item)] = paramstring

            check_mk_automation("set-autochecks", [hostname], active_checks)
            message = "Saved check configuration of host [%s] with %d checks" % (hostname, len(active_checks)) 
            log_pending(hostname, "set-autochecks", message) 
            return "index", message
        return "index"

    elif phase == "buttons":
        html.context_button("Host list", make_link([("mode", "index")]))
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

def log_entry(hostname, action, message, g_filename):
    make_nagios_directory(conf_dir)
    log_file = conf_dir + g_filename
    create_user_file(log_file, "a").write("%d %s %s %s\n" % 
            (int(time.time()), html.req.user, action, message))


def log_audit(hostname, what, message):
    log_entry(hostname, what, message, "audit.log")


def log_pending(hostname, what, message):
    log_entry(hostname, what, message, "pending.log")
    log_entry(hostname, what, message, "audit.log")


def log_commit_pending():
    pending = conf_dir + "pending.log"
    if os.path.exists(pending):
        os.remove(pending)

def parse_audit_log(what):
    path = "%s%s.log" % (conf_dir, what)
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip()
            entries.append(line.split(None, 3))
        entries.reverse()
        return entries
    return []


def check_mk_automation(command, args, indata=""):
    p = subprocess.Popen(["check_mk", "--automation", command ] + args, 
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.stdin.write(repr(indata))
    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    if exitcode != 0:
        raise MKGeneralException(outdata)
    return eval(outdata)


def read_configuration_file():
    global g_hosts
    g_hosts = {}
    path = defaults.check_mk_configdir + "/" + g_filename

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
            tags = [ tag for tag in parts[1:] if tag != 'wato' and not tag.endswith('.mk') ]
            ipaddress = variables["ipaddresses"].get(hostname)
            aliases = host_extra_conf(hostname, variables["extra_host_conf"]["alias"]) 
            if len(aliases) > 0:
                alias = aliases[0]
            else:
                alias = None
            g_hosts[hostname] = (alias, ipaddress, tags)
            

def write_configuration_file():
    all_hosts = []
    ipaddresses = {}
    aliases = []
    hostnames = g_hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        alias, ipaddress, tags = g_hosts[hostname]
        if alias:
            aliases.append((alias, [hostname]))
        all_hosts.append("|".join([hostname] + tags + [ g_filename, 'wato' ]))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    path = defaults.check_mk_configdir + "/" + g_filename
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
    out.write("extra_service_conf['_WATO'] = [ \n"
              "  ('hirni.mk', [ 'wato', 'hirni.mk' ], ALL_HOSTS, [ 'Check_MK inventory' ] ) ]\n")


# This is a dummy implementation which works without tags
# and implements only a special case of Check_MK's real logic.
def host_extra_conf(hostname, conflist):
    for value, hostlist in conflist:
        if hostname in hostlist:
            return [value]
    return []

def check_filename():
    filename = html.var("filename")
    if not filename:
        raise MKGeneralException("You called this page without a filename!")

    # Get alias (title) for filename
    title = None
    for fn, t, roles in config.config_files:
        if fn == filename:
            title = t
            break
    if not title:
        raise MKGeneralException("No config file <tt>%s</tt> is declared in <tt>multisite.mk</tt>" % filename)

    if not config.may("use_wato") or config.role not in roles:
        raise MKAuthException("You are not allowed to edit this configuration file!")

    return filename, title

def make_link(vars):
    vars = vars + [ ("filename", g_filename) ]
    return html.makeuri_contextless(vars)

def make_action_link(vars):
    vars = vars + [ ("filename", g_filename) ]
    return html.makeuri_contextless(vars + [("_transid", html.current_transid(html.req.user))])

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
    table = check_mk_automation("try-inventory", ["tcp", hostname])
    table.sort()

    html.begin_form("checks")
    html.button("_save", "Save check configuration")
    html.hidden_fields()
    html.write("<table class=services>\n")
    for state_name, state_type, checkbox in [ 
        ( "Available checks", "new", firsttime ),
        ( "Already configured checks", "old", True, ),
        ( "Obsolete checks (being checked, but should be ignored)", "obsolete", True ),
        ( "Ignored checks (configured away by admin)", "ignored", False ),
        ( "Vanished checks (checks, but no longer exist)", "vanished", True ),
        ( "Manual checks (defined in main.mk)", "manual", None ),
        ( "Legacy checks (defined in main.mk)", "legacy", None )
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

    c = html.confirm("Do you really want to delete the host <tt>%s</tt>?" % delname)
    if c:
        del g_hosts[delname]
        write_configuration_file()
        log_pending(delname, "delete-host", "Deleted host [%s]" % delname)
        check_mk_automation("delete-host", [delname])
        return "index"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 
