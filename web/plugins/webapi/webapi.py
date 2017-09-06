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

# TODO CLEANUP: Replace MKUserError by MKAPIError or something like that

def validate_request_keys(request, required_keys = None, optional_keys = None):
    if required_keys:
        missing = set(required_keys) - set(request.keys())
        if missing:
            raise MKUserError(None, _("Missing required key(s): %s") % ", ".join(missing))


    all_keys = (required_keys or []) + (optional_keys or [])
    for key in request.keys():
        if key not in all_keys:
            raise MKUserError(None, _("Invalid key: %s") % key)


def check_hostname(hostname, should_exist = True):
    # Validate hostname
    Hostname().validate_value(hostname, "hostname")

    if should_exist:
        host = Host.host(hostname)
        if not host:
            raise MKUserError(None, _("No such host"))
    else:
        if Host.host_exists(hostname):
            raise MKUserError(None, _("Host %s already exists in the folder %s") % (hostname, Host.host(hostname).folder().path()))

#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Check if the given attribute name exists, no type check
def validate_general_host_attributes(host_attributes):
    # inventory_failed and site are no "real" host_attributes (TODO: Clean this up!)
    all_host_attribute_names = map(lambda (x, y): x.name(), all_host_attributes()) + ["inventory_failed", "site"]
    for name, value in host_attributes.items():
        if name not in all_host_attribute_names:
            raise MKUserError(None, _("Unknown attribute: %s") % html.attrencode(name))

        # For real host attributes validate the values
        try:
            attr = host_attribute(name)
        except KeyError:
            attr = None

        if attr != None:
            if attr.needs_validation("host"):
                attr.validate_input(value, "")

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
    validate_request_keys(request, required_keys=["hostname", "folder"],
                                   optional_keys=["attributes", "nodes", "create_folders"])

    create_folders = int(request.get("create_folders", "1")) == 1

    hostname      = request.get("hostname")
    folder_path   = request.get("folder")
    attributes    = request.get("attributes", {})
    cluster_nodes = request.get("nodes")

    check_hostname(hostname, should_exist = False)

    # Validate folder
    if folder_path != "" and folder_path != "/":
        folders = folder_path.split("/")
        for foldername in folders:
            check_wato_foldername(None, foldername, just_name=True)
    else:
       folder_path = ""
       folders =  [""]

    # Deprecated, but still supported
    # Nodes are now specified in an extra key
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
    validate_request_keys(request, required_keys=["hostname"],
                                   optional_keys=["unset_attributes", "attributes", "nodes"])

    hostname              = request.get("hostname")
    attributes            = request.get("attributes", {})
    unset_attribute_names = request.get("unset_attributes", [])
    cluster_nodes         = request.get("nodes")

    check_hostname(hostname, should_exist = True)

    host = Host.host(hostname)

    # Deprecated, but still supported
    # Nodes are now specified in an extra key
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
    validate_request_keys(request, required_keys=["hostname"],
                                   optional_keys=["effective_attributes"])

    hostname = request.get("hostname")

    check_hostname(hostname, should_exist = True)

    host = Host.host(hostname)
    host.need_permission("read")

    if int(request.get("effective_attributes", "0")) == 1:
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
    validate_request_keys(request, optional_keys=["effective_attributes"])

    effective_attributes = int(request.get("effective_attributes", "0")) == 1

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
    validate_request_keys(request, required_keys=["hostname"])

    hostname = request.get("hostname")
    check_hostname(hostname, should_exist = True)

    host = Host.host(hostname)
    host.folder().delete_hosts([host.name()])

api_actions["delete_host"] = {
    "handler"     : action_delete_host,
    "locking"     : True,
}

#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+


def action_get_all_groups(request, group_type):
    return userdb.load_group_information().get(group_type, {})


def action_delete_group(request, group_type):
    validate_request_keys(request, required_keys=["groupname"])
    groupname = request.get("groupname")
    delete_group(groupname, group_type)


def get_group_extra_info(request, group_type):
    extra_info = {}
    extra_info["alias"] = request.get("alias")

    if group_type == "contact" and "nagvis_maps" in request:
        extra_info["nagvis_maps"] = request["nagvis_maps"]

    if cmk.is_managed_edition():
        extra_info["customer"] = request["customer"]

    return extra_info


def validate_group_request_keys(request, group_type):
    required_keys = ["groupname", "alias"]

    if cmk.is_managed_edition():
        required_keys.append("customer")

    if group_type == "contact":
        validate_request_keys(request, required_keys=required_keys,
                                       optional_keys=["nagvis_maps"])
    else:
        validate_request_keys(request, required_keys=required_keys)


def action_add_group(request, group_type):
    validate_group_request_keys(request, group_type)
    add_group(request.get("groupname"), group_type, get_group_extra_info(request, group_type))


def action_edit_group(request, group_type):
    validate_group_request_keys(request, group_type)
    edit_group(request.get("groupname"), group_type, get_group_extra_info(request, group_type))


def register_group_apis():
    for group_type in [ "contact", "host", "service" ]:
        api_actions["get_all_%sgroups" % group_type] = {
            # Note: group_type=group_type bypasses pythons late binding behaviour
            "handler"     : lambda x, group_type=group_type: action_get_all_groups(x, group_type),
            "locking"     : False,
        }

        api_actions["delete_%sgroup" % group_type] = {
            # Note: group_type=group_type bypasses pythons late binding behaviour
            "handler"     : lambda x, group_type=group_type: action_delete_group(x, group_type),
            "locking"     : True,
        }

        api_actions["add_%sgroup" % group_type] = {
            # Note: group_type=group_type bypasses pythons late binding behaviour
            "handler"     : lambda x, group_type=group_type: action_add_group(x, group_type),
            "locking"     : True,
        }

        api_actions["edit_%sgroup" % group_type] = {
            # Note: group_type=group_type bypasses pythons late binding behaviour
            "handler"     : lambda x, group_type=group_type: action_edit_group(x, group_type),
            "locking"     : True,
        }

