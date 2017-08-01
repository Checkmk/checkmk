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

#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+

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
    # Validate hostname with valuespec
    Hostname().validate_value(hostname, "hostname")

    if should_exist:
        host = watolib.Host.host(hostname)
        if not host:
            raise MKUserError(None, _("No such host"))
    else:
        if watolib.Host.host_exists(hostname):
            raise MKUserError(None, _("Host %s already exists in the folder %s") % (hostname, watolib.Host.host(hostname).folder().path()))


# Check if the given attribute name exists, no type check
def validate_general_host_attributes(host_attributes):
    # inventory_failed and site are no "real" host_attributes (TODO: Clean this up!)
    all_host_attribute_names = map(lambda (x, y): x.name(), watolib.all_host_attributes()) + ["inventory_failed", "site"]
    for name, value in host_attributes.items():
        if name not in all_host_attribute_names:
            raise MKUserError(None, _("Unknown attribute: %s") % html.attrencode(name))

        # For real host attributes validate the values
        try:
            attr = watolib.host_attribute(name)
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
        for group_entry in watolib.configured_host_tags():
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


def compute_config_hash(entity):
    import json, md5
    try:
        entity_encoded = json.dumps(entity, sort_keys=True)
        entity_hash    = md5.md5(entity_encoded).hexdigest()
    except Exception, e:
        logger.error("Error %s" % e)
        entity_hash = "0"

    return entity_hash


def validate_config_hash(hash_value, entity):
    entity_hash = compute_config_hash(entity)
    if hash_value != entity_hash:
        raise MKUserError(None, _("The configuration has changed in the meantime. "\
                                  "You need to load the configuration and start another update. "
                                  "If the existing configuration should not be checked, you can "
                                  "remove the configuration_hash value from the request object."))


def add_configuration_hash(response, configuration_object):
    response["configuration_hash"] = compute_config_hash(configuration_object)



class APICallCollection(object):
    @classmethod
    def all_classes(cls):
        return cls.__subclasses__() # pylint: disable=no-member


    def get_api_calls(self):
        raise NotImplementedError("This API collection does not register any API call")


#.
#   .--Folders-------------------------------------------------------------.
#   |                   _____     _     _                                  |
#   |                  |  ___|__ | | __| | ___ _ __ ___                    |
#   |                  | |_ / _ \| |/ _` |/ _ \ '__/ __|                   |
#   |                  |  _| (_) | | (_| |  __/ |  \__ \                   |
#   |                  |_|  \___/|_|\__,_|\___|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

class APICallFolders(APICallCollection):
    def get_api_calls(self):
        return {
            "get_folder": {
                "handler"         : self._get,
                "locking"         : False,
            },
            "add_folder": {
                "handler"         : self._add,
                "locking"         : True,
            },
            "edit_folder": {
                "handler"         : self._edit,
                "locking"         : True,
            },
            "delete_folder": {
                "handler"         : self._delete,
                "locking"         : True,
            },
            "get_all_folders": {
                "handler"         : self._get_all,
                "locking"         : False,
            },
        }


    def _get(self, request):
        validate_request_keys(request, required_keys=["folder"], optional_keys = ["effective_attributes"])
        folder_path = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)

        folder = watolib.Folder.folder(folder_path)
        if bool(int(request.get("effective_attributes", "0"))):
            attributes = folder.effective_attributes()
        else:
            attributes = folder.attributes()

        response = {"attributes": attributes}
        add_configuration_hash(response, attributes)
        return response


    def _add(self, request):
        validate_request_keys(request, required_keys=["folder", "attributes"],
                                       optional_keys=["create_parent_folders",
                                                       # "lock", "lock_subfolders"  # Not implemented yet
                                                     ])

        folder_path  = request["folder"]
        watolib.check_wato_foldername(None, os.path.basename(folder_path), just_name = True)

        folder_attributes = request.get("attributes", {})
        if "alias" in folder_attributes:
            folder_alias = folder_attributes.pop("alias") or os.path.basename(folder_path)
        else:
            folder_alias = os.path.basename(folder_path)

        # Validates host and folder attributes, since there are no real folder attributes, at all...
        validate_host_attributes(folder_attributes)

        # Check existance of parent folder, create it when configured
        create_parent_folders = bool(int(request.get("create_parent_folders", "1")))
        if create_parent_folders or watolib.Folder.folder_exists(os.path.dirname(folder_path)):
            watolib.Folder.root_folder().create_missing_folders(folder_path)
            watolib.Folder.folder(folder_path).edit(folder_alias, folder_attributes)
        else:
            raise MKUserError(None, _("Unable to create parent folder(s)."))


    def _edit(self, request):
        validate_request_keys(request, required_keys=["folder"],
                                       optional_keys=["attributes", "configuration_hash",
                                                       # "lock", "lock_subfolders"  # Not implemented yet
                                                     ])
        folder_path  = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)


        folder = watolib.Folder.folder(folder_path)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], folder.attributes())

        folder_attributes = request.get("attributes", {})
        if "alias" in folder_attributes:
            folder_alias = folder_attributes.pop("alias") or os.path.basename(folder_path)
        else:
            folder_alias = os.path.basename(folder_path)


        # Validates host and folder attributes, since there are no real folder attributes, at all...
        validate_host_attributes(folder_attributes)

        folder.edit(folder_alias, folder_attributes)


    def _delete(self, request):
        validate_request_keys(request, required_keys=["folder"],
                                       optional_keys=["configuration_hash"])

        folder_path = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)

        folder = watolib.Folder.folder(folder_path)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], folder.attributes())

        if folder.is_root():
            raise MKUserError(None, _("Unable to delete root folder"))

        folder.parent().delete_subfolder(folder.name())


    def _get_all(self, request):
        validate_request_keys(request, optional_keys = ["effective_attributes"])

        folders = {}
        effective_attributes = bool(int(request.get("effective_attributes", "0")))

        for folder_path, folder in watolib.Folder.all_folders().items():
            if effective_attributes:
                folders[folder_path] = folder.effective_attributes()
            else:
                folders[folder_path] = folder.attributes()

        return folders


