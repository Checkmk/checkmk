#!/usr/bin/python

from mod_python import importer
import config
#config = importer.import_module("config", path = ["/omd/sites/webconf/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

import sys, pprint, socket, re
from lib import *
import htmllib
# import config


config.declare_permission("use_webconf",
     "Use Webconfiguration",
     "Only with this permission, users are allowed to use Check_MK web configuration GUI.",
     [ "admin", ])


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

    # Deletion of entries
    delname = html.var("_delete")
    if delname and delname in hosts and html.confirm("Do you really want to delete the host <tt>%s</tt>?" % delname):
        del hosts[delname]
        write_configuration_file(filename, hosts)

    # Form for creating a new host
    html.begin_context_buttons()
    html.context_button("Create new host", "webconf_edithost.py?filename=" + filename)
    html.end_context_buttons()
    
    # Show table of hosts in this file
    html.write("<table class=services>\n")
    html.write("<tr><th>Hostname</th><th>IP Address</th><th>Tags</th><th>Actions</th></tr>\n")
    odd = "even"

    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        ipaddress, tags = hosts[hostname]
        edit_url = "webconf_edithost.py?filename=%s&host=%s" % (filename, hostname)
        clone_url = "webconf_edithost.py?filename=%s&clone=%s" % (filename, hostname)
        delete_url = "webconf.py?filename=%s&_delete=%s" % (filename, hostname)
        odd = odd == "odd" and "even" or "odd" 
        html.write("<tr class=\"data %s0\"><td>%s</td>" % (odd, hostname))
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


def read_configuration_file(filename):
    path = defaults.check_mk_configdir + "/" + filename

    if os.path.exists(path):
        variables = {
            "all_hosts" : [],
            "ipaddresses" : {},
        }
        execfile(path, variables, variables)
        hosts = {}
        for h in variables["all_hosts"]:
            parts = h.split('|')
            hostname = parts[0]
            tags = parts[1:]
            ipaddress = variables["ipaddresses"].get(hostname)
            hosts[hostname] = (ipaddress, tags)
        return hosts
    else:
        return {}

def write_configuration_file(filename, hosts):
    all_hosts = []
    ipaddresses = {}
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        ipaddress, tags = hosts[hostname]
        all_hosts.append("|".join([hostname] + tags))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    path = defaults.check_mk_configdir + "/" + filename
    out = file(path, "w")
    out.write("# Written by Check_MK Webconf\n\n")
    if len(all_hosts) > 0:
        out.write("all_hosts += ")
        out.write(pprint.pformat(all_hosts))
        if len(ipaddresses) > 0:
            out.write("\n\nipaddresses.update(")
            out.write(pprint.pformat(ipaddresses))
            out.write(")")
        out.write("\n")

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
        ipaddress, tags = hosts[clonename]
        mode = "clone"
    elif hostname in hosts:
        title = "Edit host " + hostname
        ipaddress, tags = hosts.get(hostname)
        mode = "edit"
    else:
        title = "Create new host"
        ipaddress, tags = None, []
        mode = "new"


    # Form submitted
    if html.var("save") and html.check_transaction():
        try:
            ipaddress = html.var("ipaddress")
            if not ipaddress: 
                ipaddress = None
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

            hosts[hostname] = (ipaddress, tags)
            write_configuration_file(filename, hosts)
            html.set_browser_redirect(1, "webconf.py?filename=%s" % htmllib.urlencode(filename))
            html.header(title)
            html.message("Saved changes.")
            html.footer()

        except MKUserError, e:
            html.header(title)
            html.write("<div class=error>%s</div>\n" % e.message)
            html.add_user_error(e.varname, e.message)

    else:
        html.header(title)

    html.begin_form("edithost")
    html.write("<table class=form>\n")
    html.write("<tr><td class=legend>Hostname</td><td class=content>")
    if hostname and mode == "edit":
        html.write(hostname)
    else:
        html.text_input("name")
    html.write("</td></tr>\n")
    html.write("<tr><td class=legend>IP-Address<br>"
            "<i>Leave empty for automatic<br>"
            "IP address lookup via DNS</td><td class=content>")
    html.text_input("ipaddress", ipaddress)
    html.write("</td>\n")

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
