#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | "_ \ / _ \/ __| |/ /   | |\/| | " /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

###############

def action_add_host(request):
    if html.var("create_folders"):
        create_folders = bool(int(html.var("create_folders")))
    else:
        create_folders = True

    hostname   = request.get("hostname")
    folder     = request.get("folder")
    attributes = request.get("attributes", {})

    if not hostname:
        raise MKUserError(None, "Hostname is missing")
    if not folder:
        raise MKUserError(None, "Foldername is missing")

    return g_api.add_host(hostname, folder, attributes, create_folders = create_folders)

api_actions["add_host"] = {
    "handler"         : action_add_host,
    "title"           : _("Add a host to WATO"),
    "description"     : _("This webservice allows you to add a new host."),
    "example_request" : ([("create_folders=1", _("If set to 1(default) create non-existing folders1)"))],
                         { "attributes": {
                                    "tag_criticality": "prod",
                                    "tag_agent": "cmk-agent",
                                    "alias": "Alias of testhost",
                                    "ipaddress": "127.0.0.1",
                                },
                          "folder": "server",
                          "hostname": "testhost"
                         }),
    "locking"         : True,
}

###############

def action_edit_host(request):
    hostname   = request.get("hostname")
    attributes = request.get("attributes", {})

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.edit_host(hostname, attributes)

api_actions["edit_host"] = {
    "handler"     : action_edit_host,
    "title"       : _("Edit a host in WATO"),
    "description" : _("Allows you to modify the host attributes in WATO, but can not change a hosts folder.<br>"\
                      "If you want to unset a host_tag specify it with <tt>tag_agent=False</tt>."),
    "example_request" : ([],
                         { "attributes": {
                                    "tag_agent": "snmp-only",
                                    "site": "slave"
                                },
                           "hostname": "testhost"
                         }),
    "locking"     : True,
}

###############

def action_get_host(request):
    if html.var("effective_attributes"):
        effective_attributes = bool(int(html.var("effective_attributes")))
    else:
        effective_attributes = True

    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.get_host(hostname, effective_attr = effective_attributes)

api_actions["get_host"] = {
    "handler"         : action_get_host,
    "title"           : _("Get host data from WATO"),
    "description"     : _("Returns the host_attributes of the given hostname"),
    "example_request" : ( [("effective_attributes=0", _("If set to 1 (default=0) also get attributes from parent folders"))],
                          { "hostname": "testhost" } ),
    "locking"         : False,
}

###############

def action_delete_host(request):
    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.delete_host(hostname)

api_actions["delete_host"] = {
    "handler"     : action_delete_host,
    "title"       : _("Delete host in WATO"),
    "description" : _("Deletes the given hostname in WATO"),
    "example_request" : ( [],
                          { "hostname": "testhost" } ),
    "locking"     : True,
}

###############

def action_discover_services(request):
    mode = html.var("var") and html.var("mode") or "new"

    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.discover_services(hostname, mode = mode)

api_actions["discover_services"] = {
    "handler"     : action_discover_services,
    "title"       : _("Host service discovery"),
    "description" : _("Starts a service discovery for the given hostname."),
    "example_request" : ( [("mode=new",_("Available modes: new, remove, fixall, refresh"))],
                          { "hostname": "testhost" } ),
    "locking"     : True,
}

###############

def action_activate_changes(request):
    mode = html.var("mode") and html.var("mode") or "dirty"
    if html.var("allow_foreign_changes"):
        allow_foreign_changes = bool(int(html.var("allow_foreign_changes")))
    else:
        allow_foreign_changes = False

    sites = request.get("sites")
    return g_api.activate_changes(sites = sites, mode = mode, allow_foreign_changes = allow_foreign_changes)

api_actions["activate_changes"] = {
    "handler"         : action_activate_changes,
    "title"           : _("Activate changes"),
    "description"     : _("Activates changes. The user still needs the required permissions to do so."),
    "example_request" : ( [("allow_foreign_changes=0", _("If set to 1 (default=0) proceed if there are foreign changes")),
                           ("mode=dirty", _("Available modes: dirty (only dirty sites), all (all sites), specific (use sites set in request)"))],
                          { "sites": ["slave", "localsite"] }),
    "locking"         : True,
}