#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

class APICallHosts(APICallCollection):
    def get_api_calls(self):
        return {
            "add_host": {
                "handler"         : self._add,
                "locking"         : True,
            },
            "edit_host": {
                "handler"         : self._edit,
                "locking"         : True,
            },
            "get_host": {
                "handler"         : self._get,
                "locking"         : False,
            },
            "delete_host": {
                "handler"         : self._delete,
                "locking"         : True,
            },
            "get_all_hosts": {
                "handler"         : self._get_all,
                "locking"         : False,
            },
        }


    def _add(self, request):
        validate_request_keys(request, required_keys=["hostname", "folder"],
                                       optional_keys=["attributes", "nodes", "create_folders"])

        create_parent_folders_var = request.get("create_parent_folders", request.get("create_folders", "1"))
        create_parent_folders = bool(int(create_parent_folders_var))

        hostname      = request.get("hostname")
        folder_path   = request.get("folder")
        attributes    = request.get("attributes", {})
        cluster_nodes = request.get("nodes")

        check_hostname(hostname, should_exist = False)

        # Validate folder
        if folder_path != "" and folder_path != "/":
            folders = folder_path.split("/")
            for foldername in folders:
                watolib.check_wato_foldername(None, foldername, just_name=True)
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
        if not watolib.Folder.folder_exists(folder_path):
            if not create_parent_folders:
                raise MKUserError(None, _("Unable to create parent folder(s)."))
            watolib.Folder.create_missing_folders(folder_path)

        # Add host
        watolib.Folder.folder(folder_path).create_hosts([(hostname, attributes, cluster_nodes)])


    def _edit(self, request):
        validate_request_keys(request, required_keys=["hostname"],
                                       optional_keys=["unset_attributes", "attributes", "nodes"])

        hostname              = request.get("hostname")
        attributes            = request.get("attributes", {})
        unset_attribute_names = request.get("unset_attributes", [])
        cluster_nodes         = request.get("nodes")

        check_hostname(hostname, should_exist = True)

        host = watolib.Host.host(hostname)

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


    def _get(self, request):
        validate_request_keys(request, required_keys=["hostname"],
                                       optional_keys=["effective_attributes"])

        hostname = request.get("hostname")

        check_hostname(hostname, should_exist = True)

        host = watolib.Host.host(hostname)
        host.need_permission("read")
        if bool(int(request.get("effective_attributes", "0"))):
            attributes = host.effective_attributes()
        else:
            attributes = host.attributes()

        response = { "attributes": attributes, "path": host.folder().path(), "hostname": host.name() }
        if host.is_cluster():
            response["nodes"] = host.cluster_nodes()
        return response


    def _get_all(self, request):
        validate_request_keys(request, optional_keys=["effective_attributes"])

        effective_attributes = bool(int(request.get("effective_attributes", "0")))

        response = {}
        all_hosts = watolib.Folder.root_folder().all_hosts_recursively()

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


    def _delete(self, request):
        validate_request_keys(request, required_keys=["hostname"])

        hostname = request["hostname"]
        check_hostname(hostname, should_exist = True)

        host = watolib.Host.host(hostname)
        host.folder().delete_hosts([host.name()])


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
    watolib.delete_group(groupname, group_type)


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
    watolib.add_group(request.get("groupname"), group_type, get_group_extra_info(request, group_type))


