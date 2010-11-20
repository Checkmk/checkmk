#!/usr/bin/python
# encoding: utf-8

from mod_python import importer
import config
#config = importer.import_module("config", path = ["/omd/sites/webconf/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

import sys, pprint, socket, re, subprocess, time
from lib import *
import htmllib
# import config

conf_dir = defaults.var_dir + "/webconf/"


config.declare_permission("use_webconf",
     "Use Webconfiguration",
     "Only with this permission, users are allowed to use Check_MK web configuration GUI.",
     [ "admin", ])

# TODO: Ein Logfile pro filename anlegen, z.B. mit Unterverzeichnis
# var/web/webconf/windows/audit.log

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
            "all_hosts"       : [],
            "ipaddresses"     : {},
            "extra_host_conf" : { "alias" : [] },
        }
        execfile(path, variables, variables)
        for h in variables["all_hosts"]:
            parts = h.split('|')
            hostname = parts[0]
            tags = [ tag for tag in parts[1:] if tag != 'webconf' and not tag.endswith('.mk') ]
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
        all_hosts.append("|".join([hostname] + tags + [ g_filename, 'webconf' ]))
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

    if not config.may("use_webconf") or config.role not in roles:
        raise MKAuthException("You are not allowed to edit this configuration file!")

    return filename, title

def make_link(vars):
    return html.makeuri(vars)

def make_action_link(vars):
    return html.makeuri(vars + [("_transid", html.current_transid(html.req.user))])


# Der Seitenaufbau besteht aus folgenden Teilen:
# 1. Kontextbuttons (wo kann man von hier aus hinspringen, ohne Aktion)
# 2. Verarbeiten einer Aktion, falls eine gültige Transaktion da ist
# 3. Anzeigen von Inhalten
#
# Der Trick: welche Inhalte angezeigt werden, hängt vom Ausgang der Aktion
# ab. Wenn man z.B. bei einem Host bei "Create new host" auf [Save] klickt,
# dann kommt bei Erfolg die Inventurseite, bei Misserfolgt bleibt man
# auf der Neuanlegen-Seite.
#
# Dummerweise kann ich aber die Kontextbuttons erst dann anzeigen, wenn
# ich den Ausgang der Aktion kenne.

def page_index(h):
    global html
    html = h
    global g_filename
    g_filename, title = check_filename()
    read_configuration_file()

    html.header("Check_MK Configuration: " + title)
    html.write("<div class=webconf>\n")

    # Wir sind hier in einem von folgenden Zuständnen:
    # 'index':     Ohne Kontext -> wir zeigen die Liste aller Hosts an
    # 'changelog': Seite der offenen Änderungen, ChangeLog
    # 'newhost':   Anlegen eines neuen Hosts -> Maske zum Editieren des Hosts
    # 'edithost':  Editieren eines bestehenden Hosts -> Maske zum Editieren
    # 'inventory': Serviceliste eines Hosts
    mode = html.var("mode")
    if mode not in [ "newhost", "edithost", "inventory", "changelog" ]:
        mode = "index"

    if html.transaction_valid():
        mode = do_actions(mode)
        if mode == None:
            html.footer()
            return


    # Mögliche Aktionen:
    # Host löschen
    # Host anlegen
    # Host editieren/speichern
    # Servicekonfiguration speichern

    # Context buttons
    html.begin_context_buttons()

    if mode in [ "index", "changelog" ]:
        html.context_button("Create new host", make_link([("mode", "newhost")]))

    if mode == "index":
        pending = parse_audit_log("pending")
        buttontext = "ChangeLog"
        if len(pending) > 0:
            buttontext = "<b>%s (%d)</b>" % (buttontext, len(pending))
            hot = True
        else:
            hot = False
        html.context_button(buttontext, make_link([("mode", "changelog")]), hot)

    if mode == "changelog":
        html.context_button("Host list", make_link([("mode", "index")]))

    if mode in [ "newhost", "edithost", "inventory" ]:
        html.context_button("Abort", make_link([("mode", "index")]))

    html.end_context_buttons()

    # Actions (regardless of current mode)
    action = html.var("_action")
    if action == "activate" and html.transaction_valid():
        activate_configuration()

    if mode == "index":
        show_hosts_table()
    elif mode == "changelog":
        show_changelog()
    elif mode in [ "edithost", "newhost" ]:
        show_edithost()

    html.write("</div>\n")
    html.footer()

def do_actions(mode):
    hostname = html.var("host")

    # Deletion of entries
    delname = html.var("_delete")
    if delname and delname in g_hosts:
        c = html.confirm("Do you really want to delete the host <tt>%s</tt>?" % delname)
        if c:
            del g_hosts[delname]
            write_configuration_file()
            log_pending(delname, "delete-host", "Deleted host %s" % delname)
            check_mk_automation("delete-host", [delname])
        elif c == False: # not yet confirmed
            return None

    # Editing of hosts
    if html.var("save"):
        try:
            alias = html.var("alias")
            if not alias:
                alias = None # make sure no alias is set - not an empty one

            ipaddress = html.var("ipaddress")
            if not ipaddress: 
                ipaddress = None # make sure no IP address is set

            tags = []
            for tagno, (tagname, taglist) in enumerate(config.host_tags):
                value = html.var("tag_%d" % tagno)
                if value:
                    tags.append(value)

            # handle clone & new
            if not hostname:
                hostname = html.var("name")
                if not hostname:
                    raise MKUserError("name", "Please specify a host name")
                elif hostname in hosts:
                    raise MKUserError("name", "A host with this name already exists.")
                elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                    raise MKUserError("name", "Invalid host name: must contain only characters, digits, dash, underscore and dot.")

            if hostname:
                g_hosts[hostname] = (alias, ipaddress, tags)
                write_configuration_file()
                if not html.var("host"):
                    log_pending(hostname, "create-host", "Created new host %s" % hostname) 
                    mode = "inventory"
                else:
                    log_pending(hostname, "edit-host", "Edited properties of host %s" % hostname)
                    mode = "index"

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    return mode


