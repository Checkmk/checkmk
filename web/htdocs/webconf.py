#!/usr/bin/python

from mod_python import importer
import config
#config = importer.import_module("config", path = ["/omd/sites/webconf/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

import sys, pprint, socket, re, subprocess
from lib import *
import htmllib
# import config


config.declare_permission("use_webconf",
     "Use Webconfiguration",
     "Only with this permission, users are allowed to use Check_MK web configuration GUI.",
     [ "admin", ])


def read_configuration_file(filename):
    path = defaults.check_mk_configdir + "/" + filename

    if os.path.exists(path):
        variables = {
            "all_hosts"       : [],
            "ipaddresses"     : {},
            "extra_host_conf" : { "alias" : [] },
        }
        execfile(path, variables, variables)
        hosts = {}
        for h in variables["all_hosts"]:
            parts = h.split('|')
            hostname = parts[0]
            tags = parts[1:]
            ipaddress = variables["ipaddresses"].get(hostname)
            aliases = host_extra_conf(hostname, variables["extra_host_conf"]["alias"]) 
            if len(aliases) > 0:
                alias = aliases[0]
            else:
                alias = None
            hosts[hostname] = (alias, ipaddress, tags)
            
        return hosts
    else:
        return {}

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
        all_hosts.append("|".join([hostname] + tags))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    path = defaults.check_mk_configdir + "/" + filename
    out = file(path, "w")
    out.write("# Written by Check_MK Webconf\n\n")
    if len(all_hosts) > 0:
        out.write("all_hosts += ")
        out.write(pprint.pformat(all_hosts))
        if len(aliases) > 0:
            out.write("\n\nif 'alias' not in extra_host_conf:\n    extra_host_conf['alias'] = []\n")
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

def page_index(h):
    global html
    html = h
    filename, title = check_filename()
        
    html.header("Check_MK Configuration: " + title)
    hosts = read_configuration_file(filename)

    # Context buttons
    html.begin_context_buttons()
    html.context_button("Create new host", "webconf_edithost.py?filename=" + filename)
    html.context_button("Activate Changes!", html.makeuri([("_action", "activate")]))
    html.end_context_buttons()

    action = html.var("_action")
    if action == "activate":
        activate_configuration()

    # Deletion of entries
    delname = html.var("_delete")
    if delname and delname in hosts and html.confirm("Do you really want to delete the host <tt>%s</tt>?" % delname):
        del hosts[delname]
        write_configuration_file(filename, hosts)

    
    # Show table of hosts in this file
    html.write("<table class=services>\n")
    html.write("<tr><th>Hostname</th><th>Alias</th>"
               "<th>IP Address</th><th>Tags</th><th>Actions</th></tr>\n")
    odd = "even"

    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        alias, ipaddress, tags = hosts[hostname]
        edit_url = "webconf_edithost.py?filename=%s&host=%s" % (filename, hostname)
        clone_url = "webconf_edithost.py?filename=%s&clone=%s" % (filename, hostname)
        delete_url = "webconf.py?filename=%s&_delete=%s" % (filename, hostname)
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
    html.footer()


def page_edithost(h):
    global html
    html = h
    filename, title = check_filename()
    hosts = read_configuration_file(filename)
    hostname = html.var("host")

    # Handle Edit, Clone and New
    clonename = html.var("clone")
    if clonename:
        title = "Create clone of %s" % clonename
        alias, ipaddress, tags = hosts[clonename]
        mode = "clone"
    elif hostname in hosts:
        title = "Edit host " + hostname
        alias, ipaddress, tags = hosts.get(hostname)
        mode = "edit"
    else:
        title = "Create new host"
        alias, ipaddress, tags = None, None, []
        mode = "new"
    
    html.header(title)
    html.begin_context_buttons()
    html.context_button("Hostlist", "webconf.py?filename=" + filename)
    html.context_button("Services", "webconf_services.py?filename=%s&host=%s" % (filename, hostname))
    html.end_context_buttons()

    # Form submitted
    if html.var("save") and html.check_transaction():
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

            hosts[hostname] = (alias, ipaddress, tags)
            write_configuration_file(filename, hosts)
# html.set_browser_redirect(1, "webconf.py?filename=%s" % htmllib.urlencode(filename))
            html.message("Saved changes.")
            html.footer()

        except MKUserError, e:
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)


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
    html.buttonlink("webconf.py?filename=%s" % filename, "Cancel")
    html.button("save", "Save", "submit")
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.hidden_fields()
    html.end_form()
    html.footer()

def activate_configuration():
    f = os.popen("check_mk -R 2>&1 >/dev/null")
    errors = f.read()
    exitcode = f.close()
    if exitcode:
        html.show_error(errors)
    else:
        html.message("The new configuration has been successfully activated.")

def page_services(h):
    global html
    html = h

    filename, title = check_filename()
    hosts = read_configuration_file(filename)

    hostname = html.var("host")
    html.header("Services of " + hostname)
    html.begin_context_buttons()
    html.context_button("Hostlist", "webconf.py?filename=" + filename)
    html.context_button("Edit host", "webconf_edithost.py?filename=%s&host=%s" % (filename, hostname))
    html.end_context_buttons()

    f = os.popen("check_mk --automation try-inventory tcp '%s' 2>&1" % (hostname))
    code = f.read()
    exit_code = f.close()
    if exit_code:
        raise MKGeneralException("Error calling check_mk: %s, exit code %s" % (code, exit_code))
    table = eval(code)
    table.sort()


    html.begin_form("checks")
    html.button("add", "Add marked checks")
    html.button("remove", "Remove marked checks")
    html.hidden_fields()
    html.write("<table class=services>\n")
    for state_name, state_type, checkbox in [ 
        ( "Available checks", "new", True ),
        ( "Ignored checks (configured away by admin)", "ignored", False ),
        ( "Already configured checks", "old", False, ),
        ( "Obsolete checks (being checked, but should be ignored)", "obsolete", False ),
        ( "Vanished checks (checks, but no longer exist)", "vanished", False ),
        ( "Manual checks (defined in main.mk)", "manual", None ),
        ( "Legacy checks (defined in main.mk)", "legacy", None)
        ]:
        first = True
        trclass = "even"
        for st, ct, item, params, descr, state, output, perfdata in table:
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
                varname = "%s %s" % (ct, item)
                html.checkbox(varname, checkbox)
            html.write("</td></tr>\n")
    html.write("</table>\n")
    html.end_form()
    html.footer()




