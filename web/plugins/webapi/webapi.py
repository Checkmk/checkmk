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

# CLEANUP: Replace MKUserError by MKAPIError or something like that
# TODO: .nodes suchen und anders behandeln

def validate_api_request(request, valid_keys):
    for key in request.keys():
        if key not in valid_keys:
            raise MKUserError(None, _("Invalid key: %s") % key)


def action_add_host(request):
    validate_api_request(request, ["hostname", "folder", "attributes"])

    if html.var("create_folders"):
        create_folders = bool(int(html.var("create_folders")))
    else:
        create_folders = True

    hostname   = request.get("hostname")
    Hostname().validate_value(hostname, "hostname")
    folder_path = request.get("folder")
    attributes = request.get("attributes", {})

    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))
    if folder_path == None:
        raise MKUserError(None, _("Foldername is missing"))

    if not Folder.folder_exists(folder_path):
        if not create_folders:
            raise MKUserError(None, _("Folder not existing"))
        Folder.create_missing_folders(folder_path)

    # TODO: Validation of arguments (hostname, foldername, attributes)

    Folder.folder(folder_path).create_hosts([(hostname, attributes, None)])


api_actions["add_host"] = {
    "handler"         : action_add_host,
    "locking"         : True,
}

###############

def action_edit_host(request):
    validate_api_request(request, ["hostname", "unset_attributes", "attributes"])

    hostname              = request.get("hostname")
    attributes            = request.get("attributes", {})
    unset_attribute_names = request.get("unset_attributes", [])

    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    host = Host.host(hostname)
    if not host:
        raise MKUserError(None, _("No such host"))

    current_attributes = host.attributes().copy()
    for attrname in unset_attribute_names:
        if attrname in current_attributes:
            del current_attributes[attrname]
    current_attributes.update(attributes)
    host.edit(attributes, host.cluster_nodes())


api_actions["edit_host"] = {
    "handler"     : action_edit_host,
    "locking"     : True,
}

###############

def action_get_host(request):
    validate_api_request(request, ["hostname"])

    hostname = request.get("hostname")
    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))
    host = Host.host(hostname)
    if not host:
        raise MKUserError(None, _("No such host"))
    host.need_permission("read")

    if html.var("effective_attributes") == "1":
        attributes = host.effective_attributes()
    else:
        attributes = host.attributes()

    return { "attributes": attributes, "path": host.folder().path(), "hostname": host.name() }


api_actions["get_host"] = {
    "handler"         : action_get_host,
    "locking"         : False,
}

###############

def action_delete_host(request):
    validate_api_request(request, ["hostname"])

    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    return g_api.delete_hosts([hostname])

api_actions["delete_host"] = {
    "handler"     : action_delete_host,
    "locking"     : True,
}

###############

def action_discover_services(request):
    validate_api_request(request, ["hostname"])

    mode = html.var("mode") and html.var("mode") or "new"

    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    return g_api.discover_services(hostname, mode = mode)

api_actions["discover_services"] = {
    "handler"     : action_discover_services,
    "locking"     : True,
}

###############

def action_activate_changes(request):
    validate_api_request(request, ["sites"])

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

###############

def action_get_all_hosts(request):
    if html.var("effective_attributes"):
        effective_attributes = bool(int(html.var("effective_attributes")))
    else:
        effective_attributes = False
    return g_api.get_all_hosts(effective_attr = effective_attributes)

api_actions["get_all_hosts"] = {
    "handler": action_get_all_hosts,
    "locking": False,
}