def action_edit_group(request, group_type):
    validate_group_request_keys(request, group_type)
    watolib.edit_group(request.get("groupname"), group_type, get_group_extra_info(request, group_type))


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
    watolib.delete_users(request.get("users"))


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
        user_template.update(values)
        new_user_objects[user_id] = {"attributes": user_template, "is_new_user": True}

    watolib.edit_users(new_user_objects)


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
        edit_user_objects[user_id] = {"attributes": user_attrs, "is_new_user": False}

    watolib.edit_users(edit_user_objects)


api_actions["edit_users"] = {
    "handler"     : action_edit_users,
    "locking"     : True,
}


#.
#   .--Rules---------------------------------------------------------------.
#   |                       ____        _                                  |
#   |                      |  _ \ _   _| | ___  ___                        |
#   |                      | |_) | | | | |/ _ \/ __|                       |
#   |                      |  _ <| |_| | |  __/\__ \                       |
#   |                      |_| \_\\__,_|_|\___||___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+

class APICallRules(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.rulesets"] # wato.services ?
        return {
            "get_ruleset": {
                "handler"                : self._get,
                "required_permissions"   : required_permissions,
                "required_output_format" : "python",
                "locking"                : True, # locking?
            },
            "set_ruleset": {
                "handler"               : self._set,
                "required_permissions"  : required_permissions,
                "required_input_format" : "python",
                "locking"               : True,
            },
            "get_rulesets_info": {
                "handler"             : self._get_rulesets_info,
                "required_permissions": required_permissions,
                "locking"             : False,
            }
        }


    def _get_ruleset_configuration(self, ruleset_name):
        collection = watolib.SingleRulesetRecursively(ruleset_name)
        collection.load()
        ruleset = collection.get(ruleset_name)

        ruleset_dict = {}
        for folder, rule_index, rule in ruleset.get_rules():
            ruleset_dict.setdefault(folder.path(), [])
             # The path is already set in the folder hierarchy
            rule_config = rule.to_dict_config()
            del rule_config["path"]
            ruleset_dict[folder.path()].append(rule_config)

        return ruleset_dict



    def _get(self, request):
        validate_request_keys(request, required_keys=["ruleset_name"])
        ruleset_name = request["ruleset_name"].encode("utf-8")

        ruleset_dict = self._get_ruleset_configuration(ruleset_name)
        ruleset_hash = compute_config_hash(ruleset_dict)

        response = {"ruleset": ruleset_dict}
        add_configuration_hash(response, ruleset_dict)
        return response


    def _set(self, request):
        validate_request_keys(request, required_keys=["ruleset_name", "ruleset"],
                                       optional_keys=["configuration_hash"])

        # NOTE: This encoding here should be kept
        # Otherwise and unicode encoded text will be written into the
        # configuration file with unknown side effects
        ruleset_name = request["ruleset_name"].encode("utf-8")

        # Future validation, currently the rule API actions are admin only, so the check is pointless
        # may_edit_ruleset(ruleset_name)

        # Check if configuration hash has changed in the meantime
        ruleset_dict = self._get_ruleset_configuration(ruleset_name)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], ruleset_dict)

        # Check permissions of new rules and rules we are going to delete
        new_ruleset            = request["ruleset"]
        folders_set_ruleset    = set(new_ruleset.keys())
        folders_obsolete_ruleset = set(ruleset_dict.keys()) - folders_set_ruleset

        for check_folders in [folders_set_ruleset, folders_obsolete_ruleset]:
            for folder_path in check_folders:
                if not watolib.Folder.folder_exists(folder_path):
                    raise MKUserError(None, _("Folder %s does not exist") % folder_path)
                rule_folder = watolib.Folder.folder(folder_path)
                rule_folder.need_permission("write")

        # Verify all rules
        rule_vs = watolib.Ruleset(ruleset_name).rulespec.valuespec
        for folder_path, rules in new_ruleset.items():
            for rule in rules:
                value = rule["value"]
                try:
                    rule_vs.validate_datatype(value, "test_value")
                    rule_vs.validate_value(value, "test_value")
                except MKException, e:
                    raise MKException("ERROR: %s. Affected Rule %r" % (str(e), rule))


        # Add new rulesets
        for folder_path, rules in new_ruleset.items():
            folder = watolib.Folder.folder(folder_path)

            new_ruleset = watolib.Ruleset(ruleset_name)
            new_ruleset.from_config(folder, rules)

            folder_rulesets = watolib.FolderRulesets(folder)
            folder_rulesets.load()
            folder_rulesets.set(ruleset_name, new_ruleset)
            folder_rulesets.save()


        # Remove obsolete rulesets
        for folder_path in folders_obsolete_ruleset:
            folder = watolib.Folder.folder(folder_path)
            new_ruleset = watolib.FolderRulesets(ruleset_name)
            new_ruleset.from_config(folder, [])
            new_ruleset.save()


    def _get_rulesets_info(self, request):
        rulesets_info = {}
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()

        for varname, ruleset in all_rulesets.get_rulesets().items():
            rulesets_info[varname] = {
                "title":     ruleset.title(),
                "help":      ruleset.help(),
                "number_of_rules": ruleset.num_rules(),
            }
            item_help = ruleset.item_help()
            if item_help:
                rulesets_info[varname]["item_help"] = item_help

        return rulesets_info


