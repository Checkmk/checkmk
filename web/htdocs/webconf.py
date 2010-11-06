#!/usr/bin/python

from mod_python import importer
config = importer.import_module("config", path = ["/omd/sites/webconf/share/check_mk/web/htdocs"])
# config = importer.import_module("config")

import sys, pprint
from lib import *
# import config


config.declare_permission("use_webconf",
     "Use Webconfiguration",
     "Only with this permission, users are allowed to use Check_MK web configuration GUI.",
     [ "admin", ])

def index(h):
    global html
    html = h
    filename = html.var("filename")
    if not filename:
        raise MKGeneralException("You called this page without a filename!")
    title = None
    for fn, t, roles in config.config_files:
        if fn == filename:
            title = t
            break
        
    if not title:
        raise MKGeneralException("No config file <tt>%s</tt> is declared in <tt>multisite.mk</tt>" % filename)

    if not config.may("use_webconf") or config.role not in roles:
        raise MKAuthException("You are not allowed to edit this configuration file!")
        
    html.header("Check_MK Configuration: " + title)
    hosts = read_configuration_file(filename)
    
    html.write("<table class=services>\n")
    html.write("<tr><th>Hostname</th><th>IP Address</th><th>Tags</th></tr>\n")
    odd = "even"
    for hostname, ipaddress, tags in hosts:
        odd = odd == "odd" and "even" or "odd" 
        html.write("<tr class=\"data %s0\"><td>%s</td>" % (odd, hostname))
        html.write("<td>%s</td>" % (ipaddress and ipaddress or "(DNS)"))
        html.write("<td>%s</td>" % ", ".join(tags))
        html.write("</tr>\n")
    html.write("</table>\n")


    write_configuration_file(filename, hosts)
    html.footer()


def read_configuration_file(filename):
    path = defaults.check_mk_configdir + "/" + filename

    if os.path.exists(path):
        variables = {
            "all_hosts" : [],
            "ipaddresses" : {},
        }
        execfile(path, variables, variables)
        hosts = []
        for h in variables["all_hosts"]:
            parts = h.split('|')
            hostname = parts[0]
            tags = parts[1:]
            ipaddress = variables["ipaddresses"].get(hostname)
            hosts.append((hostname, ipaddress, tags))
        return hosts
    else:
        return []

def write_configuration_file(filename, hosts):
    all_hosts = []
    ipaddresses = {}
    for hostname, ipaddress, tags in hosts:
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
