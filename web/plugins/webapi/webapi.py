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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# CLEANUP: Replace MKUserError by MKAPIError or something like that

def validate_request_keys(request, valid_keys):
    for key in request.keys():
        if key not in valid_keys:
            raise MKUserError(None, _("Invalid key: %s") % key)

# Check if the given attribute name exists, no type check
def validate_general_host_attributes(host_attributes):
    # inventory_failed and site are no "real" host_attributes
    all_host_attribute_names = map(lambda (x, y): x.name(), all_host_attributes()) + ["inventory_failed", "site"]
    for name, value in host_attributes.items():
        if name not in all_host_attribute_names:
            raise MKUserError(None, _("Unknown attribute: %s") % html.attrencode(name))
        # The site attribute gets an extra check
        if name == "site" and value not in config.allsites().keys():
            raise MKUserError(None, _("Unknown site %s") % html.attrencode(value))

# Check if the tag group exists and the tag value is valid
def validate_host_tags(host_tags):
    for key, value in host_tags.items():
        for group_entry in configured_host_tags():
            if group_entry[0] == key:
                for value_entry in group_entry[2]:
                    if value_entry[0] == value:
                        break
                else:
                    raise MKUserError(None, _("Unknown host tag %s") % html.attrencode(value))
                break
        else:
            raise MKUserError(None, _("Unknown host tag group %s") % html.attrencode(key))

def validate_host_attributes(attributes):
    validate_general_host_attributes(dict((key, value) for key, value in attributes.items() if not key.startswith("tag_")))
    validate_host_tags(dict((key[4:], value) for key, value in attributes.items() if key.startswith("tag_")))


def action_add_host(request):
    validate_request_keys(request, ["hostname", "folder", "attributes"])

    if html.var("create_folders"):
        create_folders = bool(int(html.var("create_folders")))
    else:
        create_folders = True

    hostname    = request.get("hostname")
    folder_path = request.get("folder")
    attributes  = request.get("attributes", {})

    # Validate hostname
    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))
    Hostname().validate_value(hostname, "hostname")
    if Host.host_exists(hostname):
        raise MKUserError(None, _("Host %s already exists in the folder %s") % (hostname, Host.host(hostname).folder().path()))

    # Validate folder
    if folder_path == None:
        raise MKUserError(None, _("Foldername is missing"))

    if folder_path != "" and folder_path != "/":
      folders = folder_path.split("/")
      for foldername in folders:
        check_wato_foldername(None, foldername, just_name=True)
    else:
       folder_path = ""
       folders =  [""]

    # Validate and cleanup given attributes
    # CLEANUP: modify WebAPI .nodes argument
    cluster_nodes = None
    if ".nodes" in attributes:
        cluster_nodes = attributes[".nodes"]
        del attributes[".nodes"]
    validate_host_attributes(attributes)

    # Create folder(s)
    if not Folder.folder_exists(folder_path):
        if not create_folders:
            raise MKUserError(None, _("Folder not existing"))
        Folder.create_missing_folders(folder_path)

    # Add host
    Folder.folder(folder_path).create_hosts([(hostname, attributes, cluster_nodes)])

api_actions["add_host"] = {
    "handler"         : action_add_host,
    "locking"         : True,
}

###############

def action_edit_host(request):
    validate_request_keys(request, ["hostname", "unset_attributes", "attributes"])

    hostname              = request.get("hostname")
    attributes            = request.get("attributes", {})
    unset_attribute_names = request.get("unset_attributes", [])

    # Validate host
    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    host = Host.host(hostname)
    if not host:
        raise MKUserError(None, _("No such host"))

    # Only validate the new attributes
    attributes    = request.get("attributes", {})
    # CLEANUP: modify WebAPI .nodes argument
    cluster_nodes = None
    if ".nodes" in attributes:
        cluster_nodes = attributes[".nodes"]
        del attributes[".nodes"]
    validate_host_attributes(attributes)

    # Update existing attributes. Add new, remove unset_attributes
    current_attributes = host.attributes().copy()
    for attrname in unset_attribute_names:
        if attrname in current_attributes:
            del current_attributes[attrname]
    current_attributes.update(attributes)

    if not cluster_nodes:
        cluster_nodes = host.cluster_nodes()

    host.edit(current_attributes, cluster_nodes)