#.
#   .--Hosttags------------------------------------------------------------.
#   |               _   _           _   _                                  |
#   |              | | | | ___  ___| |_| |_ __ _  __ _ ___                 |
#   |              | |_| |/ _ \/ __| __| __/ _` |/ _` / __|                |
#   |              |  _  | (_) \__ \ |_| || (_| | (_| \__ \                |
#   |              |_| |_|\___/|___/\__|\__\__,_|\__, |___/                |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+

class APICallHosttags(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.hosttags"]
        return {
            "get_hosttags": {
                "handler"             : self._get,
                "required_permissions": required_permissions,
                "locking"             : True,
            },
            "set_hosttags": {
                "handler"               : self._set,
                "required_permissions"  : required_permissions,
                "locking"               : True,
            }
        }


    def _get(self, request):
        validate_request_keys(request)

        hosttags_config = watolib.HosttagsConfiguration()
        hosttags_config.load()

        response = hosttags_config.get_dict_format()
        add_configuration_hash(response, response) # Looks strange, but is OK

        return response


    def _set(self, request):
        validate_request_keys(request, required_keys=["tag_groups", "aux_tags"],
                                       optional_keys=["configuration_hash"])

        hosttags_config = watolib.HosttagsConfiguration()
        hosttags_config.load()

        hosttags_dict = hosttags_config.get_dict_format()
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], hosttags_dict)
        del request["configuration_hash"]

        # Check for conflicts with existing configuration
        # Tags may be either specified grouped in a host/folder configuration, e.g agent/cmk-agent,
        # or specified as the plain id in rules. We need to check both variants..
        used_tags = self._get_used_grouped_tags()
        used_tags.update(self._get_used_rule_tags())

        changed_hosttags_config = watolib.HosttagsConfiguration()
        changed_hosttags_config.parse_config(request)

        new_tags = changed_hosttags_config.get_tag_ids()
        new_tags.update(changed_hosttags_config.get_tag_ids_with_group_prefix())

        # Remove the builtin hoststags from the list of used_tags
        builtin_hosttags, builtin_auxtags = watolib.load_builtin_hosttags()
        for tag_group_id, tag_group__title, tags in builtin_hosttags:
            for tag_id, tag_title, aux_tags in tags:
                used_tags.discard("%s/%s" % (tag_group_id, tag_id))
                used_tags.discard(tag_id)
        for tag_id, tag_title in builtin_auxtags:
            used_tags.discard(tag_id)

        missing_tags = used_tags - new_tags
        if missing_tags:
            raise MKUserError(None, _("Unable to apply new hosttag configuration. The following tags "
                                      "are still in use, but not mentioned in the updated "
                                      "configuration: %s") % ", ".join(missing_tags))

        changed_hosttags_config.save()


    def _get_used_grouped_tags(self):
        used_tags = set([])

        # This requires a lot of computation power..
        for folder in watolib.Folder.all_folders().values():
            for attr_name, value in folder.attributes().items():
                if attr_name.startswith("tag_"):
                    used_tags.add("%s/%s" % (attr_name[4:], value))

        for host in watolib.Host.all().values():
            # NOTE: Do not use tags() function
            for attr_name, value in host.attributes().items():
                if attr_name.startswith("tag_"):
                    used_tags.add("%s/%s" % (attr_name[4:], value))
        return used_tags

    def _get_used_rule_tags(self):
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()
        used_tags = set()
        for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
            for folder, rulenr, rule in ruleset.get_rules():
                for tag_spec in rule.tag_specs:
                    used_tags.add(tag_spec.lstrip("!"))

        used_tags.discard(None)
        return used_tags


