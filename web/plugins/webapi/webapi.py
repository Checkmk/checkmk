#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
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

    return g_api.add_hosts([{"hostname":   hostname,
                             "folder":     folder,
                             "attributes": attributes}],
                             create_folders = create_folders)

api_actions["add_host"] = {
    "handler"         : action_add_host,
    "locking"         : True,
}

###############

def action_edit_host(request):
    hostname         = request.get("hostname")
    attributes       = request.get("attributes", {})
    unset_attributes = request.get("unset_attributes", [])

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.edit_hosts([{"hostname":         hostname,
                              "attributes":       attributes,
                              "unset_attributes": unset_attributes}])

api_actions["edit_host"] = {
    "handler"     : action_edit_host,
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
    "locking"         : False,
}

###############

def action_delete_host(request):
    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, "Hostname is missing")

    return g_api.delete_hosts([hostname])

api_actions["delete_host"] = {
    "handler"     : action_delete_host,
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
    "locking"         : True,
}