api_actions["edit_host"] = {
    "handler"     : action_edit_host,
    "locking"     : True,
}

###############

def action_get_host(request):
    validate_request_keys(request, ["hostname"])

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

    response = { "attributes": attributes, "path": host.folder().path(), "hostname": host.name() }
    if host.is_cluster():
        response["nodes"] = host.cluster_nodes()
    return response

api_actions["get_host"] = {
    "handler"         : action_get_host,
    "locking"         : False,
}

###############

def action_get_all_hosts(request):
    if html.var("effective_attributes"):
        effective_attributes = bool(int(html.var("effective_attributes")))
    else:
        effective_attributes = False

    response = {}
    all_hosts = Folder.root_folder().all_hosts_recursively()

    for hostname, host in all_hosts.items():
        host.need_permission("read")
        if effective_attributes:
            attributes = host.effective_attributes()
        else:
            attributes = host.attributes()
        response[hostname] = { "attributes": attributes, "path": host.folder().path(), "hostname": host.name() }
        if host.is_cluster():
            response[hostname]["nodes"] = host.cluster_nodes()

    return response

api_actions["get_all_hosts"] = {
    "handler": action_get_all_hosts,
    "locking": False,
}


###############

def action_delete_host(request):
    validate_request_keys(request, ["hostname"])

    hostname = request.get("hostname")

    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    host = Host.host(hostname)
    if not host:
        raise MKUserError(None, _("No such host"))

    host.folder().delete_hosts([host.name()])

api_actions["delete_host"] = {
    "handler"     : action_delete_host,
    "locking"     : True,
}

###############

def action_discover_services(request):
    validate_request_keys(request, ["hostname", "mode"])
    config.need_permission("wato.services")

    mode = html.var("mode") and html.var("mode") or "new"
    hostname = request.get("hostname")
    if not hostname:
        raise MKUserError(None, _("Hostname is missing"))

    host = Host.host(hostname)
    if not host:
        raise MKUserError(None, _("No such host"))

    host_attributes = host.effective_attributes()
    counts, failed_hosts = check_mk_automation(host_attributes.get("site"), "inventory", [ "@scan", mode ] + [hostname])
    if failed_hosts:
        if not host.discovery_failed():
            host.set_discovery_failed()
        raise MKUserError(None, _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

    if host.discovery_failed():
        host.clear_discovery_failed()

    host.mark_dirty()

    if mode == "refresh":
        message = _("Refreshed check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        log_pending(LOCALRESTART, hostname, "refresh-autochecks", message)
    else:
        message = _("Saved check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        log_pending(LOCALRESTART, hostname, "set-autochecks", message)

    msg = _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d") % tuple(counts[hostname])
    return msg

api_actions["discover_services"] = {
    "handler"     : action_discover_services,
    "locking"     : True,
}

###############

def action_activate_changes(request):
    validate_request_keys(request, ["sites"])

    mode = html.var("mode") and html.var("mode") or "dirty"
    if html.var("allow_foreign_changes"):
        allow_foreign_changes = bool(int(html.var("allow_foreign_changes")))
    else:
        allow_foreign_changes = False

    sites = request.get("sites")

    if foreign_changes():
        if not config.may("wato.activateforeign"):
            raise MKAuthException(_("You are not allowed to activate changes of other users."))
        if not allow_foreign_changes:
            raise MKAuthException(_("There are changes from other users and foreign changes "\
                                    "are not allowed in this API call."))

    if mode == "specific":
        for site in sites:
            if site not in config.allsites().keys():
                raise MKUserError(None, _("Unknown site %s") % html.attrencode(site))

    ### Start activate changes
    errors    = []
    repstatus = load_replication_status()
    for site in config.allsites().values():
        if mode == "all" or (mode == "dirty" and repstatus.get(site["id"],{}).get("need_restart")) or\
            (sites and site["id"] in sites):
            try:
                synchronize_site(site, True)
            except Exception, e:
                errors.append("%s: %s" % (site["id"], e))
            if not config.site_is_local(site["id"]):
                remove_sync_snapshot(site["id"])

    if not errors:
        log_commit_pending()
    else:
        raise MKUserError(None, ", ".join(errors))

api_actions["activate_changes"] = {
    "handler"         : action_activate_changes,
    "locking"         : True,
}