def show_hosts_table():
    # Show table of hosts in this file
    html.write("<table class=services>\n")
    html.write("<tr><th>Hostname</th><th>Alias</th>"
               "<th>IP Address</th><th>Tags</th><th>Actions</th></tr>\n")
    odd = "even"

    hostnames = g_hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        alias, ipaddress, tags = g_hosts[hostname]
        edit_url   = make_link([("mode", "edithost"), ("host", hostname)])
        clone_url  = make_link([("mode", "newhost"), ("clone", hostname)])
        delete_url = make_action_link([("mode", "index"), ("_delete", hostname)])

        odd = odd == "odd" and "even" or "odd" 

        html.write('<tr class="data %s0"><td><a href="%s">%s</a></td>' % 
                (odd, edit_url, hostname))
        html.write("<td>%s</td>" % (alias and alias or ""))
        if not ipaddress:
            try:
                ip = socket.gethostbyname(hostname)
                ipaddress = "(DNS: %s)" % ip
            except:
                ipaddress = "(hostname not resolvable!)"
        html.write("<td>%s</td>" % ipaddress)
        html.write("<td>%s</td>" % ", ".join(tags))
        html.write("<td>")
        html.buttonlink(edit_url, "Edit")
        html.buttonlink(clone_url, "Clone")
        html.buttonlink(delete_url, "Delete")
        html.write("</td>")
        html.write("</tr>\n")

    html.write("</table>\n")
    

def show_changelog():

    def render_audit_log(log, what):
        htmlcode = '<table class="webconf auditlog %s">'
        for t, user, action, text in log:
            htmlcode += '<tr><td>%s</td><td>%s</td><td>%s</td><td width="100%%">%s</td></tr>\n' % (
                    time.strftime("%Y-%m-%d", time.localtime(float(t))),
                    time.strftime("%H:%M:%S", time.localtime(float(t))),
                    user,
                    text)
        htmlcode += "</table>"
        return htmlcode

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
        


def show_edithost():

    # Handle Edit, Clone and New
    clonename = html.var("clone")
    hostname = html.var("host")
    if clonename:
        title = "Create clone of %s" % clonename
        alias, ipaddress, tags = hosts[clonename]
        mode = "clone"
    elif hostname in g_hosts:
        title = "Edit host " + hostname
        alias, ipaddress, tags = g_hosts.get(hostname)
        mode = "edit"
    else:
        title = "Create new host"
        alias, ipaddress, tags = None, None, []
        mode = "new"
    

    html.begin_form("edithost")
    html.write('<table class=form>\n')

    # host name
    html.write("<tr><td class=legend>Hostname</td><td class=content>")
    if hostname and mode == "edit":
        html.write(hostname)
    else:
        html.text_input("name")
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
    html.buttonlink("webconf.py?filename=%s" % g_filename, "Cancel")
    html.button("save", "Save", "submit")
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.hidden_fields()
    html.end_form()

def activate_configuration():
    f = os.popen("check_mk -R 2>&1 >/dev/null")
    errors = f.read()
    exitcode = f.close()
    if exitcode:
        html.show_error(errors)
    else:
        html.message("The new configuration has been successfully activated.")
        log_commit_pending() # flush logfile with pending actions
        log_audit(None, "activate-config", "Configuration activated, monitoring server restarted")

def show_services_table(hostname):
    # Read current check configuration
    table = check_mk_automation("try-inventory", ["tcp", hostname])
    table.sort()

    # Save: add or remove marked changes
    if html.var("_save") and html.check_transaction():
        active_checks = {}
        for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
            varname = "_%s_%s" % (ct, item)
            if html.var(varname, "") != "":
                active_checks[(ct, item)] = paramstring

        check_mk_automation("set-autochecks", [hostname], active_checks)
        html.message("Saved check configuration with %d checks." % len(active_checks))
        log_pending(hostname, "set-autochecks", "Saved check configuration of host %s with %d checks" % (hostname, len(active_checks)))

        # re-read current check configuration, because it has changed
        table = check_mk_automation("try-inventory", ["tcp", hostname])
        table.sort()


    html.begin_form("checks")
    html.button("_save", "Save check configuration")
    html.hidden_fields()
    html.write("<table class=services>\n")
    for state_name, state_type, checkbox in [ 
        ( "Available checks", "new", html.has_var("_activate_available") ),
        ( "Ignored checks (configured away by admin)", "ignored", False ),
        ( "Already configured checks", "old", True, ),
        ( "Obsolete checks (being checked, but should be ignored)", "obsolete", True ),
        ( "Vanished checks (checks, but no longer exist)", "vanished", True ),
        ( "Manual checks (defined in main.mk)", "manual", None ),
        ( "Legacy checks (defined in main.mk)", "legacy", None)
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

def page_services(h):
    global html
    html = h

    filename, title = check_filename()

    hostname = html.var("host")
    html.header("Services of " + hostname)
    html.begin_context_buttons()
    html.context_button("Hostlist", "webconf.py?filename=" + filename)
    html.context_button("Edit host", "webconf_edithost.py?filename=%s&host=%s" % (filename, hostname))
    html.end_context_buttons()

    show_services_table(hostname)

    html.footer()

