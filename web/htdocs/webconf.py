#!/usr/bin/python

from mod_python import importer
config = importer.import_module("config", path = ["/omd/sites/webconf/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

import sys, pprint
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
    hostnames = hosts.keys()
    hostnames.sort()
    
    html.write("<table class=services>\n")
    html.write("<tr><th>Hostname</th><th>IP Address</th><th>Tags</th><th>Actions</th></tr>\n")
    odd = "even"

    for hostname in hostnames:
        ipaddress, tags = hosts[hostname]
        edit_url = "webconf_edithost.py?filename=%s&host=%s" % (filename, hostname)
        odd = odd == "odd" and "even" or "odd" 
        html.write("<tr class=\"data %s0\"><td>%s</td>" % (odd, hostname))
        html.write("<td>%s</td>" % (ipaddress and ipaddress or "(DNS)"))
        html.write("<td>%s</td>" % ", ".join(tags))
        html.write('<td><a class=button href="%s">edit</a></td>' % edit_url)
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
    if not hostname:
        MKGeneralException("Host %s does not exist." % hostname)

    # Form submitted
    if html.var("save") and html.check_transaction():
        ipaddress = html.var("ipaddress")
        if not ipaddress: 
            ipaddress = None
        hosts[hostname] = (ipaddress, ['hirntag'])
        write_configuration_file(filename, hosts)
        html.set_browser_redirect(1, "webconf.py?filename=%s" % htmllib.urlencode(filename))
        html.header("Edit host")
        html.message("Saved changes.")
        html.footer()

    html.header("Edit host %s" % hostname)
    ipaddress, tags = hosts[hostname]
    html.begin_form("edithost")
    html.write("<table class=form>\n")
    html.write("<tr><td class=legend>Hostname</td><td class=content>%s</td></tr>" % hostname)
    html.write("<tr><td class=legend>IP-Address<br>"
            "<i>Leave empty for automatic<br>"
            "IP address lookup via DNS</td><td class=content>")
    html.text_input("ipaddress", ipaddress)
    html.write("</td>\n")
    html.write('<tr><td class="legend button" colspan=2>')
    html.button("save", "Save", "submit")
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.hidden_fields()
    html.end_form()
    html.footer()