#.
#   .--Sites---------------------------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

class APICallSites(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.sites"]
        return {
            "get_site": {
                "handler"                : self._get,
                "required_permissions"   : required_permissions,
                "required_output_format" : "python",
                "locking"                : False,
            },
            "set_site": {
                "handler"               : self._set,
                "required_permissions"  : required_permissions,
                "required_input_format" : "python",
                "locking"               : True,
            },
            "delete_site": {
                "handler"              : self._delete,
                "required_permissions" : required_permissions,
                "locking"              : True,
            },
            "login_site": {
                "handler"              : self._login,
                "required_permissions" : required_permissions,
                "locking"              : True,
            },
            "logout_site": {
                "handler"              : self._logout,
                "required_permissions" : required_permissions,
                "locking"              : True,
            },
        }


    def _get(self, request):
        validate_request_keys(request, required_keys=["site_id"])

        all_sites = watolib.SiteManagement.load_sites()
        existing_site = all_sites.get(request["site_id"])

        if not existing_site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        sites_dict = {"site_config": existing_site, "site_id": request["site_id"]}
        sites_dict["configuration_hash"] = compute_config_hash(existing_site)
        return sites_dict


    def _set(self, request):
        validate_request_keys(request, required_keys=["site_config", "site_id"],
                                       optional_keys=["configuration_hash"])

        all_sites = watolib.SiteManagement.load_sites()
        existing_site = all_sites.get(request["site_id"])
        if existing_site and "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], existing_site)

        watolib.SiteManagement.validate_configuration(request["site_id"], request["site_config"], all_sites)

        all_sites[request["site_id"]] = request["site_config"]
        watolib.SiteManagement.save_sites(all_sites)


    def _delete(self, request):
        validate_request_keys(request, required_keys=["site_id"],
                                       optional_keys=["configuration_hash"])

        all_sites = watolib.SiteManagement.load_sites()
        existing_site = all_sites.get(request["site_id"])
        if existing_site and "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], existing_site)

        watolib.SiteManagement.delete_site(request["site_id"])


    def _login(self, request):
        validate_request_keys(request, required_keys=["site_id", "username", "password"])

        all_sites = watolib.SiteManagement.load_sites()
        site = all_sites.get(request["site_id"])
        if not site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        secret = watolib.do_site_login(request["site_id"], request["username"], request["password"])
        site["secret"] = secret
        watolib.SiteManagement.save_sites(all_sites)


    def _logout(self, request):
        validate_request_keys(request, required_keys=["site_id"])

        all_sites = watolib.SiteManagement.load_sites()
        site = all_sites.get(request["site_id"])
        if not site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        if "secret" in site:
            del site["secret"]
            watolib.SiteManagement.save_sites(all_sites)


for api_call_class in APICallCollection.all_classes():
    api_actions.update(api_call_class().get_api_calls())



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

    mode = html.var("mode", deflt="new")
    hostname = request.get("hostname")

    check_hostname(hostname, should_exist = True)

    host = watolib.Host.host(hostname)

    host_attributes = host.effective_attributes()
    counts, failed_hosts = watolib.check_mk_automation(host_attributes.get("site"), "inventory", [ "@scan", mode ] + [hostname])
    if failed_hosts:
        if not host.discovery_failed():
            host.set_discovery_failed()
        raise MKUserError(None, _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

    if host.discovery_failed():
        host.clear_discovery_failed()

    if mode == "refresh":
        message = _("Refreshed check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        watolib.add_service_change(host, "refresh-autochecks", message)
    else:
        message = _("Saved check configuration of host [%s] with %d services") % (hostname, counts[hostname][3])
        watolib.add_service_change(host, "set-autochecks", message)

    msg = _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d") % tuple(counts[hostname])
    return msg

api_actions["discover_services"] = {
    "handler"     : action_discover_services,
    "required_permissions": ["wato.services"],
    "locking"     : True,
}

###############

def action_activate_changes(request):
    validate_request_keys(request, optional_keys=["mode", "sites", "allow_foreign_changes", "comment"])

    mode = html.var("mode", deflt="dirty")
    if request.get("allow_foreign_changes"):
        allow_foreign_changes = bool(int(request.get("allow_foreign_changes")))
    else:
        allow_foreign_changes = False

    sites = request.get("sites")

    changes = watolib.ActivateChanges()
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


    manager = watolib.ActivateChangesManager()
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


for api_call_class in APICallCollection.all_classes():
    api_actions.update(api_call_class().get_api_calls())