register_group_apis() # Otherwise, group_type is known in the global scope..

#.
#   .--Users---------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def action_get_all_users(request):
    validate_request_keys(request, [])
    all_users = userdb.load_users(lock = False)
    return all_users


api_actions["get_all_users"] = {
    "handler"     : action_get_all_users,
    "locking"     : False,
}

###############

def action_delete_users(request):
    validate_request_keys(request, required_keys=["users"])
    delete_users(request.get("users"))


api_actions["delete_users"] = {
    "handler"     : action_delete_users,
    "locking"     : True,
}

###############

def action_add_users(request):
    validate_request_keys(request, required_keys=["users"])

    users_from_request = request.get("users")
    all_users = userdb.load_users()

    new_user_objects = {}
    for user_id, values in users_from_request.items():
        user_template = userdb.new_user_template("htpasswd")
        if "password" in values:
            values["password"] = userdb.encrypt_password(values["password"])
            values["serial"]   = 1

        user_template.update(values)
        new_user_objects[user_id] = {"attributes": user_template, "is_new_user": True}

    edit_users(new_user_objects)


api_actions["add_users"] = {
    "handler"     : action_add_users,
    "locking"     : True,
}

###############

def action_edit_users(request):
    validate_request_keys(request, required_keys=["users"])

    # A dictionary with the userid as key
    # Each value is a {"set_attributes": {"alias": "test"},
    #                  "unset_attributes": ["pager", "email"]}

    user_settings = request.get("users")
    all_users = userdb.load_users()

    import copy
    edit_user_objects = {}
    for user_id, settings in user_settings.items():
        if user_id not in all_users:
            raise MKUserError(None, _("Unknown user: %s") % user_id)

        if all_users[user_id].get("connector") != "htpasswd":
            raise MKUserError(None, _("This user is not a htpasswd user: %s") % user_id)

        user_attrs = copy.deepcopy(all_users[user_id])
        user_attrs.update(settings.get("set_attributes", {}))
        for entry in settings.get("unset_attributes", []):
            if entry not in user_attrs:
                continue
            del user_attrs[entry]

        new_password = settings.get("set_attributes", {}).get("password")
        if new_password:
            user_attrs["password"] = userdb.encrypt_password(new_password)
            user_attrs["serial"]   = user_attrs.get("serial", 0) + 1

        edit_user_objects[user_id] = {"attributes": user_attrs, "is_new_user": False}

    edit_users(edit_user_objects)


api_actions["edit_users"] = {
    "handler"     : action_edit_users,
    "locking"     : True,
}


#.
#   .--Other---------------------------------------------------------------.
#   |                       ___  _   _                                     |
#   |                      / _ \| |_| |__   ___ _ __                       |
#   |                     | | | | __| '_ \ / _ \ '__|                      |
#   |                     | |_| | |_| | | |  __/ |                         |
#   |                      \___/ \__|_| |_|\___|_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

def action_discover_services(request):
    validate_request_keys(request, required_keys=["hostname"],
                                   optional_keys=["mode"])
    config.user.need_permission("wato.services")

    mode = html.var("mode") and html.var("mode") or "new"
    hostname = request.get("hostname")

    check_hostname(hostname, should_exist = True)

    host = Host.host(hostname)

    host_attributes = host.effective_attributes()
    counts, failed_hosts = check_mk_automation(host_attributes.get("site"), "inventory", [ "@scan", mode ] + [hostname])
    if failed_hosts:
        if not host.discovery_failed():
            host.set_discovery_failed()
        raise MKUserError(None, _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

    if host.discovery_failed():
        host.clear_discovery_failed()

    if mode == "refresh":
        message = _("Refreshed check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        add_service_change(host, "refresh-autochecks", message)
    else:
        message = _("Saved check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        add_service_change(host, "set-autochecks", message)

    msg = _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d") % tuple(counts[hostname])
    return msg

api_actions["discover_services"] = {
    "handler"     : action_discover_services,
    "locking"     : True,
}

###############

def action_activate_changes(request):
    validate_request_keys(request, optional_keys=["mode", "sites", "allow_foreign_changes", "comment"])

    mode = html.var("mode") and html.var("mode") or "dirty"
    if request.get("allow_foreign_changes"):
        allow_foreign_changes = bool(int(request.get("allow_foreign_changes")))
    else:
        allow_foreign_changes = False

    sites = request.get("sites")

    changes = ActivateChanges()
    changes.load()

    if changes.has_foreign_changes():
        if not config.user.may("wato.activateforeign"):
            raise MKAuthException(_("You are not allowed to activate changes of other users."))
        if not allow_foreign_changes:
            raise MKAuthException(_("There are changes from other users and foreign changes "\
                                    "are not allowed in this API call."))

    if mode == "specific":
        for site in sites:
            if site not in config.allsites().keys():
                raise MKUserError(None, _("Unknown site %s") % html.attrencode(site))


    manager = ActivateChangesManager()
    manager.load()

    if not manager.has_changes():
        raise MKUserError(None, _("Currently there are no changes to activate."))

    if not sites:
        sites = manager.dirty_and_active_activation_sites()

    comment = request.get("comment", "").strip()
    if comment == "":
        comment = None

    manager.start(sites, comment=comment, activate_foreign=allow_foreign_changes)
    manager.wait_for_completion()
    return manager.get_state()

api_actions["activate_changes"] = {
    "handler"         : action_activate_changes,
    "locking"         : True,
}


